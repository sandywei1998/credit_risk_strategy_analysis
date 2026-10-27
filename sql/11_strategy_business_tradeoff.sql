-- SQL 11：授信策略的风险与业务规模权衡分析
-- 目的：评估候选人工复核规则识别风险的能力，以及可能带来的业务规模影响
-- 注意：本项目为模拟数据分析，不代表真实策略实施效果

WITH loan_risk AS (
    -- 第一步：汇总到贷款层级
    -- 只要一笔贷款在观察期内出现过 default_90d = 1，
    -- 就将该笔贷款标记为观察期内曾出现90天以上逾期
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
    -- 第二步：整合贷款、企业和风险信息
    SELECT
        l.loan_id,
        l.company_id,
        l.approved_amount_wan,
        c.company_age_years,
        c.annual_revenue_wan,
        COALESCE(r.ever_default, 0) AS ever_default,

        CASE
            WHEN c.company_age_years < 3
              OR (
                    c.annual_revenue_wan >= 2000
                AND c.annual_revenue_wan < 5000
              )
            THEN 1
            ELSE 0
        END AS manual_review_flag

    FROM loans AS l
    JOIN companies AS c
        ON l.company_id = c.company_id
    LEFT JOIN loan_risk AS r
        ON l.loan_id = r.loan_id
),

scenario_metrics AS (
    -- 第三步：计算基准情景
    SELECT
        1 AS sort_order,
        '基准情景：不增加复核规则' AS scenario,
        COUNT(*) AS retained_loans,
        SUM(ever_default) AS retained_defaulted_loans,
        SUM(approved_amount_wan) AS retained_approved_amount_wan,
        0 AS filtered_defaulted_loans,
        0 AS manual_review_loans,
        0 AS manual_review_defaulted_loans
    FROM loan_detail

    UNION ALL

    -- 第四步：候选策略
    -- 人工复核组进入复核流程，但不假设其全部被拒绝
    SELECT
        2 AS sort_order,
        '候选策略：人工复核，不直接拒绝' AS scenario,
        COUNT(*) AS retained_loans,
        SUM(ever_default) AS retained_defaulted_loans,
        SUM(approved_amount_wan) AS retained_approved_amount_wan,
        0 AS filtered_defaulted_loans,
        SUM(manual_review_flag) AS manual_review_loans,
        SUM(
            CASE
                WHEN manual_review_flag = 1
                THEN ever_default
                ELSE 0
            END
        ) AS manual_review_defaulted_loans
    FROM loan_detail

    UNION ALL

    -- 第五步：极端压力情景
    -- 假设人工复核组全部拒绝，仅保留常规审核组
    SELECT
        3 AS sort_order,
        '极端情景：人工复核组全部拒绝' AS scenario,
        SUM(
            CASE
                WHEN manual_review_flag = 0 THEN 1
                ELSE 0
            END
        ) AS retained_loans,
        SUM(
            CASE
                WHEN manual_review_flag = 0 THEN ever_default
                ELSE 0
            END
        ) AS retained_defaulted_loans,
        SUM(
            CASE
                WHEN manual_review_flag = 0
                THEN approved_amount_wan
                ELSE 0
            END
        ) AS retained_approved_amount_wan,
        SUM(
            CASE
                WHEN manual_review_flag = 1 THEN ever_default
                ELSE 0
            END
        ) AS filtered_defaulted_loans,
        SUM(manual_review_flag) AS manual_review_loans,
        SUM(
            CASE
                WHEN manual_review_flag = 1
                THEN ever_default
                ELSE 0
            END
        ) AS manual_review_defaulted_loans
    FROM loan_detail
)

-- 第六步：计算各情景的风险和业务规模指标
SELECT
    scenario AS '策略情景',

    retained_loans AS '保留贷款数',

    retained_defaulted_loans AS '保留组合中曾逾期贷款数',

    ROUND(
        1.0 * retained_defaulted_loans
        / NULLIF(retained_loans, 0),
        4
    ) AS '保留组合贷款观察逾期率',

    ROUND(
        retained_approved_amount_wan,
        2
    ) AS '保留审批金额_万元',

    ROUND(
        1.0 * retained_approved_amount_wan
        / NULLIF(
            MAX(retained_approved_amount_wan) OVER (),
            0
        ),
        4
    ) AS '审批金额保留比例',

    ROUND(
        1.0
        - 1.0 * retained_approved_amount_wan
        / NULLIF(
            MAX(retained_approved_amount_wan) OVER (),
            0
        ),
        4
    ) AS '审批金额减少比例',

    filtered_defaulted_loans AS '被筛除的曾逾期贷款数',

    ROUND(
        1.0 * filtered_defaulted_loans
        / NULLIF(
            SUM(
                CASE
                    WHEN sort_order = 1
                    THEN retained_defaulted_loans
                    ELSE 0
                END
            ) OVER (),
            0
        ),
        4
    ) AS '曾逾期贷款筛除比例',

    manual_review_loans AS '人工复核组贷款数',

    manual_review_defaulted_loans AS '人工复核组曾逾期贷款数'

FROM scenario_metrics
ORDER BY sort_order;