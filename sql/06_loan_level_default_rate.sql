
-- SQL 06：按贷款统计观察期内曾出现90天以上逾期的比例

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
)

SELECT
    CASE
        WHEN c.company_age_years < 3 THEN '1. 经营不足3年'
        WHEN c.company_age_years < 5 THEN '2. 经营3-5年'
        WHEN c.company_age_years < 10 THEN '3. 经营5-10年'
        ELSE '4. 经营10年及以上'
    END AS company_age_group,

    COUNT(*) AS total_loans,

    SUM(lr.ever_default_90d) AS defaulted_loans,

    ROUND(
        1.0 * SUM(lr.ever_default_90d) / COUNT(*),
        4
    ) AS loan_default_rate

FROM companies c

JOIN loans l
    ON c.company_id = l.company_id

JOIN loan_risk lr
    ON l.loan_id = lr.loan_id

GROUP BY company_age_group

ORDER BY company_age_group;