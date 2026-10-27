
-- SQL 15：最终授信策略评估总表
-- 用途：汇总基准组合与规则 A、B、C 的策略表现，供 Power BI 使用
-- 风险口径：每笔贷款在观察期内是否曾出现 default_90d = 1
-- 金额单位：万元
-- 注意：全部拒绝复核组仅为压力情景，不代表实际授信建议

WITH loan_risk AS (
    SELECT
        loan_id,
        MAX(
            CASE
                WHEN default_90d = 1 THEN 1
                ELSE 0
            END
        ) AS ever_default
    FROM loan_performance
    GROUP BY loan_id
),

loan_detail AS (
    SELECT
        l.loan_id,
        l.approved_amount_wan,
        COALESCE(r.ever_default, 0) AS ever_default,
        c.company_age_years,
        c.annual_revenue_wan
    FROM loans AS l
    JOIN companies AS c
        ON l.company_id = c.company_id
    LEFT JOIN loan_risk AS r
        ON l.loan_id = r.loan_id
),

rule_flags AS (
    -- 基准组合：不额外增加复核规则
    SELECT
        loan_id,
        approved_amount_wan,
        ever_default,
        '基准组合' AS strategy,
        0 AS review_flag
    FROM loan_detail

    UNION ALL

    -- 规则 A：经营不足 3 年
    SELECT
        loan_id,
        approved_amount_wan,
        ever_default,
        '规则A：经营不足3年' AS strategy,
        CASE
            WHEN company_age_years < 3 THEN 1
            ELSE 0
        END AS review_flag
    FROM loan_detail

    UNION ALL

    -- 规则 B：年营收 2000–5000 万元
    SELECT
        loan_id,
        approved_amount_wan,
        ever_default,
        '规则B：年营收2000-5000万' AS strategy,
        CASE
            WHEN annual_revenue_wan >= 2000
             AND annual_revenue_wan < 5000
            THEN 1
            ELSE 0
        END AS review_flag
    FROM loan_detail

    UNION ALL

    -- 规则 C：经营年限或年营收满足条件
    SELECT
        loan_id,
        approved_amount_wan,
        ever_default,
        '规则C：经营年限或年营收' AS strategy,
        CASE
            WHEN company_age_years < 3
              OR (
                    annual_revenue_wan >= 2000
                AND annual_revenue_wan < 5000
              )
            THEN 1
            ELSE 0
        END AS review_flag
    FROM loan_detail
),

overall AS (
    SELECT
        COUNT(*) AS total_loans,
        SUM(ever_default) AS total_defaulted_loans,
        SUM(approved_amount_wan) AS total_approved_amount_wan
    FROM loan_detail
),

strategy_summary AS (
    SELECT
        strategy,
        COUNT(*) AS total_loans,
        SUM(review_flag) AS review_loans,

        SUM(
            CASE
                WHEN review_flag = 1 THEN ever_default
                ELSE 0
            END
        ) AS review_defaulted_loans,

        SUM(
            CASE
                WHEN review_flag = 1 THEN approved_amount_wan
                ELSE 0
            END
        ) AS review_approved_amount_wan,

        SUM(
            CASE
                WHEN review_flag = 0 THEN 1
                ELSE 0
            END
        ) AS retained_loans,

        SUM(
            CASE
                WHEN review_flag = 0 THEN ever_default
                ELSE 0
            END
        ) AS retained_defaulted_loans,

        SUM(
            CASE
                WHEN review_flag = 0 THEN approved_amount_wan
                ELSE 0
            END
        ) AS retained_approved_amount_wan

    FROM rule_flags
    GROUP BY strategy
)

SELECT
    s.strategy AS '策略名称',

    s.total_loans AS '总贷款数',

    s.review_loans AS '人工复核贷款数',

    ROUND(
        1.0 * s.review_loans
        / NULLIF(s.total_loans, 0),
        4
    ) AS '人工复核贷款占比',

    s.review_defaulted_loans AS '复核组曾逾期贷款数',

    ROUND(
        1.0 * s.review_defaulted_loans
        / NULLIF(s.review_loans, 0),
        4
    ) AS '复核组曾逾期率',

    ROUND(
        1.0 * s.review_defaulted_loans
        / NULLIF(o.total_defaulted_loans, 0),
        4
    ) AS '曾逾期贷款识别覆盖率',

    ROUND(
        s.review_approved_amount_wan,
        2
    ) AS '复核组审批金额_万元',

    ROUND(
        1.0 * s.review_approved_amount_wan
        / NULLIF(o.total_approved_amount_wan, 0),
        4
    ) AS '复核组审批金额占比',

    s.retained_loans AS '假设拒绝复核组后剩余贷款数',

    s.retained_defaulted_loans AS '假设拒绝复核组后剩余曾逾期贷款数',

    ROUND(
        1.0 * s.retained_defaulted_loans
        / NULLIF(s.retained_loans, 0),
        4
    ) AS '假设拒绝复核组后剩余组合曾逾期率',

    ROUND(
        s.retained_approved_amount_wan,
        2
    ) AS '假设拒绝复核组后剩余审批金额_万元',

    ROUND(
        1.0 * s.retained_approved_amount_wan
        / NULLIF(o.total_approved_amount_wan, 0),
        4
    ) AS '假设拒绝复核组后审批金额保留比例',

    ROUND(
        1.0
        - 1.0 * s.retained_approved_amount_wan
        / NULLIF(o.total_approved_amount_wan, 0),
        4
    ) AS '假设拒绝复核组后审批金额减少比例'

FROM strategy_summary AS s
CROSS JOIN overall AS o
ORDER BY
    CASE s.strategy
        WHEN '基准组合' THEN 1
        WHEN '规则A：经营不足3年' THEN 2
        WHEN '规则B：年营收2000-5000万' THEN 3
        ELSE 4
    END;