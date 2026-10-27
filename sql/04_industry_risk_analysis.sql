
-- =====================================================
-- 04_industry_risk_analysis.sql
-- 任务：分析不同行业的贷款风险
-- 口径：每笔贷款在12个月观察期内是否曾出现90+天逾期
-- =====================================================

WITH loan_default AS (
    -- 第一步：将月度表现汇总到贷款层级
    SELECT
        loan_id,
        MAX(default_90d) AS bad_flag
    FROM loan_performance
    GROUP BY loan_id
)

-- 第二步：关联企业行业、贷款和风险结果
SELECT
    c.industry,
    COUNT(*) AS loan_count,
    SUM(ld.bad_flag) AS bad_loans,
    ROUND(AVG(ld.bad_flag), 4) AS bad_rate
FROM companies c
JOIN loans l
    ON c.company_id = l.company_id
JOIN loan_default ld
    ON l.loan_id = ld.loan_id
GROUP BY c.industry
ORDER BY bad_rate DESC;