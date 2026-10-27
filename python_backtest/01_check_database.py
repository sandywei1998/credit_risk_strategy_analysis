
from pathlib import Path
import sqlite3

# 获取当前 Python 文件所在的目录
project_dir = Path(__file__).resolve().parent.parent

# 查找项目目录中的 SQLite 数据库文件
db_files = []

for pattern in ("*.db", "*.sqlite", "*.sqlite3"):
    db_files.extend(project_dir.rglob(pattern))

# 如果没有找到数据库，提示检查路径
if not db_files:
    print("没有找到 SQLite 数据库文件。")
    print("请检查数据库是否放在项目文件夹内。")

else:
    print("找到以下数据库文件：")

    for i, file in enumerate(db_files, start=1):
        print(f"{i}. {file}")

    # 如果只找到一个数据库，自动使用它
    if len(db_files) == 1:
        db_path = db_files[0]

        print(f"\n正在读取：{db_path}")

        # 只读取，不修改数据库
        with sqlite3.connect(
            f"file:{db_path.as_posix()}?mode=ro",
            uri=True
        ) as conn:

            cursor = conn.cursor()

            cursor.execute("""
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                ORDER BY name;
            """)

            tables = cursor.fetchall()

            print("\n数据库中的数据表：")

            for table in tables:
                print("-", table[0])

    else:
        print("\n找到了多个数据库，请先确认哪一个是原始项目数据库。")