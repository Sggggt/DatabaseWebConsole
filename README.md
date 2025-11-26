# Database Web Console

## Setup
- 安装 Python 3.10+，推荐在虚拟环境中运行（`python -m venv .venv && .\\.venv\\Scripts\\activate`）。
- 安装依赖：`python install_package.py`（如需强制升级加 `--upgrade`）。

## Configure connection
- 编辑 `db_config.ini`，填入 host/port/user/database，password 可选，`auto_connect` 设置为 `True`/`False`。
- 也可以直接在网页中填写；连接成功后会自动写回到 `db_config.ini`。

## Run
```bash
python app.py
```
- 打开 `http://127.0.0.1:5000`。
- 在 “Database Connection” 面板输入连接信息并点击 “Connect to Database”。
- 连接后可以：
  - 在 “Browse Tables” 查看当前库中的表并快速预览数据；
  - 在 “Custom SQL” 运行任意 SQL（支持 SELECT/DDL/DML，返回受影响行数与耗时）。

## Notes
- 不再提供任务数据的自动导入脚本，也不再依赖 Task6/7/8 SQL 文件。
- 需要清理指定数据库时，可选择 `clear_data.py`（按 `db_config.ini` 中的数据库名工作，谨慎使用）。
- 依赖清单见 `install_package.py`。
