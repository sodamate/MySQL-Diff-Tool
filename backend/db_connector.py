import pymysql
import sqlparse
import re
from typing import Dict, List, Any, Optional


class DBConnector:
    _DANGEROUS_CHARS = re.compile(r'[`;\'"\\]|--')

    @staticmethod
    def _validate_identifier(name: str) -> str:
        if not name or DBConnector._DANGEROUS_CHARS.search(name):
            raise ValueError(f"Invalid identifier: {name}")
        return name

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
        table = self._validate_identifier(table)
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
        table = self._validate_identifier(table)
        query = f"SELECT * FROM `{table}`"
        if limit and isinstance(limit, int) and limit > 0:
            query += f" LIMIT {limit}"
        return self.execute_query(query)

    def get_primary_key(self, table: str) -> List[str]:
        table = self._validate_identifier(table)
        indexes = self.execute_query(
            f"SHOW INDEX FROM `{table}` WHERE Key_name = 'PRIMARY'"
        )
        return [idx["Column_name"] for idx in indexes]

    def get_databases(self) -> List[str]:
        query = "SHOW DATABASES"
        results = self.execute_query(query)
        exclude = ["information_schema", "mysql", "performance_schema", "sys"]
        return [row["Database"] for row in results if row["Database"] not in exclude]

    def get_views(self) -> List[str]:
        query = "SHOW FULL TABLES WHERE Table_type = 'VIEW'"
        results = self.execute_query(query)
        return [list(row.values())[0] for row in results]

    def get_view_definition(self, view: str) -> str:
        view = self._validate_identifier(view)
        result = self.execute_query(f"SHOW CREATE VIEW `{view}`")[0]
        return result.get("Create View") or list(result.values())[1]

    @staticmethod
    def normalize_sql(sql: str) -> str:
        """
        标准化 SQL语句格式，用于对比
        
        Args:
           sql: 原始 SQL语句
            
        Returns:
            格式化后的 SQL语句
        """
        if not sql:
            return sql
        
        # 使用 sqlparse 格式化 SQL
        formatted = sqlparse.format(
           sql,
            reindent=True,           # 重新缩进
            keyword_case='upper',    # 关键字转大写
            strip_whitespace=True,   # 去除多余空白
            strip_comments=False     # 保留注释
        )
        
        return formatted.strip()
