from discord import Guild
import aiofiles

from dotenv import load_dotenv
load_dotenv()

import pickle
from typing import List,Dict,Any
import os

from base.database import PostgresDB
from base.aio_req import (
    aio_get_request
)

DISCORD_BASE_URL = "https://discord.com/api"

DISCORD_BOT_TOKEN = os.environ["DISCORD_BOT_TOKEN"]

# テーブル名のベースになるもの
# 後ろにサーバidがつく
LINE_TABLE = 'guilds_line_channel_'
VC_TABLE = 'guilds_vc_signal_'

# 各テーブルのカラム
LINE_COLUMNS = {
    'channel_id': 'NUMERIC PRIMARY KEY', 
    'guild_id': 'NUMERIC', 
    'line_ng_channel': 'boolean',
    'ng_message_type': 'VARCHAR(50)[]',
    'message_bot': 'boolean',
    'ng_users':'NUMERIC[]'
}
VC_COLUMNS = {
    'vc_id': 'NUMERIC PRIMARY KEY', 
    'guild_id': 'NUMERIC', 
    'send_signal':'boolean',
    'send_channel_id': 'NUMERIC', 
    'join_bot': 'boolean',
    'everyone_mention': 'boolean',
    'mention_role_id':'NUMERIC[]'
}
WEBHOOK_COLUMNS = {
    'uuid':'UUID PRIMARY KEY',
    'guild_id': 'NUMERIC', 
    'webhook_id':'NUMERIC',
    'subscription_type':'VARCHAR(50)',
    'subscription_id': 'VARCHAR(50)',
    'mention_roles':'NUMERIC[]',
    'mention_members':'NUMERIC[]',
    'search_or_word':'VARCHAR(50)[]',
    'search_and_word':'VARCHAR(50)[]',
    'mention_or_word':'VARCHAR(50)[]',
    'mention_and_word':'VARCHAR(50)[]',
    'created_at':'VARCHAR(50)'
}

# 各テーブルのカラムの初期値
LINE_NEW_COLUMNS = {
    'channel_id': 0, 
    'guild_id': 0, 
    'line_ng_channel': False,
    'ng_message_type': [],
    'message_bot': True,
    'ng_users':[]
}
VC_NEW_COLUMNS = {
    'vc_id': 0, 
    'guild_id': 0, 
    'send_signal':True,
    'send_channel_id': 0, 
    'join_bot': True,
    'everyone_mention': True,
    'mention_role_id':[]
}

# 取得するチャンネルのタイプ
LINE_TYPE = [0,2]
VC_TYPE = [2]

# 各要素をタプルにする
TABLES = (LINE_TABLE,VC_TABLE)
COLUMNS = (LINE_COLUMNS,VC_COLUMNS)
NEW_COLUMNS = (LINE_NEW_COLUMNS,VC_NEW_COLUMNS)
CHANNEL_TYPE = (LINE_TYPE,VC_TYPE)

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

async def db_pickle_save(guilds:List[Guild]):
    """
    データベースのテーブルの中身をキャッシュデータとしてローカルに保存します。

    param:
    guilds  :List[discord.Guild]
    Botが所属しているDiscordサーバのクラス
    """
    # データベースへ接続
    await db.connect()
    
    # サーバごとにテーブルのキャッシュデータを作成
    for guild in guilds:
        for table,column,new_column,channel_type in zip(
            TABLES,
            COLUMNS,
            NEW_COLUMNS,
            CHANNEL_TYPE
        ):
            # テーブル名を代入
            table_name:str = f"{table}{guild.id}"

            # テーブルの要素を取得
            table_fetch = await db.select_rows(
                table_name=f"{table_name}",
                columns=[],
                where_clause={}
            )

            webhook_colums = [key for key in column.keys()]
            table_colums = list()

            # テーブルをつくるか、カラムを取得するかのフラグ
            create_colum_flag = False
            create_table_flag = False

            # テーブルを削除するかのフラグ
            drop_table_flag = False

            # テーブルがなかった場合、作成
            if len(table_fetch) > 0:
                # テーブルが存在する場合、カラムを格納
                if (table_fetch[0] != f"{table_name} does not exist"):
                    create_colum_flag = True
                # テーブルが存在しない場合、作成
                elif (table_fetch[0] == f"{table_name} does not exist"):
                    create_table_flag = True

            # テーブルが存在している
            elif len(table_fetch) == 0:
                print(f'テーブル:{table_name}の要素は空です')
                # 中身が空かつ、要素が変更されていた場合
                if table_colums != webhook_colums:
                    drop_table_flag = True
                else:
                    table_colums = [key for key in column.keys()]

             # データベース側のカラムを格納
            if create_colum_flag:
                print(f'テーブル:{table_name}のカラム名一覧を作成します')
                table_colums = [key for key in table_fetch[0].keys()]
                
            # カラムの構成が変更されていた場合、削除し新たに作成する
            if table_colums != webhook_colums or drop_table_flag:
                print(f'テーブル:{table_name}を削除します')
                create_table_flag = True
                await db.drop_table(table_name=table_name)

            # テーブルの作成
            if create_table_flag:
                print(f'テーブル:{table_name}を作成します')
                await db.create_table(
                    table_name=table_name,
                    columns=column
                )

            # 中身が空の場合
            if len(table_fetch) == 0:

                # Discordのチャンネルを取得
                all_channel = await get_discord_channel(
                    guild_id=guild.id,
                    get_channel_type=channel_type
                )

                row_values = []

                # 主キーがチャンネルidの場合
                if (LINE_TABLE in table_name or
                    VC_TABLE in table_name
                    ):
                    for channel in all_channel:
                        row = {}
                        for key,values in new_column.items():
                            # 各要素を更新
                            if key == "channel_id" or key == "vc_id":
                                value = channel["id"]
                            elif key == "guild_id":
                                value = guild.id
                            elif key == "send_channel_id":
                                # システムチャンネルがある場合代入
                                if hasattr(guild.system_channel,'id'):
                                    value = guild.system_channel.id
                                else:
                                    value = 0
                            else:
                                value = values
                            row.update({key:value})
                        
                        row_values.append(row)

                        # 一つ一つ作成
                        # await db.insert_row(table_name=table_name,row_values=row)

                    # まとめて作成(バッジ)
                    await db.batch_insert_row(
                        table_name=table_name,
                        row_values=row_values
                    )

                    # テーブルの要素を取得
                    table_fetch = await db.select_rows(
                        table_name=f"{table_name}",
                        columns=[],
                        where_clause={}
                    )

            dict_row = list()

            # テーブルに中身がある場合
            if len(table_fetch) > 0:
                if table_fetch[0] != f"{table_name} does not exist":
                    print(f'{table_name}.pickleの書き込みをはじめます')
                    dict_row = [
                        dict(zip(record.keys(), record)) 
                        for record in table_fetch
                    ]


            # 書き込み
            async with aiofiles.open(
                file=f'{table_name}.pickle',
                mode='wb'
            ) as f:
                await f.write(pickle.dumps(obj=dict_row))

            print(f'{table_name}.pickleの書き込みが終了しました')

        # Webhookのテーブル
        table_fetch = await db.select_rows(
            table_name=f"webhook_{guild.id}",
            columns=[],
            where_clause={}
        )

        # カラム一覧
        webhook_colums = [key for key in WEBHOOK_COLUMNS.keys()]
        table_colums = list()

        # テーブルをつくるか、カラムを取得するかのフラグ
        create_colum_flag = False
        create_table_flag = False

        # テーブルを削除するかのフラグ
        drop_table_flag = False

        if len(table_fetch) > 0:
            # テーブルが存在する場合、カラムを格納
            if (table_fetch[0] != f"webhook_{guild.id} does not exist"):
                create_colum_flag = True
            # テーブルが存在しない場合、作成
            elif (table_fetch[0] == f"webhook_{guild.id} does not exist"):
                create_table_flag = True
        # テーブルが存在している
        elif len(table_fetch) == 0:
            print(f'テーブル:webhook_{guild.id}の要素は空です')
            # 中身が空かつ、要素が変更されていた場合
            if table_colums != webhook_colums:
                drop_table_flag = True
            else:
                table_colums = [key for key in WEBHOOK_COLUMNS.keys()]
            
        # データベース側のカラムを格納
        if create_colum_flag:
            print(f'テーブル:webhook_{guild.id}のカラム名一覧を作成します')
            table_colums = [key for key in table_fetch[0].keys()]
            
        # カラムの構成が変更されていた場合、削除し新たに作成する
        if table_colums != webhook_colums or drop_table_flag:
            print(f'テーブル:webhook_{guild.id}を削除します')
            create_table_flag = True
            await db.drop_table(table_name=f"webhook_{guild.id}")

        # テーブルの作成
        if create_table_flag:
            print(f'テーブル:webhook_{guild.id}を作成します')
            await db.create_table(
                table_name=f"webhook_{guild.id}",
                columns=WEBHOOK_COLUMNS
            )
        
        # テーブルの要素を取得
        table_fetch = await db.select_rows(
            table_name=f"webhook_{guild.id}",
            columns=[],
            where_clause={}
        )
        
        print(f'webhook_{guild.id}.pickleの書き込みをはじめます')
    
        # pickleに書き込むためdictに変換
        dict_row = [
            dict(zip(record.keys(), record)) 
            for record in table_fetch
        ]

        # 書き込み
        async with aiofiles.open(
            file=f'webhook_{guild.id}.pickle',
            mode='wb'
        ) as f:
            await f.write(pickle.dumps(obj=dict_row))

        print(f'webhook_{guild.id}.pickleの書き込みが終了しました')


    await db.disconnect()


async def get_discord_channel(
    guild_id:int,
    get_channel_type:List[int]
) -> List[Dict[str,Any]]:
    """
    Discordサーバ内のチャンネルを取得します。

    param:
    guild_id            :int
    Discordのサーバid

    get_channel_type    :List[int]
    取得するチャンネルtype
    空の場合、すべて取得する
    以下に説明を記す


    0:テキストチャンネル	
        Discordサーバのテキストチャンネル
    1:ダイレクトメッセージ	
        一ユーザへのダイレクトメッセージ
    2:ボイスチャンネル	
        Discordサーバのボイスチャンネル
    3:グループダイレクトメッセージ	
        複数のユーザから構成されるダイレクトメッセージ
    4:カテゴリーチャンネル	
        テキストチャンネルやボイスチャンネルをまとめる親チャンネル
    5:ギルドアナウンスチャンネル(旧ニュースチャンネル)	
        お気に入りにしたサーバの通知や、Discord公式の通知を受け取るチャンネル
    10:アナウンスチャンネル	
        5で作成されるスレッドチャンネル
    11:公開スレッドチャンネル	
        0で作成されるスレッドチャンネル
        公開に設定されている場合はこちら
    12:非公開スレッドチャンネル	
        0で作成されるスレッドチャンネル
        非公開に設定されている場合はこちら
    13:ステージチャンネル	
        ラジオのような聞き専のチャンネル
    14:ギルドディレクトリチャンネル	
        サーバ紹介をするチャンネル
        大規模なコミュニティサーバでのみ使用可能
        以下のリンクに使用例あり
        https://support.discord.com/hc/ja/articles/4406046651927-DIscord%E5%AD%A6%E7%94%9F%E3%83%8F%E3%83%96FAQ#:~:text=Discord%E5%AD%A6%E7%94%9F%E3%83%8F%E3%83%96%E3%81%AF%E3%80%81%E5%AD%A6%E7%94%9F,%E3%81%99%E3%82%8B%E3%81%93%E3%81%A8%E3%81%8C%E3%81%A7%E3%81%8D%E3%81%BE%E3%81%99%E3%80%82
    15:フォーラムチャンネル	
        特定の話題について議論するチャンネル
    """
    # サーバのチャンネル一覧を取得
    all_channel = await aio_get_request(
        url = DISCORD_BASE_URL + f'/guilds/{guild_id}/channels',
        headers = {
            'Authorization': f'Bot {DISCORD_BOT_TOKEN}'
        }
    )

    # 空の場合、すべてのチャンネルを格納
    if len(get_channel_type) == 0:
        all_channel_filter = [
            channel
            for channel in all_channel
        ]
    else:
        # 該当するチャンネルだけ格納
        all_channel_filter = [
            channel
            for channel in all_channel
            if channel['type'] in get_channel_type
        ]

    return all_channel_filter