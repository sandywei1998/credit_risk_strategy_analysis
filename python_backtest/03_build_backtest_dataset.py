from pathlib import Path
import sqlite3
import csv


# ============================================================
# 1. 定位项目目录、数据库和输出文件
# ============================================================

project_dir = Path(__file__).resolve().parent.parent
db_path = project_dir / "credit_risk.db"
output_dir = Path(__file__).resolve().parent / "output"
output_path = output_dir / "backtest_dataset.csv"

if not db_path.exists():
    raise FileNotFoundError(f"没有找到数据库：{db_path}")

output_dir.mkdir(parents=True, exist_ok=True)

print("=" * 70)
print("第 03 步：构建历史回测数据集")
print(f"数据库：{db_path}")
print(f"输出文件：{output_path}")
print("=" * 70)


def quote_identifier(name):
    """安全引用 SQLite 字段名。"""
    return '"' + name.replace('"', '""') + '"'


errors = []


# ============================================================
# 2. 只读连接数据库
# ============================================================

with sqlite3.connect(
    db_path.as_uri() + "?mode=ro",
    uri=True
) as conn:

    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # --------------------------------------------------------
    # 3. 检查关键业务键唯一性
    # --------------------------------------------------------

    print("\n【1. 业务键唯一性检查】")

    # 公司表：每家公司一条记录
    # 财务表：每家公司一条财务记录
    # 贷款表：每笔贷款一条记录

    unique_checks = [
        ("companies", "company_id"),
        ("financials", "company_id"),
        ("loans", "loan_id"),
    ]

    for table, field in unique_checks:
        field_sql = quote_identifier(field)
        table_sql = quote_identifier(table)

        cursor.execute(f"""
            SELECT COUNT(*)
            FROM (
                SELECT {field_sql}
                FROM {table_sql}
                GROUP BY {field_sql}
                HAVING COUNT(*) > 1
            )
        """)

        duplicate_groups = cursor.fetchone()[0]

        print(f"{table}.{field}：重复分组数 = {duplicate_groups}")

        if duplicate_groups > 0:
            errors.append(
                f"{table}.{field} 存在重复分组，无法安全关联。"
            )

    # 贷款表现表中，loan_id 单独重复是正常的：
    # 每笔贷款会有多个观察月份。
    # 因此检查 loan_id + observation_month 组合是否重复。

    cursor.execute("""
        SELECT COUNT(*)
        FROM (
            SELECT loan_id, observation_month
            FROM loan_performance
            GROUP BY loan_id, observation_month
            HAVING COUNT(*) > 1
        )
    """)

    duplicate_month_groups = cursor.fetchone()[0]

    print(
        "loan_performance 的重复贷款-月份组合数："
        f"{duplicate_month_groups}"
    )

    if duplicate_month_groups > 0:
        errors.append(
            "loan_performance 存在重复的贷款-月份组合。"
        )

    # --------------------------------------------------------
    # 4. 检查表之间的关联关系
    # --------------------------------------------------------

    print("\n【2. 表之间的关联检查】")

    relationship_checks = [
        (
            "贷款找不到对应公司的记录数",
            """
            SELECT COUNT(*)
            FROM loans l
            LEFT JOIN companies c
                ON l.company_id = c.company_id
            WHERE c.company_id IS NULL
            """
        ),
        (
            "贷款找不到对应财务记录的数量",
            """
            SELECT COUNT(*)
            FROM loans l
            LEFT JOIN financials f
                ON l.company_id = f.company_id
            WHERE f.company_id IS NULL
            """
        ),
        (
            "财务记录找不到对应公司的数量",
            """
            SELECT COUNT(*)
            FROM financials f
            LEFT JOIN companies c
                ON f.company_id = c.company_id
            WHERE c.company_id IS NULL
            """
        ),
        (
            "表现记录找不到对应贷款的数量",
            """
            SELECT COUNT(*)
            FROM loan_performance p
            LEFT JOIN loans l
                ON p.loan_id = l.loan_id
            WHERE l.loan_id IS NULL
            """
        ),
    ]

    for description, sql in relationship_checks:
        cursor.execute(sql)
        unmatched_count = cursor.fetchone()[0]

        print(f"{description}：{unmatched_count}")

        if unmatched_count > 0:
            errors.append(
                f"{description}为 {unmatched_count}，存在关联缺失。"
            )

    # --------------------------------------------------------
    # 5. 检查每笔贷款的观察期
    # --------------------------------------------------------

    print("\n【3. 观察期完整性检查】")

    cursor.execute("""
        SELECT
            COUNT(*) AS loan_count,
            MIN(month_count) AS min_months,
            MAX(month_count) AS max_months,
            SUM(
                CASE WHEN month_count != 12 THEN 1 ELSE 0 END
            ) AS not_12_months
        FROM (
            SELECT
                loan_id,
                COUNT(DISTINCT observation_month) AS month_count
            FROM loan_performance
            GROUP BY loan_id
        )
    """)

    summary = cursor.fetchone()

    observed_loan_count = summary["loan_count"] or 0
    min_months = summary["min_months"]
    max_months = summary["max_months"]
    not_12_months = summary["not_12_months"] or 0

    cursor.execute("SELECT COUNT(*) FROM loans")
    total_loans = cursor.fetchone()[0]

    print(f"贷款总数：{total_loans}")
    print(f"有观察记录的贷款数：{observed_loan_count}")
    print(f"单笔贷款最少观察月份数：{min_months}")
    print(f"单笔贷款最多观察月份数：{max_months}")
    print(f"观察月份数量不是 12 的贷款数：{not_12_months}")

    if observed_loan_count != total_loans:
        errors.append(
            "有观察记录的贷款数与贷款总数不一致。"
        )

    if not_12_months > 0:
        errors.append(
            f"{not_12_months} 笔贷款的观察月份数量不是 12。"
        )

    # 检查月份范围
    cursor.execute("""
        SELECT COUNT(*)
        FROM loan_performance
        WHERE observation_month IS NULL
           OR observation_month < 1
           OR observation_month > 12
    """)

    invalid_month_count = cursor.fetchone()[0]

    print(f"不在第 1 至第 12 月范围内的记录数：{invalid_month_count}")

    if invalid_month_count > 0:
        errors.append("观察月份存在无效值。")

    # 检查违约标记
    cursor.execute("""
        SELECT COUNT(*)
        FROM loan_performance
        WHERE default_90d IS NULL
           OR default_90d NOT IN (0, 1)
    """)

    invalid_label_count = cursor.fetchone()[0]

    print(f"default_90d 非 0/1 或为空的记录数：{invalid_label_count}")

    if invalid_label_count > 0:
        errors.append("default_90d 存在无效标签。")

    # 检查贷款表现记录中是否有缺失的贷款编号
    cursor.execute("""
        SELECT COUNT(*)
        FROM loan_performance
        WHERE loan_id IS NULL
           OR TRIM(loan_id) = ''
    """)

    missing_loan_id_count = cursor.fetchone()[0]

    print(f"loan_performance 中贷款编号缺失的记录数：{missing_loan_id_count}")

    if missing_loan_id_count > 0:
        errors.append("loan_performance 存在缺失的 loan_id。")

    # --------------------------------------------------------
    # 6. 有问题则停止，不生成数据集
    # --------------------------------------------------------

    if errors:
        print("\n" + "=" * 70)
        print("发现以下问题，暂不生成回测数据集：")

        for error in errors:
            print(f"- {error}")

        print("\n请将运行结果发给我，我们继续排查。")
        raise SystemExit(1)

    print("\n以上关联与观察期检查全部通过。")

    # --------------------------------------------------------
    # 7. 汇总每笔贷款的月度表现
    # --------------------------------------------------------

    print("\n【4. 汇总每笔贷款的历史表现】")

    cursor.execute("""
        SELECT
            loan_id,
            COUNT(DISTINCT observation_month) AS observed_months,
            MAX(days_past_due) AS max_days_past_due,
            MAX(default_90d) AS default_90d_ever
        FROM loan_performance
        GROUP BY loan_id
    """)

    performance_rows = {
        row["loan_id"]: dict(row)
        for row in cursor.fetchall()
    }

    print(f"汇总后的贷款表现记录数：{len(performance_rows)}")

    # --------------------------------------------------------
    # 8. 关联贷款、公司和财务信息
    # --------------------------------------------------------

    print("\n【5. 构建每笔贷款一行的数据集】")

    cursor.execute("""
        SELECT
            l.loan_id,
            l.company_id,
            l.application_date,
            l.requested_amount_wan,
            l.approved_amount_wan,
            l.annual_interest_rate,
            l.loan_term_months,

            c.industry,
            c.region,
            c.company_age_years,
            c.ownership_type,
            c.annual_revenue_wan,

            f.report_date,
            f.total_assets_wan,
            f.total_liabilities_wan,
            f.equity_wan,
            f.current_assets_wan,
            f.current_liabilities_wan,
            f.net_profit_wan,
            f.operating_cash_flow_wan

        FROM loans l
        LEFT JOIN companies c
            ON l.company_id = c.company_id
        LEFT JOIN financials f
            ON l.company_id = f.company_id

        ORDER BY l.loan_id
    """)

    loan_rows = [dict(row) for row in cursor.fetchall()]

    if len(loan_rows) != total_loans:
        raise RuntimeError(
            f"合并后的贷款记录数为 {len(loan_rows)}，"
            f"原始贷款数为 {total_loans}，数量不一致。"
        )

    final_rows = []

    for row in loan_rows:
        loan_id = row["loan_id"]
        performance = performance_rows.get(loan_id)

        if performance is None:
            raise RuntimeError(
                f"贷款 {loan_id} 没有找到对应的表现汇总记录。"
            )

        row.update(performance)
        final_rows.append(row)

    # 检查最终数据集的贷款编号唯一性
    final_loan_ids = [row["loan_id"] for row in final_rows]

    if len(final_loan_ids) != len(set(final_loan_ids)):
        raise RuntimeError("最终数据集存在重复 loan_id，停止导出。")

    if len(final_rows) != total_loans:
        raise RuntimeError("最终数据集行数与原始贷款数不一致。")

    # --------------------------------------------------------
    # 9. 导出 CSV
    # --------------------------------------------------------

    if not final_rows:
        raise RuntimeError("没有可导出的数据。")

    fieldnames = list(final_rows[0].keys())

    with open(
        output_path,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(final_rows)

    # --------------------------------------------------------
    # 10. 输出结果摘要
    # --------------------------------------------------------

    default_count = sum(
        int(row["default_90d_ever"])
        for row in final_rows
    )

    print("\n" + "=" * 70)
    print("回测数据集生成成功")
    print("=" * 70)
    print(f"原始贷款数：{total_loans}")
    print(f"输出数据行数：{len(final_rows)}")
    print(f"输出字段数：{len(fieldnames)}")
    print(
        "观察期内至少一个月被标记为 90 天以上逾期的贷款数："
        f"{default_count}"
    )
    print(f"输出文件：{output_path}")

    print("\n前 3 笔贷款的关键字段：")

    for row in final_rows[:3]:
        print(
            row["loan_id"],
            row["company_id"],
            row["application_date"],
            row["report_date"],
            row["observed_months"],
            row["max_days_past_due"],
            row["default_90d_ever"]
        )

    print("\n说明：")
    print("1. 每行代表一笔贷款，而不是一条月度观察记录。")
    print("2. default_90d_ever 表示观察期内曾出现 90 天以上逾期标记。")
    print("3. 本步骤只整合数据，不代表策略效果已经验证。")
    print("4. 财务报告日期与申请日期的时间关系仍需单独核实。")