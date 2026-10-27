from pathlib import Path
import csv


# ============================================================
# 1. 文件路径
# ============================================================

project_dir = Path(__file__).resolve().parent.parent
output_dir = Path(__file__).resolve().parent / "output"

input_path = output_dir / "backtest_dataset.csv"
detail_path = output_dir / "strategy_backtest_detail.csv"
summary_path = output_dir / "strategy_evaluation.csv"

if not input_path.exists():
    raise FileNotFoundError(
        f"没有找到数据集：{input_path}\n"
        "请先成功运行 03_build_backtest_dataset.py。"
    )

print("=" * 70)
print("第 04 步：复现 A、B、C 三种授信策略")
print(f"读取文件：{input_path}")
print("=" * 70)


# ============================================================
# 2. 读取 CSV
# ============================================================

with open(input_path, "r", encoding="utf-8-sig", newline="") as file:
    reader = csv.DictReader(file)
    rows = list(reader)

if not rows:
    raise ValueError("数据集为空，请检查 CSV 文件。")

required_columns = [
    "loan_id",
    "company_id",
    "company_age_years",
    "annual_revenue_wan",
    "approved_amount_wan",
    "default_90d_ever",
]

missing_columns = [
    column for column in required_columns
    if column not in rows[0]
]

if missing_columns:
    raise ValueError(f"数据集缺少字段：{missing_columns}")


def to_float(value, field_name, loan_id):
    """把字段转换为数字；缺失或非法值直接报错。"""
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError(
            f"贷款 {loan_id} 的字段 {field_name} "
            f"不是有效数字：{value!r}"
        )


# ============================================================
# 3. 检查关键字段和贷款编号
# ============================================================

loan_ids = [row["loan_id"] for row in rows]

if len(loan_ids) != len(set(loan_ids)):
    raise ValueError("数据集中存在重复 loan_id，不能继续计算。")

for row in rows:
    loan_id = row["loan_id"]

    age = to_float(
        row["company_age_years"], "company_age_years", loan_id
    )
    revenue = to_float(
        row["annual_revenue_wan"], "annual_revenue_wan", loan_id
    )
    amount = to_float(
        row["approved_amount_wan"], "approved_amount_wan", loan_id
    )
    label = to_float(
        row["default_90d_ever"], "default_90d_ever", loan_id
    )

    if age < 0:
        raise ValueError(f"贷款 {loan_id} 的企业经营年限小于 0。")

    if amount < 0:
        raise ValueError(f"贷款 {loan_id} 的审批金额小于 0。")

    if label not in (0, 1):
        raise ValueError(
            f"贷款 {loan_id} 的违约标签不是 0 或 1。"
        )

    row["_age"] = age
    row["_revenue"] = revenue
    row["_amount"] = amount
    row["_default"] = int(label)


# ============================================================
# 4. 定义三种策略
# ============================================================

# A：企业经营年限不足 3 年
# B：年营业收入在 2,000 万至 5,000 万之间（含边界）
# C：满足 A 或 B

for row in rows:
    row["strategy_A"] = int(row["_age"] < 3)
    row["strategy_B"] = int(2000 <= row["_revenue"] <= 5000)
    row["strategy_C"] = int(
        row["strategy_A"] == 1 or row["strategy_B"] == 1
    )


# ============================================================
# 5. 计算策略评价指标
# ============================================================

total_loans = len(rows)
total_defaults = sum(row["_default"] for row in rows)
total_approved_amount = sum(row["_amount"] for row in rows)

strategies = [
    ("基准组合", None),
    ("策略A：经营不足3年", "strategy_A"),
    ("策略B：年营收2000至5000万", "strategy_B"),
    ("策略C：A或B", "strategy_C"),
]

summary = []

for strategy_name, flag_column in strategies:

    if flag_column is None:
        selected = []
    else:
        selected = [
            row for row in rows
            if row[flag_column] == 1
        ]

    selected_count = len(selected)
    selected_defaults = sum(row["_default"] for row in selected)
    selected_amount = sum(row["_amount"] for row in selected)

    # 基准组合：所有贷款都保留，因此风险识别覆盖率为 0%
    if flag_column is None:
        selected_defaults = 0
        selected_amount = 0
        selected_count = 0

    if total_defaults > 0:
        risk_capture_rate = selected_defaults / total_defaults
    else:
        risk_capture_rate = 0

    if selected_count > 0:
        selected_default_rate = selected_defaults / selected_count
    else:
        selected_default_rate = 0

    if total_loans > 0:
        review_loan_ratio = selected_count / total_loans
    else:
        review_loan_ratio = 0

    if total_approved_amount > 0:
        review_amount_ratio = selected_amount / total_approved_amount
    else:
        review_amount_ratio = 0

    retained_loans = total_loans - selected_count
    retained_amount = total_approved_amount - selected_amount

    retained_loan_ratio = (
        retained_loans / total_loans if total_loans else 0
    )
    retained_amount_ratio = (
        retained_amount / total_approved_amount
        if total_approved_amount else 0
    )

    summary.append({
        "策略名称": strategy_name,
        "总贷款数": total_loans,
        "观察期内曾逾期贷款数": total_defaults,
        "复核组贷款数": selected_count,
        "复核组曾逾期贷款数": selected_defaults,
        "曾逾期贷款识别覆盖率": risk_capture_rate,
        "复核组曾逾期率": selected_default_rate,
        "复核组审批金额_万元": selected_amount,
        "复核组审批金额占比": review_amount_ratio,
        "复核组贷款数占比": review_loan_ratio,
        "假设拒绝复核组后贷款保留比例": retained_loan_ratio,
        "假设拒绝复核组后审批金额保留比例": retained_amount_ratio,
    })


# ============================================================
# 6. 输出策略明细
# ============================================================

detail_fields = [
    key for key in rows[0].keys()
    if not key.startswith("_")
]

with open(
    detail_path,
    "w",
    encoding="utf-8-sig",
    newline=""
) as file:
    writer = csv.DictWriter(file, fieldnames=detail_fields)
    writer.writeheader()

    for row in rows:
        writer.writerow({
            key: row[key]
            for key in detail_fields
        })


# ============================================================
# 7. 输出策略汇总
# ============================================================

summary_fields = list(summary[0].keys())

with open(
    summary_path,
    "w",
    encoding="utf-8-sig",
    newline=""
) as file:
    writer = csv.DictWriter(file, fieldnames=summary_fields)
    writer.writeheader()
    writer.writerows(summary)


# ============================================================
# 8. 在终端展示结果
# ============================================================

print("\n【数据集概况】")
print(f"总贷款数：{total_loans}")
print(f"观察期内曾逾期贷款数：{total_defaults}")
print(
    "观察期内曾逾期比例："
    f"{total_defaults / total_loans:.2%}"
    if total_loans else "观察期内曾逾期比例：无法计算"
)

print("\n【策略评价结果】")

for item in summary:
    print("\n" + "-" * 60)
    print(item["策略名称"])
    print(f"复核组贷款数：{item['复核组贷款数']}")
    print(
        "复核组曾逾期贷款数："
        f"{item['复核组曾逾期贷款数']}"
    )
    print(
        "曾逾期贷款识别覆盖率："
        f"{item['曾逾期贷款识别覆盖率']:.2%}"
    )
    print(
        "复核组曾逾期率："
        f"{item['复核组曾逾期率']:.2%}"
    )
    print(
        "复核组审批金额占比："
        f"{item['复核组审批金额占比']:.2%}"
    )
    print(
        "假设拒绝复核组后审批金额保留比例："
        f"{item['假设拒绝复核组后审批金额保留比例']:.2%}"
    )

print("\n" + "=" * 70)
print("策略复现完成")
print(f"策略明细：{detail_path}")
print(f"策略汇总：{summary_path}")
print("=" * 70)

print("\n注意：")
print("1. 本脚本采用观察期内曾出现 default_90d 标记作为历史风险标签。")
print("2. 该标签口径必须与 SQL15 核对一致后，才能判断结果是否一致。")
print("3. 假设拒绝复核组只是情景模拟，不代表真实拒贷后的结果。")
print("4. 当前收入阈值与经营年限阈值按照本项目已讨论的规则定义。")