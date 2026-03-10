from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List
import os
import json
import logging
from datetime import datetime

from db_connector import DBConnector
from schema_diff import SchemaDiff
from data_diff import DataDiff
from sql_generator import SQLGenerator

# 配置文件目录
CONFIG_DIR = os.path.join(os.path.dirname(__file__), "configs")
if not os.path.exists(CONFIG_DIR):
    os.makedirs(CONFIG_DIR)

# 上次连接配置文件
LAST_CONFIG_FILE = os.path.join(CONFIG_DIR, "last-connection.json")

app = FastAPI(title="MySQL Diff Tool")

# 配置日志输出到文件
log_dir = os.path.join(os.path.dirname(__file__), "logs")
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

log_file = os.path.join(log_dir, f"diff_tool_{datetime.now().strftime('%Y%m%d')}.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()  # 同时输出到控制台
    ]
)
logger = logging.getLogger(__name__)
logger.info(f"日志文件：{log_file}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class DBConfig(BaseModel):
    host: str
    port: int = 3306
    user: str
    password: str
    database: str = ""


class CompareRequest(BaseModel):
    source: DBConfig
    target: DBConfig
    source_table: str
    target_table: str
    compare_data: bool = True
    data_limit: Optional[int] = 10000


class SaveConfigRequest(BaseModel):
    name: str
    source: DBConfig
    target: DBConfig
    selectedSourceTable: str = ""
    selectedTargetTable: str = ""
    compareMode: str = "table"
    compareData: bool = True
    dataLimit: int = 10000
    createdAt: str = ""


@app.post("/api/get-databases")
async def get_databases(config: DBConfig):
    try:
        db = DBConnector(config.host, config.port,
                         config.user, config.password)
        db.connect()
        databases = db.get_databases()
        db.close()
        return {"success": True, "databases": databases}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/get-tables")
async def get_tables(config: DBConfig):
    try:
        if not config.database:
            raise HTTPException(
                status_code=400, detail="Database name is required")
        db = DBConnector(
            config.host, config.port, config.user, config.password, config.database
        )
        db.connect()
        tables = db.get_tables()
        db.close()
        return {"success": True, "tables": tables}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# 配置管理API
@app.get("/api/configs")
async def get_configs():
    try:
        configs = []
        if os.path.exists(CONFIG_DIR):
            for filename in os.listdir(CONFIG_DIR):
                if filename.endswith(".json"):
                    file_path = os.path.join(CONFIG_DIR, filename)
                    with open(file_path, "r", encoding="utf-8") as f:
                        config = json.load(f)
                        configs.append(config)

        # 按创建时间排序
        configs.sort(key=lambda x: x.get("createdAt", ""), reverse=True)
        return {"success": True, "configs": configs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/configs")
async def save_config(request: SaveConfigRequest):
    try:
        config_name = request.name.strip()
        if not config_name:
            raise HTTPException(status_code=400, detail="配置名称不能为空")

        config_data = request.dict()
        if not config_data.get("createdAt"):
            import datetime
            config_data["createdAt"] = datetime.datetime.now().isoformat()

        # 保存配置到文件
        filename = f"{config_name}.json"
        file_path = os.path.join(CONFIG_DIR, filename)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)

        return {"success": True, "message": f"配置 '{config_name}' 已保存"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/configs/{name}")
async def delete_config(name: str):
    try:
        filename = f"{name}.json"
        file_path = os.path.join(CONFIG_DIR, filename)

        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="配置文件不存在")

        os.remove(file_path)
        return {"success": True, "message": f"配置 '{name}' 已删除"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/last-config")
async def get_last_config():
    try:
        if os.path.exists(LAST_CONFIG_FILE):
            with open(LAST_CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
            return {"success": True, "config": config}
        else:
            return {"success": False, "message": "无上次连接配置"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/last-config")
async def save_last_config(request: SaveConfigRequest):
    try:
        config_data = request.dict()
        if not config_data.get("createdAt"):
            import datetime
            config_data["createdAt"] = datetime.datetime.now().isoformat()

        with open(LAST_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)

        return {"success": True, "message": "上次连接配置已保存"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/compare-schema")
async def compare_schema(request: CompareRequest):
    source_db = None
    target_db = None
    try:
        source_db = DBConnector(
            request.source.host,
            request.source.port,
            request.source.user,
            request.source.password,
            request.source.database,
        )
        target_db = DBConnector(
            request.target.host,
            request.target.port,
            request.target.user,
            request.target.password,
            request.target.database,
        )

        source_db.connect()
        target_db.connect()

        # 获取表和视图
        source_tables = source_db.get_tables()
        target_tables = target_db.get_tables()
        source_views = source_db.get_views()
        target_views = target_db.get_views()
        
        logger.info(f"开始对比 Schema...")
        logger.info(f"源库表数：{len(source_tables)}, 视图数：{len(source_views)}")
        logger.info(f"目标库表数：{len(target_tables)}, 视图数：{len(target_views)}")

        # 对比表
        table_diff = SchemaDiff.compare_tables(source_tables, target_tables)
        # 对比视图
        view_diff = SchemaDiff.compare_tables(source_views, target_views)

        results = {
            "table_diff": {
                "added": table_diff["added"] + view_diff["added"],
                "removed": table_diff["removed"] + view_diff["removed"],
                "common": table_diff["common"] + view_diff["common"],
            },
            "table_details": {},
            "view_list": source_views + [v for v in target_views if v not in source_views],
        }

        # 对比共同表的结构
        for table in table_diff["common"]:
            source_struct = source_db.get_table_structure(table)
            target_struct = target_db.get_table_structure(table)

            col_diff = SchemaDiff.compare_columns(
                source_struct["columns"], target_struct["columns"]
            )
            idx_diff = SchemaDiff.compare_indexes(
                source_struct["indexes"], target_struct["indexes"]
            )

            has_diff = (
                col_diff["added"]
                or col_diff["removed"]
                or col_diff["modified"]
                or idx_diff["added"]
                or idx_diff["removed"]
            )

            if has_diff:
                results["table_details"][table] = {
                    "columns": col_diff,
                    "indexes": idx_diff,
                }

        # 视图对比：先格式化 SQL，再进行字符串对比
        view_details = {}
        different_views = []
        
        for view in view_diff["common"]:
            source_def = source_db.get_view_definition(view)
            target_def = target_db.get_view_definition(view)
            
            # 标准化 SQL 格式后对比
            source_normalized = DBConnector.normalize_sql(source_def)
            target_normalized = DBConnector.normalize_sql(target_def)
            
            if source_normalized != target_normalized:
                logger.info(f"🔍 发现差异视图：{view}")
                logger.info(f"源视图标准化SQL：{source_normalized}")
                logger.info(f"目标视图标准化SQL：{target_normalized}")
                different_views.append(view)
                view_details[view] = {
                    "is_view": True,
                    "has_diff": True,
                    "source_definition": source_def,
                    "target_definition": target_def,
                }
        
        # 只有存在差异的视图才加入 table_details
        for view in different_views:
            results["table_details"][view] = view_details[view]

        # 构建 schema_diff_data，正确标记类型
        schema_diff_data = {
            "source_only": (
                [{"name": t, "type": "table"} for t in table_diff["added"]] +
                [{"name": v, "type": "view"} for v in view_diff["added"]]
            ),
            "target_only": (
                [{"name": t, "type": "table"} for t in table_diff["removed"]] +
                [{"name": v, "type": "view"} for v in view_diff["removed"]]
            ),
            "different": (
                [{"name": t, "type": "table"} for t in table_diff["common"] if t in results["table_details"]] +
                [{"name": v, "type": "view"} for v in different_views]  # 只有真正有差异的视图
            ),
        }

        sync_sql = SQLGenerator.generate_schema_sync_sql(
            source_db.connection,
            target_db.connection,
            request.source.database,
            request.target.database,
            schema_diff_data,
        )

        results["sync_sql"] = sync_sql.split("\n")
        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if source_db:
            source_db.close()
        if target_db:
            target_db.close()


@app.post("/api/compare")
async def compare_databases(request: CompareRequest):
    source_db = None
    target_db = None
    try:
        source_db = DBConnector(
            request.source.host,
            request.source.port,
            request.source.user,
            request.source.password,
            request.source.database,
        )
        target_db = DBConnector(
            request.target.host,
            request.target.port,
            request.target.user,
            request.target.password,
            request.target.database,
        )

        source_db.connect()
        target_db.connect()

        source_table = request.source_table
        target_table = request.target_table

        source_struct = source_db.get_table_structure(source_table)
        target_struct = target_db.get_table_structure(target_table)

        col_diff = SchemaDiff.compare_columns(
            source_struct["columns"], target_struct["columns"]
        )
        idx_diff = SchemaDiff.compare_indexes(
            source_struct["indexes"], target_struct["indexes"]
        )

        table_result = {"schema": {"columns": col_diff, "indexes": idx_diff}}

        sql_parts = []
        sql_parts.extend(SQLGenerator.generate_column_sql(
            target_table, col_diff))
        sql_parts.extend(SQLGenerator.generate_index_sql(
            target_table, idx_diff))

        if request.compare_data:
            source_pk_cols = source_db.get_primary_key(source_table)
            target_pk_cols = target_db.get_primary_key(target_table)

            if source_pk_cols and target_pk_cols:
                source_data = source_db.get_table_data(
                    source_table, request.data_limit)
                target_data = target_db.get_table_data(
                    target_table, request.data_limit)

                data_diff_result = DataDiff.compare_data(
                    source_data, target_data, source_pk_cols
                )
                table_result["data"] = data_diff_result

                sql_parts.extend(
                    SQLGenerator.generate_data_sql(
                        target_table, data_diff_result, source_pk_cols
                    )
                )

        results = {
            "source_table": source_table,
            "target_table": target_table,
            "table_details": table_result,
            "sync_sql": sql_parts,
        }
        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if source_db:
            source_db.close()
        if target_db:
            target_db.close()


frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/", StaticFiles(directory=frontend_path, html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
