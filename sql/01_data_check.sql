
-- =====================================================
-- 01_data_check.sql
-- 项目：信贷风险分析与授信策略评估
-- 阶段：2.1 数据导入验证
-- 目的：检查四张数据表是否存在、记录数是否符合预期
-- =====================================================

-- 检查1：查看当前数据库中的所有业务表
SELECT
    name AS table_name
FROM sqlite_master
WHERE type = 'table'
  AND name NOT LIKE 'sqlite_%'
ORDER BY name;


-- 检查2：验证四张业务表的记录数
SELECT
    'companies' AS table_name,
    COUNT(*) AS row_count
FROM companies

UNION ALL

SELECT
    'financials',
    COUNT(*)
FROM financials

UNION ALL

SELECT
    'loans',
    COUNT(*)
FROM loans

UNION ALL

SELECT
    'loan_performance',
    COUNT(*)
FROM loan_performance;


-- 检查3：检查企业编号是否重复
SELECT
    COUNT(*) AS total_rows,
    COUNT(DISTINCT company_id) AS unique_company_ids
FROM companies;


-- 检查4：检查贷款编号是否重复
SELECT
    COUNT(*) AS total_rows,
    COUNT(DISTINCT loan_id) AS unique_loan_ids
FROM loans;


-- 检查5：检查四张表的关键字段是否存在空值
SELECT
    'companies.company_id' AS field_name,
    SUM(CASE WHEN company_id IS NULL THEN 1 ELSE 0 END) AS null_count
FROM companies

UNION ALL

SELECT
    'financials.company_id',
    SUM(CASE WHEN company_id IS NULL THEN 1 ELSE 0 END)
FROM financials

UNION ALL

SELECT
    'loans.loan_id',
    SUM(CASE WHEN loan_id IS NULL THEN 1 ELSE 0 END)
FROM loans

UNION ALL

SELECT
    'loan_performance.loan_id',
    SUM(CASE WHEN loan_id IS NULL THEN 1 ELSE 0 END)
FROM loan_performance;