
-- SQL 05：企业经营年限与违约风险分析

SELECT
    CASE
        WHEN c.company_age_years < 3 THEN '1. 经营不足3年'
        WHEN c.company_age_years < 5 THEN '2. 经营3-5年'
        WHEN c.company_age_years < 10 THEN '3. 经营5-10年'
        ELSE '4. 经营10年及以上'
    END AS company_age_group,

    COUNT(DISTINCT l.loan_id) AS total_loans,

    SUM(
        CASE
            WHEN lp.default_90d = 1 THEN 1
            ELSE 0
        END
    ) AS default_records,

    ROUND(
        1.0 * SUM(
            CASE
                WHEN lp.default_90d = 1 THEN 1
                ELSE 0
            END
        ) / COUNT(*),
        4
    ) AS default_rate

FROM companies c

JOIN loans l
    ON c.company_id = l.company_id

JOIN loan_performance lp
    ON l.loan_id = lp.loan_id

GROUP BY company_age_group

ORDER BY company_age_group;