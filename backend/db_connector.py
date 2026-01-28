import pymysql
from typing import Dict, List, Any, Optional


class DBConnector:
    def __init__(
        self, host: str, port: int, user: str, password: str, database: str = ""
    ):
        self.config = {
            "host": host,
            "port": port,
            "user": user,
            "password": password,
            "charset": "utf8mb4",
            "cursorclass": pymysql.cursors.DictCursor,
        }
        if database:
            self.config["database"] = database
        self.connection = None

    def connect(self):
        self.connection = pymysql.connect(**self.config)
        return self.connection

    def close(self):
        if self.connection:
            self.connection.close()

    def execute_query(
        self, query: str, params: Optional[tuple] = None
    ) -> List[Dict[str, Any]]:
        if not self.connection:
            raise RuntimeError("Database connection not established")
        with self.connection.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()

    def get_tables(self) -> List[str]:
        query = "SHOW FULL TABLES WHERE Table_type = 'BASE TABLE'"
        results = self.execute_query(query)
        # SHOW FULL TABLES 返回两列，第一列是表名
        return [list(row.values())[0] for row in results]

    def get_table_structure(self, table: str) -> Dict[str, Any]:
        columns = self.execute_query(f"SHOW FULL COLUMNS FROM `{table}`")
        indexes = self.execute_query(f"SHOW INDEX FROM `{table}`")
        create_result = self.execute_query(f"SHOW CREATE TABLE `{table}`")[0]

        # SHOW CREATE TABLE 返回的键可能是 'Create Table' 或其他
        create_stmt = (
            create_result.get("Create Table")
            or create_result.get("create table")
            or list(create_result.values())[1]
        )

        return {"columns": columns, "indexes": indexes, "create_statement": create_stmt}

    def get_table_data(
        self, table: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        query = f"SELECT * FROM `{table}`"
        if limit:
            query += f" LIMIT {limit}"
        return self.execute_query(query)

    def get_primary_key(self, table: str) -> List[str]:
        indexes = self.execute_query(
            f"SHOW INDEX FROM `{table}` WHERE Key_name = 'PRIMARY'"
        )
        return [idx["Column_name"] for idx in indexes]

    def get_databases(self) -> List[str]:
        query = "SHOW DATABASES"
        results = self.execute_query(query)
        exclude = ["information_schema", "mysql", "performance_schema", "sys"]
        return [row["Database"] for row in results if row["Database"] not in exclude]

        def check_object_type(conn, database, object_name):
            """
            检查数据库对象类型

            Returns:
                'BASE TABLE' | 'VIEW' | None
            """
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT TABLE_TYPE 
                    FROM information_schema.TABLES 
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                """,
                    (database, object_name),
                )
                result = cursor.fetchone()
                return result["TABLE_TYPE"] if result else None

        def get_views(conn, database):
            """获取视图列表"""
            with conn.cursor() as cursor:
                cursor.execute(f"USE `{database}`")
                cursor.execute("SHOW FULL TABLES WHERE Table_type = 'VIEW'")
                return [row[0] for row in cursor.fetchall()]

        def is_view(conn, database, object_name):
            """判断对象是否为视图"""
            obj_type = check_object_type(conn, database, object_name)
            return obj_type == "VIEW"
