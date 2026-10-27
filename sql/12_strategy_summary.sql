
-- SQL 12：授信策略效果汇总表
-- 目标：汇总基准组合、候选策略分组及全部拒绝的压力情景
-- 风险口径：每笔贷款在观察期内是否曾出现 default_90d = 1
-- 金额单位：万元

WITH loan_risk AS (
    SELECT
        loan_id,
        MAX(
            CASE WHEN default_90d = 1 THEN 1 ELSE 0 END
        ) AS ever_default
    FROM loan_performance
    GROUP BY loan_id
),

loan_detail AS (
    SELECT
        l.loan_id,
        l.approved_amount_wan,
        COALESCE(r.ever_default, 0) AS ever_default,
        CASE
            WHEN c.company_age_years < 3
              OR (
                    c.annual_revenue_wan >= 2000
                AND c.annual_revenue_wan < 5000
              )
            THEN 1
            ELSE 0
        END AS manual_review_flag
    FROM loans AS l
    JOIN companies AS c
        ON l.company_id = c.company_id
    LEFT JOIN loan_risk AS r
        ON l.loan_id = r.loan_id
),

overall AS (
    SELECT
        COUNT(*) AS total_loans,
        SUM(ever_default) AS total_defaulted_loans,
        SUM(approved_amount_wan) AS total_approved_amount_wan
    FROM loan_detail
),

strategy_groups AS (
    SELECT
        '基准组合：全部贷款' AS strategy_group,
        COUNT(*) AS loan_count,
        SUM(ever_default) AS defaulted_loans,
        SUM(approved_amount_wan) AS approved_amount_wan
    FROM loan_detail

    UNION ALL

    SELECT
        '候选策略：人工复核组',
        COUNT(*),
        SUM(ever_default),
        SUM(approved_amount_wan)
    FROM loan_detail
    WHERE manual_review_flag = 1

    UNION ALL

    SELECT
        '候选策略：常规审核组',
        COUNT(*),
        SUM(ever_default),
        SUM(approved_amount_wan)
    FROM loan_detail
    WHERE manual_review_flag = 0

    UNION ALL

    SELECT
        '压力情景：拒绝人工复核组后保留的组合',
        COUNT(*),
        SUM(ever_default),
        SUM(approved_amount_wan)
    FROM loan_detail
    WHERE manual_review_flag = 0
)

SELECT
    s.strategy_group AS '策略分组',
    s.loan_count AS '贷款数',
    s.defaulted_loans AS '曾逾期贷款数',

    ROUND(
        1.0 * s.defaulted_loans
        / NULLIF(s.loan_count, 0),
        4
    ) AS '贷款观察期曾逾期率',

    ROUND(
        1.0 * s.loan_count
        / NULLIF(o.total_loans, 0),
        4
    ) AS '贷款数量占比',

    ROUND(
        1.0 * s.defaulted_loans
        / NULLIF(o.total_defaulted_loans, 0),
        4
    ) AS '占全部曾逾期贷款比例',

    ROUND(
        s.approved_amount_wan,
        2
    ) AS '审批金额_万元',

    ROUND(
        1.0 * s.approved_amount_wan
        / NULLIF(o.total_approved_amount_wan, 0),
        4
    ) AS '审批金额占比',

    ROUND(
        1.0
        - 1.0 * s.approved_amount_wan
        / NULLIF(o.total_approved_amount_wan, 0),
        4
    ) AS '相对基准审批金额减少比例'

FROM strategy_groups AS s
CROSS JOIN overall AS o
ORDER BY
    CASE s.strategy_group
        WHEN '基准组合：全部贷款' THEN 1
        WHEN '候选策略：人工复核组' THEN 2
        WHEN '候选策略：常规审核组' THEN 3
        ELSE 4
    END;