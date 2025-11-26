# Database Web Console

## 功能与场景
- 依托本机的 MySQL 环境运行，可直接复用你在 MySQL Workbench 中配置好的数据库实例（确保服务已启动并可本地连接）。
- 通过网页操作数据库：查看表结构与预览数据、运行任意 SQL（支持 DDL/DML/SELECT，显示耗时与影响行数）。

## 环境准备
- 安装 Python 3.10+。建议使用虚拟环境：`python -m venv .venv && .\.venv\Scripts\activate`
- 安装依赖：`python install_package.py`，需要强制更新时可加 `--upgrade`

## 数据库连接配置
- 直接编辑 `db_config.ini`：填写 `host`、`port`、`user`、`database`，`password` 可选；`auto_connect` 设为 `True`/`False`
- 也可在网页端输入连接信息，连接成功会自动写回 `db_config.ini`

## 运行
```bash
python app.py
```
- 打开 `http://127.0.0.1:5000`
- 在 “Database Connection” 面板输入连接信息后点击 “Connect to Database”
- 连接成功后可：
  - 在 “Browse Tables” 查看当前库的表并快速预览数据
  - 在 “Custom SQL” 执行自定义 SQL，返回结果/受影响行数与耗时

## 其他说明
- 不再提供任务数据的自动导入脚本，也不依赖 Task6/7/8 SQL 文件
- 需要清理指定数据库时，可使用 `clear_data.py`（按 `db_config.ini` 中的数据库名操作，谨慎执行）
- 依赖清单见 `install_package.py`
