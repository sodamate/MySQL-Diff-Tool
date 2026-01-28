# MySQL 数据库对比工具

替代 Navicat 数据库对比功能的 Web 工具。

## 功能特性

- ✅ 表结构对比（字段、索引、约束）
- ✅ 数据内容对比（行级差异）
- ✅ 跨数据库对比（开发环境 vs 生产环境）
- ✅ 生成 HTML 差异报告
- ✅ 自动生成同步 SQL 脚本
- ✅ Web 界面操作

## 安装步骤

### 1. 安装依赖

```bash
cd mysql-diff-tool
pip install -r requirements.txt
```

### 2. 启动服务

```bash
cd backend
python main.py
```

服务将在 `http://localhost:8000` 启动。

## 使用方法

1. 打开浏览器访问 `http://localhost:8000`
2. 分别填写源数据库和目标数据库的连接信息
3. 点击"测试连接"验证配置
4. 选择是否对比数据内容（可设置行数限制）
5. 点击"开始对比"执行对比
6. 查看结果：
   - **表结构差异**：新增/删除/修改的字段和索引
   - **数据差异**：新增/删除/修改的记录统计
   - **同步SQL脚本**：可下载的 SQL 文件

## 技术栈

- **后端**: FastAPI + Python 3.9+
- **数据库驱动**: PyMySQL
- **前端**: Vue 3 + Element Plus
- **模板引擎**: Jinja2

## 注意事项

- 数据对比默认限制 10000 行，可根据需要调整
- 大表对比建议关闭数据对比或降低行数限制
- 生成的 SQL 脚本建议在测试环境验证后再应用到生产环境

## 目录结构

```
mysql-diff-tool/
├── backend/
│   ├── main.py              # FastAPI 主应用
│   ├── db_connector.py      # 数据库连接管理
│   ├── schema_diff.py       # 结构对比逻辑
│   ├── data_diff.py         # 数据对比逻辑
│   └── sql_generator.py     # SQL 脚本生成
├── frontend/
│   ├── index.html           # 前端页面
│   └── app.js               # Vue 应用逻辑
└── requirements.txt         # Python 依赖
```