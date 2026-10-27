
-- SQL 09：候选授信策略初步回测
-- 规则：经营不足3年，或年营收在2000-5000万的企业进入人工复核

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
)

SELECT
    strategy_group,

    COUNT(*) AS total_loans,

    SUM(ever_default_90d) AS defaulted_loans,

    ROUND(
        1.0 * COUNT(*) /
        (SELECT COUNT(*) FROM loan_strategy),
        4
    ) AS loan_share,

    ROUND(
        1.0 * SUM(ever_default_90d) / COUNT(*),
        4
    ) AS loan_default_rate

FROM loan_strategy

GROUP BY strategy_group

ORDER BY strategy_group;