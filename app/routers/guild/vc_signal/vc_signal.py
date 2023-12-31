from fastapi import APIRouter
from fastapi.responses import RedirectResponse
from starlette.requests import Request
from fastapi.templating import Jinja2Templates

from dotenv import load_dotenv
load_dotenv()

import os
from typing import List

from typing import List,Dict,Any,Tuple

from base.database import PostgresDB
from base.aio_req import (
    aio_get_request,
    pickle_read,
    return_permission,
    oauth_check,
    sort_discord_vc_channel
)
from model_types.discord_type.discord_user_session import DiscordOAuthData,DiscordUser

from discord.ext import commands
try:
    from core.start import DBot
except ModuleNotFoundError:
    from app.core.start import DBot

DISCORD_BASE_URL = "https://discord.com/api"
DISCORD_REDIRECT_URL = f"https://discord.com/api/oauth2/authorize?response_type=code&client_id={os.environ.get('DISCORD_CLIENT_ID')}&scope={os.environ.get('DISCORD_SCOPE')}&redirect_uri={os.environ.get('DISCORD_CALLBACK_URL')}&prompt=consent"

DISCORD_BOT_TOKEN = os.environ["DISCORD_BOT_TOKEN"]

USER = os.getenv('PGUSER')
PASSWORD = os.getenv('PGPASSWORD')
DATABASE = os.getenv('PGDATABASE')
HOST = os.getenv('PGHOST')
db = PostgresDB(
    user=USER,
    password=PASSWORD,
    database=DATABASE,
    host=HOST
)


# new テンプレート関連の設定 (jinja2)
templates = Jinja2Templates(directory="templates")

class VcSignalView(commands.Cog):
    def __init__(self, bot: DBot):
        self.bot = bot
        self.router = APIRouter()

        @self.router.get('/guild/{guild_id}/vc-signal')
        async def vc_signal(
            request:Request,
            guild_id:int
        ):
            # OAuth2トークンが有効かどうか判断
            if request.session.get('discord_oauth_data'):
                oauth_session = DiscordOAuthData(**request.session.get('discord_oauth_data'))
                user_session = DiscordUser(**request.session.get('discord_user'))
                # トークンの有効期限が切れていた場合、再ログインする
                if not await oauth_check(access_token=oauth_session.access_token):
                    return RedirectResponse(url=DISCORD_REDIRECT_URL,status_code=302)
            else:
                return RedirectResponse(url=DISCORD_REDIRECT_URL,status_code=302)
            # 使用するデータベースのテーブル名
            TABLE = f'guilds_vc_signal_{guild_id}'

            # サーバのチャンネル一覧を取得
            all_channel = await aio_get_request(
                url = DISCORD_BASE_URL + f'/guilds/{guild_id}/channels',
                headers = {
                    'Authorization': f'Bot {DISCORD_BOT_TOKEN}'
                }
            )

            # チャンネルのソート
            all_channel_sort,all_channels,vc_channels = await sort_discord_vc_channel(all_channel=all_channel)

            vc_cate_sort = [
                tmp
                for tmp in all_channel_sort
                if tmp['type'] == 2 or tmp['type'] == 4
            ]

            # text_channel = list(chain.from_iterable(all_channels))
            text_channel_sort = [
                tmp
                for tmp in all_channel_sort
                if tmp['type'] == 0
            ]


            # サーバの情報を取得
            guild = await aio_get_request(
                url = DISCORD_BASE_URL + f'/guilds/{guild_id}',
                headers = {
                    'Authorization': f'Bot {DISCORD_BOT_TOKEN}'
                }
            )

            # ログインユーザの情報を取得
            guild_user = await aio_get_request(
                url = DISCORD_BASE_URL + f'/guilds/{guild_id}/members/{user_session.id}',
                headers = {
                    'Authorization': f'Bot {DISCORD_BOT_TOKEN}'
                }
            )
            role_list = [g for g in guild_user["roles"]]


            # サーバの権限を取得
            guild_user_permission = await return_permission(
                guild_id=guild_id,
                user_id=user_session.id,
                access_token=oauth_session.access_token
            )

            # パーミッションの番号を取得
            permission_code = await guild_user_permission.get_permission_code()

            # キャッシュ読み取り
            guild_table_fetch:List[Dict[str,Any]] = await pickle_read(filename='guild_set_permissions')
            guild_table = [
                g
                for g in guild_table_fetch
                if int(g.get('guild_id')) == guild_id
            ]
            guild_permission_code = 8
            guild_permission_user = list()
            guild_permission_role = list()
            if len(guild_table) > 0:
                guild_permission_code = int(guild_table[0].get('vc_permission'))
                guild_permission_user = [
                    user
                    for user in guild_table[0].get('vc_user_id_permission')
                ]
                guild_permission_role = [
                    role
                    for role in guild_table[0].get('vc_role_id_permission')
                ]

            and_code = guild_permission_code & permission_code
            admin_code = 8 & permission_code

            user_permission:str = 'normal'

            # 許可されている場合、管理者の場合
            if (and_code == permission_code or
                admin_code == 8 or
                user_session.id in guild_permission_user or
                len(set(guild_permission_role) & set(role_list)) > 0
                ):
                user_permission = 'admin'

            # キャッシュ読み取り
            table_fetch:List[Dict[str,Any]] = await pickle_read(filename=TABLE)

            # データベースへ接続
            await db.connect()

            vc_set = []

            # ボイスチャンネルのみを代入
            app_vc = [int(x['id']) for x in vc_cate_sort if x['type'] == 2]

            # テータベース側のボイスチャンネルを代入
            db_vc = [int(x['vc_id']) for x in table_fetch]
            if set(app_vc) != set(db_vc):
                # データベース側で欠けているチャンネルを取得
                missing_items = [
                    item
                    for item in table_fetch
                    if item not in vc_cate_sort
                ]

                # 新しくボイスチャンネルが作成されていた場合
                if len(missing_items) > 0:
                    for vc in missing_items:
                        if vc['type'] == 2:
                            row_values = {
                                'vc_id': vc['id'],
                                'guild_id': guild_id,
                                'send_signal': True,
                                'send_channel_id': guild.get('system_channel_id'), 
                                'join_bot': False,
                                'everyone_mention': True,
                                'mention_role_id':[]
                            }

                            # サーバー用に新たにカラムを作成
                            await db.insert_row(
                                table_name=TABLE,
                                row_values=row_values
                            )
                            vc_set.append(row_values)
                # ボイスチャンネルがいくつか削除されていた場合
                else:
                    # 削除されたチャンネルを取得
                    missing_items = [
                        item
                        for item in all_channels
                        if item not in table_fetch
                    ]

                    # 削除されたチャンネルをテーブルから削除
                    for vc in missing_items:
                        await db.delete_row(
                            table_name=TABLE,
                            where_clause={
                                'vc_id':vc['vc_id']
                            }
                        )

                    # 削除後のチャンネルを除き、残りのチャンネルを取得
                    vc_set = [
                        d for d in table_fetch
                        if not (d.get('vc_id') in [
                            e.get('vc_id') for e in missing_items
                        ] )
                    ]

            else:
                vc_set = table_fetch

                # データベースの状況を取得
                db_check_fetch = await db.select_rows(
                    table_name=TABLE,
                    columns=[],
                    where_clause={}
                )
                # データベースに登録されたが、削除されずに残っているチャンネルを削除
                check = [int(c['vc_id']) for c in db_check_fetch]
                del_check = set(check) - set(app_vc)

                for chan_id in list(del_check):
                    await db.delete_row(
                        table_name=TABLE,
                        where_clause={
                            'channel_id':chan_id
                        }
                    )

            await db.disconnect()

            return templates.TemplateResponse(
                "guild/vc_signal/vc_signal.html",
                {
                    "request": request,
                    "vc_cate_channel": vc_cate_sort,
                    "text_channel": text_channel_sort,
                    "guild": guild,
                    "guild_id": guild_id,
                    'vc_set' : vc_set,
                    "user_permission":user_permission,
                    "title": "ボイスチャンネルの送信設定/" + guild['name']
                }
            )
