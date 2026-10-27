
-- SQL 10：候选授信策略效果评估
-- 人工复核规则：
-- 1. 企业经营不足3年
-- 2. 企业年营收在2000万至5000万元之间

WITH loan_risk AS (
    SELECT
        loan_id,
        MAX(
            CASE
                WHEN default_90d = 1 THEN 1
                ELSE 0
            END
        ) AS ever_default_90d
    FROM loan_performance
    GROUP BY loan_id
),

loan_strategy AS (
    SELECT
        l.loan_id,
        l.requested_amount_wan,
        l.approved_amount_wan,
        l.annual_interest_rate,
        lr.ever_default_90d,

        CASE
            WHEN c.company_age_years < 3
              OR (
                  c.annual_revenue_wan >= 2000
                  AND c.annual_revenue_wan < 5000
              )
            THEN '人工复核组'
            ELSE '常规审核组'
        END AS strategy_group

    FROM loans l

    JOIN companies c
        ON l.company_id = c.company_id

    JOIN loan_risk lr
        ON l.loan_id = lr.loan_id
),

group_metrics AS (
    SELECT
        strategy_group,

        COUNT(*) AS total_loans,

        SUM(ever_default_90d) AS defaulted_loans,

        SUM(requested_amount_wan) AS total_requested_wan,

        SUM(approved_amount_wan) AS total_approved_wan,

        SUM(
            CASE
                WHEN ever_default_90d = 1
                THEN approved_amount_wan
                ELSE 0
            END
        ) AS defaulted_approved_wan,

        AVG(annual_interest_rate) AS avg_interest_rate

    FROM loan_strategy
    GROUP BY strategy_group
),

overall_metrics AS (
    SELECT
        SUM(total_loans) AS all_loans,

        SUM(defaulted_loans) AS all_defaulted_loans,

        SUM(total_requested_wan) AS all_requested_wan,

        SUM(total_approved_wan) AS all_approved_wan,

        SUM(defaulted_approved_wan) AS all_defaulted_approved_wan

    FROM group_metrics
)

SELECT
    g.strategy_group,

    g.total_loans,

    ROUND(
        1.0 * g.total_loans / o.all_loans,
        4
    ) AS loan_share,

    g.defaulted_loans,

    ROUND(
        1.0 * g.defaulted_loans / g.total_loans,
        4
    ) AS loan_default_rate,

    ROUND(
        1.0 * g.defaulted_loans / o.all_defaulted_loans,
        4
    ) AS default_capture_rate,

    ROUND(g.total_requested_wan, 2) AS total_requested_wan,

    ROUND(g.total_approved_wan, 2) AS total_approved_wan,

    ROUND(
        1.0 * g.total_approved_wan / o.all_approved_wan,
        4
    ) AS approved_amount_share,

    ROUND(g.defaulted_approved_wan, 2)
        AS defaulted_approved_wan,

    ROUND(
        1.0 * g.defaulted_approved_wan
        / NULLIF(o.all_defaulted_approved_wan, 0),
        4
    ) AS defaulted_approved_amount_share,

    ROUND(g.avg_interest_rate, 4) AS avg_interest_rate

FROM group_metrics g
CROSS JOIN overall_metrics o

ORDER BY
    CASE
        WHEN g.strategy_group = '人工复核组' THEN 1
        ELSE 2
    END;