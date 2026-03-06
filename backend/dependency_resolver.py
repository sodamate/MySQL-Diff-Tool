"""
依赖关系解析器 - 智能排序表和视图的创建顺序
解决备份文件中表/视图顺序混乱的问题
"""

from collections import defaultdict, deque


class DependencyResolver:
    def __init__(self, conn, database):
        self.conn = conn
        self.database = database
        self.graph = defaultdict(list)
        self.in_degree = {}

    def get_table_fk_dependencies(self, table_name):
        """获取表的外键依赖"""
        with self.conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT REFERENCED_TABLE_NAME 
                FROM information_schema.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = %s 
                  AND TABLE_NAME = %s
                  AND REFERENCED_TABLE_NAME IS NOT NULL
            """,
                (self.database, table_name),
            )
            return [row["REFERENCED_TABLE_NAME"] for row in cursor.fetchall()]

    def get_view_dependencies(self, view_name):
        """解析视图依赖的表/视图（使用官方元数据）"""
        with self.conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT DISTINCT REFERENCED_TABLE_NAME
                FROM information_schema.VIEW_TABLE_USAGE
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
            """,
                (self.database, view_name),
            )
            return [row["REFERENCED_TABLE_NAME"] for row in cursor.fetchall()]

    def build_dependency_graph(self, tables, views):
        """构建依赖图"""
        all_objects = tables + views

        # 初始化入度
        for obj in all_objects:
            self.in_degree[obj] = 0

        # 表的外键依赖
        for table in tables:
            deps = self.get_table_fk_dependencies(table)
            for dep in deps:
                if dep in all_objects:
                    self.graph[dep].append(table)
                    self.in_degree[table] += 1

        # 视图的依赖
        for view in views:
            deps = self.get_view_dependencies(view)
            for dep in deps:
                if dep in all_objects:
                    self.graph[dep].append(view)
                    self.in_degree[view] += 1

    def topological_sort(self):
        """拓扑排序（Kahn算法）"""
        queue = deque(
            [node for node, degree in self.in_degree.items() if degree == 0])
        sorted_result = []

        while queue:
            current = queue.popleft()
            sorted_result.append(current)

            for neighbor in self.graph[current]:
                self.in_degree[neighbor] -= 1
                if self.in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # 检测循环依赖
        if len(sorted_result) != len(self.in_degree):
            remaining = [k for k, v in self.in_degree.items() if v > 0]
            raise ValueError(f"检测到循环依赖: {', '.join(remaining)}")

        return sorted_result


def sort_objects_by_dependency(conn, database, object_names):
    """
    智能排序：按依赖关系对表和视图排序

    Args:
        conn: 数据库连接
        database: 数据库名
        object_names: 对象名列表（表+视图）

    Returns:
        排序后的对象名列表
    """
    if not object_names:
        return []

    # 分离表和视图
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT TABLE_NAME, TABLE_TYPE
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME IN ({})
        """.format(",".join(["%s"] * len(object_names))),
            [database] + object_names,
        )

        results = cursor.fetchall()
        tables = [r["TABLE_NAME"]
                  for r in results if r["TABLE_TYPE"] == "BASE TABLE"]
        views = [r["TABLE_NAME"] for r in results if r["TABLE_TYPE"] == "VIEW"]

    resolver = DependencyResolver(conn, database)
    resolver.build_dependency_graph(tables, views)

    try:
        return resolver.topological_sort()
    except ValueError as e:
        print(f"⚠️ 警告: {str(e)}")
        return tables + views
