
-- SQL 14：授信复核规则的边际贡献分析
-- 目的：拆解规则A、规则B及两者重叠部分的风险识别贡献
-- 风险口径：贷款在观察期内是否曾出现 default_90d = 1
-- 金额单位：万元

WITH loan_risk AS (
    SELECT
        loan_id,
        MAX(
            CASE
                WHEN default_90d = 1 THEN 1
                ELSE 0
            END
        ) AS ever_default
    FROM loan_performance
    GROUP BY loan_id
),

loan_detail AS (
    SELECT
        l.loan_id,
        l.approved_amount_wan,
        COALESCE(r.ever_default, 0) AS ever_default,
        c.company_age_years,
        c.annual_revenue_wan,

        CASE
            WHEN c.company_age_years < 3 THEN 1
            ELSE 0
        END AS rule_a_flag,

        CASE
            WHEN c.annual_revenue_wan >= 2000
             AND c.annual_revenue_wan < 5000
            THEN 1
            ELSE 0
        END AS rule_b_flag

    FROM loans AS l
    JOIN companies AS c
        ON l.company_id = c.company_id
    LEFT JOIN loan_risk AS r
        ON l.loan_id = r.loan_id
),

segment_detail AS (
    SELECT
        *,
        CASE
            WHEN rule_a_flag = 1 AND rule_b_flag = 0
                THEN '仅命中规则A：经营不足3年'
            WHEN rule_a_flag = 0 AND rule_b_flag = 1
                THEN '仅命中规则B：营收2000-5000万'
            WHEN rule_a_flag = 1 AND rule_b_flag = 1
                THEN '同时命中规则A和B'
            ELSE '两条规则均未命中'
        END AS segment
    FROM loan_detail
),

segment_summary AS (
    SELECT
        segment,
        COUNT(*) AS loan_count,
        SUM(ever_default) AS defaulted_loans,
        SUM(approved_amount_wan) AS approved_amount_wan
    FROM segment_detail
    GROUP BY segment
),

overall AS (
    SELECT
        COUNT(*) AS total_loans,
        SUM(ever_default) AS total_defaulted_loans,
        SUM(approved_amount_wan) AS total_approved_amount_wan
    FROM loan_detail
)

SELECT
    s.segment AS '企业分组',
    s.loan_count AS '贷款数',
    s.defaulted_loans AS '曾逾期贷款数',

    ROUND(
        1.0 * s.loan_count
        / NULLIF(o.total_loans, 0),
        4
    ) AS '贷款数量占比',

    ROUND(
        1.0 * s.defaulted_loans
        / NULLIF(s.loan_count, 0),
        4
    ) AS '分组贷款曾逾期率',

    ROUND(
        1.0 * s.defaulted_loans
        / NULLIF(o.total_defaulted_loans, 0),
        4
    ) AS '占全部曾逾期贷款比例',

    ROUND(
        s.approved_amount_wan,
        2
    ) AS '审批金额_万元',

    ROUND(
        1.0 * s.approved_amount_wan
        / NULLIF(o.total_approved_amount_wan, 0),
        4
    ) AS '审批金额占比'

FROM segment_summary AS s
CROSS JOIN overall AS o
ORDER BY
    CASE s.segment
        WHEN '仅命中规则A：经营不足3年' THEN 1
        WHEN '仅命中规则B：营收2000-5000万' THEN 2
        WHEN '同时命中规则A和B' THEN 3
        ELSE 4
    END;