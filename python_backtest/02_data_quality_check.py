from pathlib import Path
import sqlite3


# 1. 定位项目目录和数据库
project_dir = Path(__file__).resolve().parent.parent
db_path = project_dir / "credit_risk.db"

if not db_path.exists():
    raise FileNotFoundError(f"没有找到数据库：{db_path}")

print("=" * 70)
print("信贷风险项目：数据质量检查")
print(f"数据库路径：{db_path}")
print("=" * 70)


def quote_identifier(name):
    """安全地引用 SQLite 表名或字段名。"""
    return '"' + name.replace('"', '""') + '"'


# 2. 以只读方式打开数据库
with sqlite3.connect(
    db_path.as_uri() + "?mode=ro",
    uri=True
) as conn:

    cursor = conn.cursor()

    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """)

    tables = [row[0] for row in cursor.fetchall()]

    if not tables:
        print("数据库中没有找到业务数据表。")

    # 3. 逐张表检查
    for table in tables:
        table_sql = quote_identifier(table)

        print("\n" + "=" * 70)
        print(f"数据表：{table}")
        print("=" * 70)

        # 读取字段结构
        cursor.execute(f"PRAGMA table_info({table_sql})")
        columns_info = cursor.fetchall()

        columns = [row[1] for row in columns_info]

        print("\n【字段结构】")
        print(f"{'字段名':<30} {'数据类型':<15} {'主键'}")

        for row in columns_info:
            column_name = row[1]
            data_type = row[2] or "未声明"
            is_primary_key = "是" if row[5] else "否"

            print(
                f"{column_name:<30} "
                f"{data_type:<15} "
                f"{is_primary_key}"
            )

        # 检查总行数
        cursor.execute(f"SELECT COUNT(*) FROM {table_sql}")
        row_count = cursor.fetchone()[0]

        print(f"\n【数据规模】")
        print(f"总行数：{row_count}")
        print(f"字段数：{len(columns)}")

        if row_count == 0 or not columns:
            print("表为空或没有字段，跳过后续检查。")
            continue

        # 检查每个字段的空值和空字符串
        print("\n【缺失值检查】")

        total_missing = 0

        for column in columns:
            column_sql = quote_identifier(column)

            cursor.execute(f"""
                SELECT COUNT(*)
                FROM {table_sql}
                WHERE {column_sql} IS NULL
                   OR TRIM(CAST({column_sql} AS TEXT)) = ''
            """)

            missing_count = cursor.fetchone()[0]
            total_missing += missing_count

            if missing_count > 0:
                print(f"{column}: {missing_count} 条缺失")
            else:
                print(f"{column}: 0 条缺失")

        print(f"各字段缺失单元格合计：{total_missing}")

        # 检查完全重复的记录
        print("\n【整行重复检查】")

        columns_sql = ", ".join(
            quote_identifier(column) for column in columns
        )

        cursor.execute(f"""
            SELECT COALESCE(SUM(n - 1), 0)
            FROM (
                SELECT COUNT(*) AS n
                FROM {table_sql}
                GROUP BY {columns_sql}
                HAVING COUNT(*) > 1
            )
        """)

        duplicate_rows = cursor.fetchone()[0]
        print(f"重复记录数（超出每组第一条的部分）：{duplicate_rows}")

        # 显示主键重复情况
        primary_keys = [
            row[1] for row in columns_info if row[5]
        ]

        if primary_keys:
            print("\n【主键重复检查】")

            primary_key_sql = ", ".join(
                quote_identifier(column) for column in primary_keys
            )

            cursor.execute(f"""
                SELECT COUNT(*)
                FROM (
                    SELECT {primary_key_sql}
                    FROM {table_sql}
                    GROUP BY {primary_key_sql}
                    HAVING COUNT(*) > 1
                )
            """)

            duplicate_key_groups = cursor.fetchone()[0]
            print(f"重复主键组合数：{duplicate_key_groups}")
        else:
            print("\n【主键重复检查】")
            print("该表没有显式声明主键，暂不判断业务主键是否重复。")

        # 显示少量样例，帮助确认字段含义
        print("\n【前 3 条样例数据】")

        cursor.execute(f"SELECT * FROM {table_sql} LIMIT 3")

        for sample in cursor.fetchall():
            print(sample)

print("\n" + "=" * 70)
print("检查完成：以上结果仅供诊断，没有修改数据库。")
print("=" * 70)