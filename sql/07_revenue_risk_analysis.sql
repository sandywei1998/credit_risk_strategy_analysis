
-- SQL 07：企业年营收与贷款级逾期率分析

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

company_revenue AS (
    SELECT
        c.company_id,
        c.annual_revenue_wan,
        CASE
            WHEN c.annual_revenue_wan < 500 THEN '1. 年营收不足500万'
            WHEN c.annual_revenue_wan < 2000 THEN '2. 年营收500-2000万'
            WHEN c.annual_revenue_wan < 5000 THEN '3. 年营收2000-5000万'
            ELSE '4. 年营收5000万及以上'
        END AS revenue_group
    FROM companies c
)

SELECT
    cr.revenue_group,

    COUNT(*) AS total_loans,

    SUM(lr.ever_default_90d) AS defaulted_loans,

    ROUND(
        1.0 * SUM(lr.ever_default_90d) / COUNT(*),
        4
    ) AS loan_default_rate

FROM company_revenue cr

JOIN loans l
    ON cr.company_id = l.company_id

JOIN loan_risk lr
    ON l.loan_id = lr.loan_id

GROUP BY cr.revenue_group

ORDER BY cr.revenue_group;