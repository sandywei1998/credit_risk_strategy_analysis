from pathlib import Path
import pandas as pd


# ============================================================
# 第 05 步：授信策略敏感性分析
# ============================================================

# 当前脚本所在目录
SCRIPT_DIR = Path(__file__).resolve().parent

# 输入、输出路径
INPUT_FILE = SCRIPT_DIR / "output" / "backtest_dataset.csv"
OUTPUT_FILE = SCRIPT_DIR / "output" / "strategy_sensitivity_analysis.csv"

# 敏感性分析参数
AGE_THRESHOLDS = [2, 3, 4, 5]

REVENUE_RANGES = [
    (1500, 4000),
    (2000, 5000),
    (3000, 6000),
]

# 必须包含的字段
REQUIRED_COLUMNS = [
    "loan_id",
    "company_age_years",
    "annual_revenue_wan",
    "approved_amount_wan",
    "default_90d_ever",
]


def main():
    print("=" * 70)
    print("第 05 步：授信策略敏感性分析")
    print(f"读取文件：{INPUT_FILE}")
    print("=" * 70)

    # 1. 检查输入文件
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"找不到输入文件：{INPUT_FILE}\n"
            "请先成功运行第 03 步，生成 backtest_dataset.csv。"
        )

    df = pd.read_csv(INPUT_FILE)

    missing_columns = [
        col for col in REQUIRED_COLUMNS if col not in df.columns
    ]
    if missing_columns:
        raise ValueError(
            f"数据集缺少必要字段：{missing_columns}\n"
            f"当前字段：{df.columns.tolist()}"
        )

    # 2. 检查关键字段
    if df["loan_id"].duplicated().any():
        raise ValueError("loan_id 存在重复，要求每笔贷款只能有一行。")

    if df[REQUIRED_COLUMNS].isnull().any().any():
        null_counts = df[REQUIRED_COLUMNS].isnull().sum()
        raise ValueError(
            "必要字段存在空值，请先检查数据：\n"
            f"{null_counts[null_counts > 0]}"
        )

    if not df["default_90d_ever"].isin([0, 1]).all():
        raise ValueError("default_90d_ever 必须只能取 0 或 1。")

    # 3. 统计基准数据
    total_loans = len(df)
    total_defaults = int(df["default_90d_ever"].sum())
    total_approved_amount = df["approved_amount_wan"].sum()

    if total_defaults == 0:
        raise ValueError("曾逾期贷款数为 0，无法计算风险识别覆盖率。")

    if total_approved_amount <= 0:
        raise ValueError("审批金额总和必须大于 0。")

    print("\n【基准数据】")
    print(f"贷款总数：{total_loans}")
    print(f"曾逾期贷款数：{total_defaults}")
    print(f"整体曾逾期比例：{total_defaults / total_loans:.2%}")
    print(f"审批金额总计：{total_approved_amount:,.2f} 万元")

    # 4. 遍历所有阈值组合
    results = []

    for age_threshold in AGE_THRESHOLDS:
        for revenue_min, revenue_max in REVENUE_RANGES:

            # 规则：经营年限不足阈值，或者年营收落入指定区间
            age_flag = df["company_age_years"] < age_threshold

            revenue_flag = (
                (df["annual_revenue_wan"] >= revenue_min)
                & (df["annual_revenue_wan"] <= revenue_max)
            )

            review_flag = age_flag | revenue_flag

            review_df = df.loc[review_flag]

            review_loan_count = len(review_df)
            review_default_count = int(
                review_df["default_90d_ever"].sum()
            )

            review_approved_amount = review_df[
                "approved_amount_wan"
            ].sum()

            # 5. 计算评价指标
            default_capture_rate = (
                review_default_count / total_defaults
            )

            review_default_rate = (
                review_default_count / review_loan_count
                if review_loan_count > 0 else 0
            )

            review_loan_share = review_loan_count / total_loans

            review_approved_amount_share = (
                review_approved_amount / total_approved_amount
            )

            retained_approved_amount_ratio = (
                1 - review_approved_amount_share
            )

            strategy_name = (
                f"经营不足{age_threshold}年 或 "
                f"营收{revenue_min}-{revenue_max}万"
            )

            results.append({
                "策略名称": strategy_name,
                "经营年限阈值_年": age_threshold,
                "营收下限_万元": revenue_min,
                "营收上限_万元": revenue_max,
                "复核组贷款数": review_loan_count,
                "复核组贷款占比": review_loan_share,
                "复核组曾逾期贷款数": review_default_count,
                "曾逾期贷款识别覆盖率": default_capture_rate,
                "复核组曾逾期率": review_default_rate,
                "复核组审批金额_万元": review_approved_amount,
                "复核组审批金额占比": review_approved_amount_share,
                "假设拒绝复核组后审批金额保留比例":
                    retained_approved_amount_ratio,
            })

    # 6. 生成结果表
    result_df = pd.DataFrame(results)

    # 先按风险识别覆盖率从高到低排序
    result_df = result_df.sort_values(
        by=[
            "曾逾期贷款识别覆盖率",
            "复核组审批金额占比",
        ],
        ascending=[False, True],
    ).reset_index(drop=True)

    # 7. 导出 CSV
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    result_df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

    # 8. 在控制台展示结果
    print("\n【12 种候选策略：按曾逾期识别覆盖率排序】")
    print("-" * 110)

    display_columns = [
        "策略名称",
        "复核组贷款数",
        "曾逾期贷款识别覆盖率",
        "复核组曾逾期率",
        "复核组审批金额占比",
        "假设拒绝复核组后审批金额保留比例",
    ]

    display_df = result_df[display_columns].copy()

    percentage_columns = [
        "曾逾期贷款识别覆盖率",
        "复核组曾逾期率",
        "复核组审批金额占比",
        "假设拒绝复核组后审批金额保留比例",
    ]

    for col in percentage_columns:
        display_df[col] = display_df[col].map(
            lambda x: f"{x:.2%}"
        )

    print(display_df.to_string(index=False))

    print("\n" + "=" * 70)
    print("敏感性分析完成")
    print(f"候选策略数量：{len(result_df)}")
    print(f"结果文件：{OUTPUT_FILE}")
    print("=" * 70)

    print("\n解释提醒：")
    print("1. 本分析使用历史观察期内曾出现 default_90d 标记作为风险标签。")
    print("2. 调整阈值后的结果属于历史回测比较，不代表未来效果保证。")
    print("3. 假设拒绝复核组只是一种情景模拟，不代表真实拒贷结果。")
    print("4. 策略优劣需要同时考虑风险识别、审核工作量和审批金额影响。")


if __name__ == "__main__":
    main()