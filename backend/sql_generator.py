from typing import Dict, List, Any
from schema_diff import SchemaDiff


class SQLGenerator:
    @staticmethod
    def generate_column_sql(table: str, diff: Dict[str, List]) -> List[str]:
        sqls = []

        for col in diff.get("added", []):
            null_clause = "NULL" if col["Null"] == "YES" else "NOT NULL"
            default_clause = f"DEFAULT {col['Default']}" if col["Default"] else ""
            sqls.append(
                f"ALTER TABLE `{table}` ADD COLUMN `{col['Field']}` "
                f"{col['Type']} {null_clause} {default_clause};"
            )

        for col in diff.get("removed", []):
            sqls.append(f"ALTER TABLE `{table}` DROP COLUMN `{col['Field']}`;")

        for item in diff.get("modified", []):
            col = item["source"]
            null_clause = "NULL" if col["Null"] == "YES" else "NOT NULL"
            default_clause = f"DEFAULT {col['Default']}" if col["Default"] else ""
            sqls.append(
                f"ALTER TABLE `{table}` MODIFY COLUMN `{col['Field']}` "
                f"{col['Type']} {null_clause} {default_clause};"
            )

        return sqls

    @staticmethod
    def generate_index_sql(table: str, diff: Dict[str, List]) -> List[str]:
        sqls = []

        for idx_name in diff.get("added", []):
            sqls.append(f"-- Add index: {idx_name} (manual creation required)")

        for idx_name in diff.get("removed", []):
            if idx_name != "PRIMARY":
                sqls.append(f"ALTER TABLE `{table}` DROP INDEX `{idx_name}`;")

        return sqls

    @staticmethod
    def generate_data_sql(
        table: str, diff: Dict[str, Any], pk_cols: List[str]
    ) -> List[str]:
        sqls = []

        for row in diff.get("added", []):
            cols = ", ".join([f"`{k}`" for k in row.keys()])
            vals = ", ".join([SQLGenerator._format_value(v) for v in row.values()])
            sqls.append(f"INSERT INTO `{table}` ({cols}) VALUES ({vals});")

        for row in diff.get("removed", []):
            where_clause = " AND ".join(
                [f"`{col}` = {SQLGenerator._format_value(row[col])}" for col in pk_cols]
            )
            sqls.append(f"DELETE FROM `{table}` WHERE {where_clause};")

        for item in diff.get("modified", []):
            s_row = item["source"]
            set_clause = ", ".join(
                [
                    f"`{k}` = {SQLGenerator._format_value(v)}"
                    for k, v in s_row.items()
                    if k not in pk_cols
                ]
            )
            where_clause = " AND ".join(
                [
                    f"`{col}` = {SQLGenerator._format_value(s_row[col])}"
                    for col in pk_cols
                ]
            )
            sqls.append(f"UPDATE `{table}` SET {set_clause} WHERE {where_clause};")

        return sqls

    @staticmethod
    def _format_value(val: Any) -> str:
        if val is None:
            return "NULL"
        elif isinstance(val, (int, float)):
            return str(val)
        else:
            escaped = str(val).replace("'", "''")
            return f"'{escaped}'"

    @staticmethod
    def generate_schema_sync_sql(
        source_conn,
        target_conn,
        source_db: str,
        target_db: str,
        schema_diff: Dict[str, Any],
    ) -> str:
        """
        生成整库架构同步SQL（智能排序）

        Args:
            source_conn: 源数据库连接
            target_conn: 目标数据库连接
            source_db: 源数据库名
            target_db: 目标数据库名
            schema_diff: 架构差异数据

        Returns:
            完整的同步SQL脚本
        """
        from dependency_resolver import sort_objects_by_dependency

        sql_parts = []
        sql_parts.append(f"-- ==========================================\n")
        sql_parts.append(f"-- 数据库架构同步脚本\n")
        sql_parts.append(f"-- 源库: {source_db}\n")
        sql_parts.append(f"-- 目标库: {target_db}\n")
        sql_parts.append(f"-- ==========================================\n\n")

        # 提取所有源库对象
        all_source_tables = []
        all_source_views = []

        for item in schema_diff.get("source_only", []):
            if item["type"] == "table":
                all_source_tables.append(item["name"])
            elif item["type"] == "view":
                all_source_views.append(item["name"])

        for item in schema_diff.get("different", []):
            if item["type"] == "table":
                all_source_tables.append(item["name"])
            elif item["type"] == "view":
                all_source_views.append(item["name"])

        # 智能排序（考虑依赖关系）
        try:
            all_objects = all_source_tables + all_source_views
            sorted_objects = sort_objects_by_dependency(
                source_conn, source_db, all_objects
            )
            sql_parts.append("-- ✓ 已自动排序（依赖关系）\n\n")
        except Exception as e:
            sql_parts.append(f"-- ⚠ 依赖排序失败: {str(e)}\n")
            sql_parts.append(f"-- 使用降级策略：表在前，视图在后\n\n")
            sorted_objects = all_source_tables + all_source_views

        # 阶段1: 删除目标库中多余的视图（逆序）
        target_only_views = [
            item["name"]
            for item in schema_diff.get("target_only", [])
            if item["type"] == "view"
        ]
        if target_only_views:
            sql_parts.append(
                "-- ==================== 阶段1: 删除多余视图 ====================\n"
            )
            for view in reversed(target_only_views):
                sql_parts.append(f"DROP VIEW IF EXISTS `{target_db}`.`{view}`;\n")
            sql_parts.append("\n")

        # 阶段2: 删除目标库中多余的表
        target_only_tables = [
            item["name"]
            for item in schema_diff.get("target_only", [])
            if item["type"] == "table"
        ]
        if target_only_tables:
            sql_parts.append(
                "-- ==================== 阶段2: 删除多余表 ====================\n"
            )
            for table in target_only_tables:
                sql_parts.append(f"DROP TABLE IF EXISTS `{target_db}`.`{table}`;\n")
            sql_parts.append("\n")

        # 阶段3: 按依赖顺序创建/修改对象
        sql_parts.append(
            "-- ==================== 阶段3: 同步对象（按依赖顺序） ====================\n"
        )

        for obj_name in sorted_objects:
            # 判断对象类型
            obj_type = None
            is_different = False
            is_source_only = False

            for item in schema_diff.get("different", []):
                if item["name"] == obj_name:
                    obj_type = item["type"]
                    is_different = True
                    break
            if not obj_type:
                for item in schema_diff.get("source_only", []):
                    if item["name"] == obj_name:
                        obj_type = item["type"]
                        is_source_only = True
                        break

            if not obj_type:
                continue

            sql_parts.append(f"-- {obj_type.upper()}: {obj_name}\n")

            if obj_type == "table":
                if is_source_only:
                    # 源库新增的表：直接创建
                    with source_conn.cursor() as cursor:
                        cursor.execute(f"SHOW CREATE TABLE `{source_db}`.`{obj_name}`")
                        result = cursor.fetchone()
                        create_stmt = (
                            result.get("Create Table") or list(result.values())[1]
                        )
                    # 替换数据库名
                    create_stmt = create_stmt.replace(
                        f"`{source_db}`.", f"`{target_db}`."
                    )
                    sql_parts.append(f"{create_stmt};\n\n")
                elif is_different:
                    # 表结构不同：使用 ALTER 语句增量修改
                    # 获取源库和目标库的表结构
                    with source_conn.cursor() as cursor:
                        cursor.execute(f"SHOW COLUMNS FROM `{source_db}`.`{obj_name}`")
                        source_cols = cursor.fetchall()
                        cursor.execute(f"SHOW INDEX FROM `{source_db}`.`{obj_name}`")
                        source_indexes = cursor.fetchall()

                    with target_conn.cursor() as cursor:
                        cursor.execute(f"SHOW COLUMNS FROM `{target_db}`.`{obj_name}`")
                        target_cols = cursor.fetchall()
                        cursor.execute(f"SHOW INDEX FROM `{target_db}`.`{obj_name}`")
                        target_indexes = cursor.fetchall()

                    # 对比列差异
                    col_diff = SchemaDiff.compare_columns(source_cols, target_cols)
                    # 对比索引差异
                    idx_diff = SchemaDiff.compare_indexes(
                        source_indexes, target_indexes
                    )

                    # 生成修改语句
                    sql_parts.extend(
                        SQLGenerator.generate_column_sql(obj_name, col_diff)
                    )
                    sql_parts.extend(
                        SQLGenerator.generate_index_sql(obj_name, idx_diff)
                    )
                    if col_diff or idx_diff:
                        sql_parts.append("\n")
            else:  # view
                # 视图：无论新增还是修改，都使用删除重建方式（视图定义通常是整体替换）
                with source_conn.cursor() as cursor:
                    cursor.execute(f"SHOW CREATE VIEW `{source_db}`.`{obj_name}`")
                    result = cursor.fetchone()
                    create_stmt = result.get("Create View") or list(result.values())[1]

                sql_parts.append(f"DROP VIEW IF EXISTS `{target_db}`.`{obj_name}`;\n")
                # 替换数据库名
                create_stmt = create_stmt.replace(f"`{source_db}`.", f"`{target_db}`.")
                sql_parts.append(f"{create_stmt};\n\n")

        sql_parts.append("-- ==========================================\n")
        sql_parts.append("-- 同步完成\n")
        sql_parts.append("-- ==========================================\n")

        return "".join(sql_parts)
