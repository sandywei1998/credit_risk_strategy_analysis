
-- 任务2.2：分析不同资产负债率分组的贷款风险

WITH loan_default AS (
    SELECT
        loan_id,
        MAX(default_90d) AS bad_flag
    FROM loan_performance
    GROUP BY loan_id
),
company_risk AS (
    SELECT
        l.loan_id,
        f.company_id,
        1.0 * f.total_liabilities_wan / f.total_assets_wan AS debt_ratio,
        ld.bad_flag
    FROM loans l
    JOIN financials f
        ON l.company_id = f.company_id
    JOIN loan_default ld
        ON l.loan_id = ld.loan_id
)
SELECT
    CASE
        WHEN debt_ratio < 0.5 THEN '低负债'
        WHEN debt_ratio < 0.7 THEN '中负债'
        ELSE '高负债'
    END AS debt_group,
    COUNT(*) AS loan_count,
    ROUND(AVG(bad_flag), 4) AS bad_rate
FROM company_risk
GROUP BY debt_group
ORDER BY debt_group;