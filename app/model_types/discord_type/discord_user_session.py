from pydantic import BaseModel,validator
from typing import List,Optional,Union,Any

class DiscordOAuthData(BaseModel):
    """
    DiscordのOAuth2認証のデータ

    param:
    access_token    :str
        ユーザのアクセストークン
    expires_in      :int
        アクセストークンの有効期限(秒)
    refresh_token   :str
        リフレッシュトークン
    scope           :str
        許可されている権限
    token_type      :str
        トークンのタイプ
        Bearer
    """
    access_token    :str
    expires_in      :int
    refresh_token   :str
    scope           :str
    token_type      :str


class DiscordUser(BaseModel):
    """
    ユーザ情報

    param:
    id                  :int
        ユーザid
    username            :str
        ユーザ名
    global_name         :Union[str,None]

    display_name        :Union[str,None]

    avatar              :str
        アバターid
    avatar_decoration   :Union[str,None]
        アバターの説明
    discriminator       :str
        ユーザ名の識別子
    public_flags        :int

    flags               :int

    banner              :Union[str,None]
        プロフィールのバナー
    banner_color        :Union[str,None]
        プロフィールのバナーのカラーコード
    accent_color        :int

    locale              :str
        言語
    mfa_enabled         :bool

    premium_type        :int
        Nitroユーザのランク
    email               :str
        ユーザが登録しているメールアドレス
    verified            :Optional[bool]
        認証済みかどうか
    bio                 :Optional[str]
    """
    id                  :int
    username            :str
    global_name         :Union[str,None]
    display_name        :Union[str,None]
    avatar              :Optional[str]
    avatar_decoration   :Union[str,None]
    discriminator       :str
    public_flags        :int
    flags               :int
    banner              :Union[str,None]
    banner_color        :Union[str,None]
    accent_color        :Optional[int]
    locale              :str
    mfa_enabled         :bool
    premium_type        :int
    email               :Optional[str]
    verified            :Optional[bool]
    bio                 :Optional[str]

class DiscordConnection(BaseModel):
    """
    Discordのアカウント連携情報

    param:
    type                :str
        連携しているサービス名(Twitter,Github)
    id                  :str
        サービスでのユーザid
    name                :str
        サービスでのユーザ名
    visibility          :int
    friend_sync         :bool
    show_activity       :bool
    verified            :bool
    two_way_link        :bool
    metadata_visibility :int
    """
    type                :str
    id                  :str
    name                :str
    visibility          :int
    friend_sync         :bool
    show_activity       :bool
    verified            :bool
    two_way_link        :bool
    metadata_visibility :int


class MatchGuild(BaseModel):
    """
    Botとユーザが所属のサーバーのクラス

    id              :int
    name            :str
    icon            :str
    owner           :bool
    permissions     :int
    features        :List
    permissions_new :int
    """
    id              :int
    name            :str
    icon            :str
    owner           :bool
    permissions     :int
    features        :List[str]
    permissions_new :int


class ThreadMetadata(BaseModel):
    """
    スレッドのメタデータ

    archived                :bool
        アーカイブされたいるかどうか
    archive_timestamp       :str
        アーカイブされた日時
    auto_archive_duration   :int
        アーカイブまでの残り秒数
    locked                  :bool
        ロックされているか
    create_timestamp        :str
        作成日時
    """
    archived                :bool
    archive_timestamp       :str
    auto_archive_duration   :int
    locked                  :bool
    create_timestamp        :str

class Threads(BaseModel):
    """
    スレッド

    id                  :int
        スレッドid
    type                :int
        チャンネルタイプ
    last_message_id     :int
        最後の投稿id
    flags               :int
        用途不明
    guild_id            :int
        サーバーid
    name                :str
        スレッド名
    parent_id           :int
        親チャンネルのid
    rate_limit_per_user :int
        レートリミット?
    bitrate             :int
        ビットレート
    user_limit          :int
        ユーザリミット
    rtc_region          :str
        リージョン
    owner_id            :int
        ?
    thread_metadata     :ThreadMetadata
        スレッドのメタデータ
    message_count       :int
        スレッドのメッセージ数
    member_count        :int
        スレッドのメンバー数
    total_message_sent  :int
        トータルでのメッセージ数
    """
    id                  :int
    type                :int
    last_message_id     :int
    flags               :int
    guild_id            :int
    name                :str
    parent_id           :int
    rate_limit_per_user :int
    bitrate             :int
    user_limit          :int
    rtc_region          :str
    owner_id            :int
    thread_metadata     :ThreadMetadata
    message_count       :int
    member_count        :int
    total_message_sent  :int

class DiscordGuild(BaseModel):
    """
    Discordのサーバークラス
    使いません
    """
    id                              :int
    name                            :str
    icon                            :str
    description                     :Optional[str]
    home_header                     :Optional[str]
    splash                          :Optional[str]
    discovery_splash                :Optional[str]
    features                        :List[str]
    banner                          :Optional[str]
    owner_id                        :int
    application_id                  :Optional[int]
    region                          :Optional[str]
    afk_channel_id                  :Optional[int]
    afk_timeout                     :int
    system_channel_id               :Optional[int]
    system_channel_flags            :int
    widget_enabled                  :bool
    widget_channel_id               :Optional[int]
    verification_level              :int
    roles                           :List
    default_message_notifications   :int
    mfa_level                       :int
    explicit_content_filter         :int
    max_presences                   :Optional[int]
    max_members                     :int
    max_stage_video_channel_users   :Optional[int]
    max_video_channel_users         :Optional[int]
    vanity_url_code                 :Optional[str]
    premium_tier                    :int
    premium_subscription_count      :int
    preferred_locale                :str
    rules_channel_id                :Optional[int]
    safety_alerts_channel_id        :Optional[int]
    public_updates_channel_id       :Optional[int]
    hub_type                        :Optional[str]
    premium_progress_bar_enabled    :bool
    latest_onboarding_question_id   :Optional[int]
    nsfw                            :bool
    nsfw_level                      :int
    emojis                          :List
    stickers                        :List
    incidents_data                  :Any
    inventory_settings              :Any
    embed_enabled                   :bool
    embed_channel_id                :Optional[int]