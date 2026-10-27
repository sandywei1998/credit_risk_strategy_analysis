"""
Credit Risk & Lending Strategy Project
Stage 1: Generate fully synthetic SME lending data.

All records are fictional and generated for learning/demo purposes.
No real customer or bank data is used.
Run:
    pip install pandas numpy
    python generate_data.py
Output:
    data/companies.csv
    data/financials.csv
    data/loans.csv
    data/loan_performance.csv
"""

from pathlib import Path
import numpy as np
import pandas as pd

# ---------------------------
# 1. Reproducibility & config
# ---------------------------
SEED = 20261011
N_COMPANIES = 5_000
N_LOANS = 6_500
OBSERVATION_MONTHS = 12

rng = np.random.default_rng(SEED)
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def money_round(values, digits=2):
    return np.round(values, digits)


# ---------------------------
# 2. Company master data
# ---------------------------
company_ids = np.array([f"C{i:05d}" for i in range(1, N_COMPANIES + 1)])

industries = np.array([
    "制造业", "批发零售", "建筑业", "交通运输", "信息服务",
    "住宿餐饮", "农林牧渔", "商务服务"
])
industry_probs = [0.22, 0.20, 0.13, 0.10, 0.10, 0.08, 0.07, 0.10]
industry = rng.choice(industries, size=N_COMPANIES, p=industry_probs)

regions = np.array(["A区域", "B区域", "C区域", "D区域"])
region = rng.choice(regions, size=N_COMPANIES, p=[0.32, 0.28, 0.23, 0.17])

company_age = np.clip(rng.gamma(shape=2.8, scale=3.0, size=N_COMPANIES), 0.5, 35).round(1)
ownership_type = rng.choice(
    ["民营", "个体工商户", "国有/集体", "外商投资"],
    size=N_COMPANIES,
    p=[0.72, 0.16, 0.07, 0.05]
)

# Revenue is positively skewed; unit: RMB 10,000 yuan (万元)
annual_revenue = np.clip(rng.lognormal(mean=7.0, sigma=0.85, size=N_COMPANIES), 80, 30_000)
annual_revenue = money_round(annual_revenue)

companies = pd.DataFrame({
    "company_id": company_ids,
    "industry": industry,
    "region": region,
    "company_age_years": company_age,
    "ownership_type": ownership_type,
    "annual_revenue_wan": annual_revenue,
})

# ---------------------------
# 3. Financial statement data
# ---------------------------
# Unit: 万元. Create internally consistent, but intentionally varied, ratios.
total_assets = np.clip(
    annual_revenue * rng.uniform(0.35, 1.5, size=N_COMPANIES),
    50, 50_000
)
leverage_ratio = np.clip(rng.beta(2.3, 2.0, size=N_COMPANIES), 0.08, 0.96)
total_liabilities = total_assets * leverage_ratio
equity = total_assets - total_liabilities

current_asset_ratio = rng.uniform(0.18, 0.75, size=N_COMPANIES)
current_assets = total_assets * current_asset_ratio
current_liabilities = total_liabilities * rng.uniform(0.25, 0.90, size=N_COMPANIES)

# Profit margin can be negative for a subset of companies.
profit_margin = np.clip(rng.normal(0.055, 0.075, size=N_COMPANIES), -0.25, 0.30)
net_profit = annual_revenue * profit_margin

# Operating cash flow relates to profit but includes noise.
operating_cash_flow = net_profit + annual_revenue * rng.normal(0.015, 0.065, size=N_COMPANIES)

# Report date is before loan applications to avoid future-information leakage.
financials = pd.DataFrame({
    "company_id": company_ids,
    "report_date": "2022-12-31",
    "total_assets_wan": money_round(total_assets),
    "total_liabilities_wan": money_round(total_liabilities),
    "equity_wan": money_round(equity),
    "current_assets_wan": money_round(current_assets),
    "current_liabilities_wan": money_round(current_liabilities),
    "net_profit_wan": money_round(net_profit),
    "operating_cash_flow_wan": money_round(operating_cash_flow),
})

# ---------------------------
# 4. Loan applications
# ---------------------------
# Applications span 2023-01 to 2024-12; each has a complete 12-month
# synthetic performance window in the generated dataset.
application_start = pd.Timestamp("2023-01-01")
application_end = pd.Timestamp("2024-12-31")
day_offsets = (application_end - application_start).days
application_dates = application_start + pd.to_timedelta(
    rng.integers(0, day_offsets + 1, size=N_LOANS), unit="D"
)

# Sample companies with replacement, so some companies have multiple loans.
loan_company_idx = rng.integers(0, N_COMPANIES, size=N_LOANS)
loan_company_ids = company_ids[loan_company_idx]

requested_amount = np.clip(
    annual_revenue[loan_company_idx] * rng.uniform(0.05, 0.55, size=N_LOANS),
    10, 5_000
)

# Simulated baseline approval amount; not a real bank policy.
approval_fraction = rng.uniform(0.45, 1.0, size=N_LOANS)
approved_amount = requested_amount * approval_fraction
approved_amount = money_round(approved_amount)

annual_interest_rate = np.clip(rng.normal(0.065, 0.012, size=N_LOANS), 0.035, 0.12)
loan_term_months = rng.choice([6, 12, 18, 24, 36], size=N_LOANS, p=[0.08, 0.36, 0.12, 0.30, 0.14])

loans = pd.DataFrame({
    "loan_id": [f"L{i:06d}" for i in range(1, N_LOANS + 1)],
    "company_id": loan_company_ids,
    "application_date": pd.to_datetime(application_dates).strftime("%Y-%m-%d"),
    "requested_amount_wan": money_round(requested_amount),
    "approved_amount_wan": approved_amount,
    "annual_interest_rate": np.round(annual_interest_rate, 4),
    "loan_term_months": loan_term_months,
})

# ---------------------------
# 5. Generate synthetic 12-month loan performance
# ---------------------------
# Join application-time features to each loan.
loan_fin = pd.DataFrame({
    "loan_id": loans["loan_id"],
    "company_id": loan_company_ids,
    "company_age_years": company_age[loan_company_idx],
    "annual_revenue_wan": annual_revenue[loan_company_idx],
    "leverage_ratio": leverage_ratio[loan_company_idx],
    "net_profit_wan": net_profit[loan_company_idx],
    "operating_cash_flow_wan": operating_cash_flow[loan_company_idx],
    "current_assets_wan": current_assets[loan_company_idx],
    "current_liabilities_wan": current_liabilities[loan_company_idx],
})
loan_fin["current_ratio"] = (
    loan_fin["current_assets_wan"] /
    loan_fin["current_liabilities_wan"].replace(0, np.nan)
).fillna(0)

# Synthetic risk probability: explicit educational assumptions only.
# Higher leverage, negative operating cash flow, weak liquidity/profit,
# and younger company age increase the simulated probability.
logit = (
    -3.25
    + 2.6 * (loan_fin["leverage_ratio"].to_numpy() - 0.50)
    + 0.85 * (loan_fin["operating_cash_flow_wan"].to_numpy() < 0)
    + 0.60 * (loan_fin["current_ratio"].to_numpy() < 1.0)
    + 0.50 * (loan_fin["net_profit_wan"].to_numpy() < 0)
    + 0.35 * (loan_fin["company_age_years"].to_numpy() < 3)
)
pd_12m = 1 / (1 + np.exp(-logit))
pd_12m = np.clip(pd_12m, 0.01, 0.65)

bad_12m = rng.binomial(1, pd_12m, size=N_LOANS)

# For bad loans, generate a first 90+ DPD event month; otherwise no 90+ event.
event_month = np.full(N_LOANS, fill_value=OBSERVATION_MONTHS + 1, dtype=int)
bad_indices = np.where(bad_12m == 1)[0]
event_month[bad_indices] = rng.integers(3, OBSERVATION_MONTHS + 1, size=len(bad_indices))

performance_rows = []
for i in range(N_LOANS):
    loan_id = loans.loc[i, "loan_id"]
    approved = float(approved_amount[i])
    for month in range(1, OBSERVATION_MONTHS + 1):
        if month < event_month[i]:
            # Most months current; occasional small delinquency below 90 DPD.
            dpd = int(rng.choice([0, 0, 0, 1, 7, 15], p=[0.66, 0.08, 0.06, 0.08, 0.06, 0.06]))
        else:
            dpd = min(180, 90 + 30 * (month - event_month[i]) + int(rng.integers(0, 10)))

        overdue_balance = 0.0 if dpd == 0 else approved * rng.uniform(0.05, 0.35)
        performance_rows.append({
            "loan_id": loan_id,
            "observation_month": month,
            "days_past_due": dpd,
            "overdue_balance_wan": round(float(overdue_balance), 2),
            "default_90d": int(dpd >= 90),
        })

loan_performance = pd.DataFrame(performance_rows)

# ---------------------------
# 6. Export CSVs
# ---------------------------
datasets = {
    "companies.csv": companies,
    "financials.csv": financials,
    "loans.csv": loans,
    "loan_performance.csv": loan_performance,
}
for filename, df in datasets.items():
    df.to_csv(DATA_DIR / filename, index=False, encoding="utf-8-sig")
    print(f"Created {DATA_DIR / filename} | rows={len(df):,} | cols={len(df.columns)}")

print("\nSynthetic dataset generation complete.")
print(f"Companies: {len(companies):,}")
print(f"Loans: {len(loans):,}")
print(f"Performance records: {len(loan_performance):,}")
print(f"Simulated 90+ DPD loan rate: {bad_12m.mean():.2%}")
print("\nReminder: all data and risk labels are synthetic assumptions for learning only.")
