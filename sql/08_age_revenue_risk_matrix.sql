
-- SQL 08：企业经营年限与营收的联合风险分析

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

company_groups AS (
    SELECT
        company_id,

        CASE
            WHEN company_age_years < 3 THEN '1. 不足3年'
            WHEN company_age_years < 5 THEN '2. 3-5年'
            WHEN company_age_years < 10 THEN '3. 5-10年'
            ELSE '4. 10年及以上'
        END AS age_group,

        CASE
            WHEN annual_revenue_wan < 500 THEN '1. 营收不足500万'
            WHEN annual_revenue_wan < 2000 THEN '2. 营收500-2000万'
            WHEN annual_revenue_wan < 5000 THEN '3. 营收2000-5000万'
            ELSE '4. 营收5000万及以上'
        END AS revenue_group

    FROM companies
)

SELECT
    cg.age_group,
    cg.revenue_group,

    COUNT(*) AS total_loans,

    SUM(lr.ever_default_90d) AS defaulted_loans,

    ROUND(
        1.0 * SUM(lr.ever_default_90d) / COUNT(*),
        4
    ) AS loan_default_rate

FROM company_groups cg

JOIN loans l
    ON cg.company_id = l.company_id

JOIN loan_risk lr
    ON l.loan_id = lr.loan_id

GROUP BY
    cg.age_group,
    cg.revenue_group

ORDER BY
    cg.age_group,
    cg.revenue_group;