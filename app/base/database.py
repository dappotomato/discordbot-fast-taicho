import asyncpg
from asyncpg.connection import Connection
from asyncpg.exceptions import DuplicateTableError
import asyncio
import os

from typing import List,Dict,Any,Union,Tuple

from dotenv import load_dotenv
load_dotenv()


class DataBaseNotConnect(Warning):...

class PostgresDB:
    def __init__(
            self,
            user:str,
            password:str,
            database:str,
            host:str
    ):
        """
        PostgreSQLのクラス

        user    :str
            Postgresのユーザー名
        password:str
            パスワード
        database:str
            データベースの名前
        host    :str
            ホスト番号
        conn    :Connection
            データベースの接続情報
        """
        self.user = user
        self.password = password
        self.database = database
        self.host = host
        self.conn:Connection = None

    async def connect(self):
        """
        PostgreSQLへ接続
        """
        self.conn = await asyncpg.connect(
            user=self.user,
            password=self.password,
            database=self.database,
            host=self.host
        )

    async def disconnect(self):
        """
        PostgreSQLの切断
        """
        if self.conn == None:
            raise DataBaseNotConnect
        await self.conn.close()

    async def create_table(self, table_name:str, columns:dict) -> str:
        """
        テーブルの作成

        table_name  :str
            作成するテーブル名
        colums      :dict
            テーブル内の名前と型
        """
        if self.conn == None:
            raise DataBaseNotConnect
        columns_str = ', '.join(
            [
                f"{column_name} {data_type}" for column_name, data_type in columns.items()
            ]
        )
        sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({columns_str});"
        try:
            await self.conn.execute(sql)
            return "ok"
        except DuplicateTableError:
            return "DuplicateTableError"

    async def drop_table(self, table_name:str) -> None:
        """
        テーブルの削除

        table_name:str
            削除するテーブルの名前
        """
        sql = f"DROP TABLE IF EXISTS {table_name};"
        await self.conn.execute(sql)

    async def select_rows(
        self,
        table_name:str,
        columns:List[str]=None,
        where_clause:dict=None
    ) -> List:
        """
        テーブルの参照

        table_name  :str
            参照するテーブルの名前
        columns     :List[str]
            参照する列、指定がない場合すべてを参照
        where_clause:dict
            条件、指定しない場合はすべて取得

        return:

        list        :List[Any]
        """
        if self.conn == None:
            raise DataBaseNotConnect
        if columns is None or len(columns) == 0:
            columns_str = '*'
        else:
            columns_str = ', '.join(columns)

        if where_clause is None:
            sql = f"SELECT {columns_str} FROM {table_name};"
        else:
            where_clause_str = ' AND '.join(
                [
                    f"{column}=${i+1}" for i, column in enumerate(
                        where_clause.keys()
                    )
                ]
            )
            where_clause_values = list(where_clause.values())
            sql = f"SELECT {columns_str} FROM {table_name} "
            if where_clause_str:
                sql += f"WHERE {where_clause_str};"
            else:
                sql += ";"

        try:
            return await self.conn.fetch(sql, *where_clause_values)
        except asyncpg.exceptions.UndefinedTableError:
            return [f"{table_name} does not exist"]

    async def insert_row(
        self,
        table_name:str,
        row_values:dict
    ) -> bool:
        """
        行の追加

        table_name:str
            対象のテーブルの名前
        row_values:dict
            追加する行の内容
        """
        if self.conn == None:
            raise DataBaseNotConnect
        columns_str = ', '.join(row_values.keys())
        values_str = ', '.join(
            [
                f"${i+1}" for i in range(len(row_values))
            ]
        )
        sql = f"INSERT INTO {table_name} ({columns_str}) VALUES ({values_str});"
        try:
            await self.conn.execute(sql, *row_values.values())
            return True
        except asyncpg.exceptions.UniqueViolationError:
            return False

    async def batch_insert_row(
        self,
        table_name: str,
        row_values: List[Dict[str, Any]]
    ) -> None:
        """
        行を一気に作成
        """
        if self.conn == None:
            raise DataBaseNotConnect

        #print(row_values)

        columns = row_values[0].keys()

        values = [
            tuple(
                row[col]
                for col in columns
            )
            for row in row_values
        ]

        #print(columns)
        #print(values)

        await self.conn.copy_records_to_table(
            table_name=table_name,
            records=values
        )

    async def update_row(
        self,
        table_name:str,
        row_values:dict,
        where_clause:dict
    ) -> None:
        """
        行の更新

        table_name  :str
            テーブルの名前
        row_values  :dict
            更新の内容
        where_clause:dict
            条件
        """
        if self.conn == None:
            raise DataBaseNotConnect

        """
        set_clause = []
        for column, value in row_values.items():
            if isinstance(value, (list, tuple)) and array_append:
                set_clause.append(f"{column} = array_cat({column}, $1)")
            else:
                if column in set_clause:
                    set_index = set_clause.index(column)
                else:
                    set_index = 0
                set_clause.append(f"{column} = ${len(where_clause) + set_index + 1}")
        set_clause_str = ', '.join(set_clause)
        """


        set_clause_str = ', '.join(
            [
                f"{column}=${i+1}" for i, column in enumerate(
                    row_values.keys()
                )
            ]
        )

        where_clause_str = ' AND '.join(
            [
                f"{column}=${i+len(row_values)+1}" for i, column in enumerate(
                    where_clause.keys()
                )
            ]
        )
        values = list(row_values.values()) + list(where_clause.values())
        sql = f"UPDATE {table_name} SET {set_clause_str} "
        if where_clause_str:
            sql += f"WHERE {where_clause_str};"
        else:
            sql += ";"
        await self.conn.execute(sql, *values)

    async def primary_batch_update_rows(
        self,
        table_name: str,
        set_values_and_where_columns: List[Dict],
        table_colum:Dict
    ) -> None:
        """
        updateを複数行う

        param:
        tabel_name                  : str
            更新するテーブル名

        set_values_and_where_columns: List[Dict],
            更新する値と条件の辞書型配列
            それぞれに更新する行と、更新する内容を記述する
            必ず以下のような構造にすること
            また、where_clauseは主キーを指定し、重複させないこと

            set_values_and_where_columns = [
                {
                    'where_clause': {'channel_id': 0},
                    'row_values': {'カラム名': '値'},
                },
                {
                    'where_clause': {'channel_id': 1},
                    'row_values': {'カラム名': '値'},
                },
                {
                    'where_clause': {'channel_id': 2},
                    'row_values': {'カラム名': '値', 'カラム名': '値'},
                },
            ]

        table_colum                 : Dict
            テーブルのカラム一覧
            Postgresでcreateしたときのものを辞書型で表現すること

            table_colum = {
                'channel_id': 'NUMERIC PRIMARY KEY',
                'guild_id': 'NUMERIC',
                'line_ng_channel': 'boolean',
                'ng_message_type': 'VARCHAR(50)[]',
                'message_bot': 'boolean',
                'ng_users':'NUMERIC[]'
            }

        """
        # テーブル名と列名のリストを取得
        columns = table_colum.keys()

        # 主キーを取り出す
        primary_key = [
            key
            for key,value in table_colum.items()
            if 'PRIMARY KEY' in value
        ]

        updates = set_values_and_where_columns

        # SET 句の文字列を構築
        set_clauses = []
        # はじめに条件となる主キーを代入
        values = [w['where_clause'][primary_key[0]] for w in updates]
        values_len = [w['where_clause'][primary_key[0]] for w in updates]

        # 主キーの数でパラメータの初期値を決める
        param_count = len(values_len) + 1

        for i, column in enumerate(columns):
            set_clause = f"{column} = CASE "
            # case文に入るカラムがあるかのフラグ
            set_clause_flag = False

            for j, update in enumerate(updates):
                # 更新するカラムがあった場合
                if update['row_values'].get(column) is not None:
                    # フラグを挙げる
                    set_clause_flag = True
                    # $param_count $param_count + 1
                    set_clause += f"WHEN {primary_key[0]} = ${param_count} THEN ${param_count + 1} "
                    # 上記の数だけ2足す
                    param_count += 2
                    values.append(update['where_clause'][primary_key[0]])
                    values.append(update['row_values'][column])

                    #print(update['where_clause'][primary_key[0]],column,update['row_values'][column])

            set_clause += f"ELSE {column} END"
            # case文が書かれていた場合、配列に追加
            if set_clause_flag:
                set_clauses.append(set_clause)

        # WHERE 句の文字列を構築
        where_clause = f"{primary_key[0]} IN (" + ", ".join(
            f"${i + 1}" for i in range(len(values_len))
        ) + ")"

        # SQL 文の構築
        sql = f"UPDATE {table_name} SET \n{', '.join(set_clauses)} WHERE {where_clause}"

        await self.conn.execute(sql, *values)

    async def delete_row(
        self,
        table_name:str,
        where_clause:dict
    ) -> None:
        """
        行の削除

        param:
        table_name  :str
            テーブルの名前
        where_clause:dict
            条件

        """
        if self.conn == None:
            raise DataBaseNotConnect
        where_clause_str = ' AND '.join(
            [
                f"{column}=${i+1}" for i, column in enumerate(
                    where_clause.keys()
                )
            ]
        )
        where_clause_values = list(where_clause.values())
        sql = f"DELETE FROM {table_name} "
        if where_clause_str:
            sql += f"WHERE {where_clause_str};"
        else:
            sql += ";"
        await self.conn.execute(sql, *where_clause_values)

    async def free_sql(self,sql_syntax:str)-> List:
        """
        PostgreSQLの構文を文字列にしてそのまま実行する

        param:
        sql_syntax:str
        sqlの構文

        return:
        List
        selectは結果が帰ってくる
        """
        if self.conn == None:
            raise DataBaseNotConnect
        return await self.conn.fetch(sql_syntax)

    async def get_columns_type(
        self,
        table_name:str
    ) -> Dict:
        """
        指定されたテーブルの列の型を返す

        param:
        table_name  :str
            テーブルの名前

        return:
        List[Tuple[str,str]]
            行名と型の配列

        """
        query = f"""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = '{table_name}';
        """

        result = await self.conn.fetch(query)
        columns:List[Tuple[str,str]] = [
            (row['column_name'],row['data_type'])
            for row in result
        ]
        columns_dict:Dict = {}

        # ARRAY型の列の要素のデータ型を取得
        for i, (column_name,data_type) in enumerate(columns):
            # 初期の辞書型
            tmp_dict:Dict = {column_name:data_type}
            # 配列の場合
            if data_type.startswith('ARRAY'):
                query = f"""
                SELECT column_name, udt_name
                FROM information_schema.columns
                WHERE table_name = '{table_name}' AND column_name = '{column_name}'
                """

                result:List[Dict] = await self.conn.fetch(query)
                element_data_type:str = result[0]['udt_name']

                # 配列の場合(先頭に_がある)
                if element_data_type.startswith('_'):
                    element_data_type = element_data_type.replace('_','')
                    element_data_type = f'{element_data_type}[]'
                # 配列用に更新
                tmp_dict = {
                    column_name: element_data_type
                }

            # varcharの場合
            if data_type == 'character varying':
                tmp_dict = {
                    column_name: 'varchar'
                }
            columns_dict.update(tmp_dict)

        return columns_dict


async def main():
    import re
    import uuid
    user = os.getenv('PGUSER')
    password = os.getenv('PGPASSWORD')
    database = os.getenv('PGDATABASE')
    host = os.getenv('PGHOST')
    db = PostgresDB(
        user=user,
        password=password,
        database=database,
        host=host
    )
    # ローカル側のカラム(こちらに合わせる)
    columns = {
        'uuid':'UUID PRIMARY KEY',
        'guild_id': 'NUMERIC',
        'webhook_id':'NUMERIC',
        'subscription_type':'VARCHAR(50)',
        'subscription_id': 'VARCHAR(50)',
        'mention_roles':'NUMERIC[]',
        'mention_members':'NUMERIC[]',
        'ng_or_word':'VARCHAR(50)[]',
        'ng_and_word':'VARCHAR(50)[]',
        'search_or_word':'VARCHAR(50)[]',
        'search_and_word':'VARCHAR(50)[]',
        'mention_or_word':'VARCHAR(50)[]',
        'mention_and_word':'VARCHAR(50)[]',
        'created_at':'VARCHAR(50)'
    }

    new_columns:Dict = {
        'uuid':'',
        'guild_id': 0,
        'webhook_id':0,
        'subscription_type':'',
        'subscription_id': '',
        'mention_roles':[],
        'mention_members':[],
        'ng_or_word':[],
        'ng_and_word':[],
        'search_or_word':[],
        'search_and_word':[],
        'mention_or_word':[],
        'mention_and_word':[],
        'created_at':''
    }

    table_fetch = [
        {
            'uuid':uuid.UUID('e04ddf59-8f06-49e9-b0a1-b3a21724a22e'),
            'guild_id': 0,
            'webhook_id':0,
            'subscription_type':'twitter',
            'subscription_id': 'a',
            'mention_roles':[1],
            'mention_members':[1,2],
            'search_or_word':[],
            'search_and_word':[],
            'mention_or_word':[],
            'mention_and_word':[],
            'created_at':'Tue May 23 05:00:00 +0000 2022'
        },
        {
            'uuid':uuid.UUID('e04ddf59-8f06-49e9-b0a1-b3a21724a22e'),
            'guild_id': 0,
            'webhook_id':0,
            'subscription_type':'twitter',
            'subscription_id': 'a',
            'mention_roles':[1],
            'mention_members':[1,2],
            'search_or_word':[],
            'search_and_word':[],
            'mention_or_word':[],
            'mention_and_word':[],
            'created_at':'Tue May 23 05:00:00 +0000 2022'
        }
    ]

    set_columns:Dict = {}
    table_name='webhook_838937935822585928'
    await db.connect()

    # データベース側のカラム
    table_columns = await db.get_columns_type(table_name=table_name)
    print(table_columns)

    missing_items = [
        {key:value}
        for key,value in new_columns.items()
        if key not in table_columns.keys()
    ]
    for column_name,data_type in columns.items():
        table_data_type:str = table_columns.get(column_name)
        # (数字)が含まれていた場合、取り除く
        data_type:str = re.sub(r'\(\d+\)','',data_type)

        # データベース側になかった場合
        # 主キーで、変更があった場合
        if (table_data_type == None or
            table_data_type not in data_type.lower() and (
            'PRIMARY KEY' in data_type or
            'primary key' in data_type
            )):

            if isinstance(new_columns[column_name],list):
                new_columns[column_name] = tuple(new_columns[column_name])

            set_columns.update(
                {
                    column_name:new_columns[column_name]
                }
            )
        # 完全一致(大文字小文字区別せず)あった場合
        # 主キーで、変更がない場合
        elif (table_data_type == data_type.lower() or
            (table_data_type in data_type.lower() and (
            'PRIMARY KEY' in data_type or
            'primary key' in data_type
            ))):
            set_columns.update(
                {
                    column_name:'Unchanged'
                }
            )

    #print(set_columns.values())
    if (len(list(set_columns.values())) == 1 and
        list(set_columns.values())[0] == "Unchanged"):
        unchanged = True
    else:
        unchanged = False

    for i,table in enumerate(table_fetch):
        for table_key,table_value in table.items():
            if set_columns.get(table_key) == "Unchanged":
                table.update({table_key:table_value})

        for item in missing_items:
            for key,value in item.items():
                table.update({key:value})

        table_fetch[i] = table
        print(table)

    await db.disconnect()

    print(set_columns)
    #print(table_fetch)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
