
-- 任务2.2：计算整体贷款风险水平
-- 口径：每笔贷款在12个月观察期内是否曾出现90天以上逾期

SELECT
    COUNT(*) AS total_loans,
    SUM(default_90d) AS bad_loans,
    AVG(default_90d) AS bad_rate
FROM (
    SELECT
        loan_id,
        MAX(default_90d) AS default_90d
    FROM loan_performance
    GROUP BY loan_id
);