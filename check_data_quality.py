"""
Stage 1 quality checks for the synthetic credit-risk project.
Run after generate_data.py has created the four CSV files.
"""

from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

required_files = [
    "companies.csv",
    "financials.csv",
    "loans.csv",
    "loan_performance.csv",
]

missing_files = [name for name in required_files if not (DATA_DIR / name).exists()]
if missing_files:
    raise FileNotFoundError(
        f"Missing files in {DATA_DIR}: {missing_files}. "
        "Please run generate_data.py first."
    )

companies = pd.read_csv(DATA_DIR / "companies.csv")
financials = pd.read_csv(DATA_DIR / "financials.csv")
loans = pd.read_csv(DATA_DIR / "loans.csv")
performance = pd.read_csv(DATA_DIR / "loan_performance.csv")

print("=" * 60)
print("1. File sizes")
for name, df in [
    ("companies", companies),
    ("financials", financials),
    ("loans", loans),
    ("loan_performance", performance),
]:
    print(f"{name:20s}: {len(df):>8,} rows | {len(df.columns):>2} columns")

print("\n" + "=" * 60)
print("2. Duplicate primary-key checks")
checks = {
    "companies.company_id unique": companies["company_id"].is_unique,
    "financials.company_id unique": financials["company_id"].is_unique,
    "loans.loan_id unique": loans["loan_id"].is_unique,
}
for label, passed in checks.items():
    print(f"{'PASS' if passed else 'FAIL'} - {label}")

print("\n" + "=" * 60)
print("3. Missing values")
for name, df in [
    ("companies", companies),
    ("financials", financials),
    ("loans", loans),
    ("loan_performance", performance),
]:
    missing_count = int(df.isna().sum().sum())
    print(f"{name:20s}: {missing_count} missing cells")

print("\n" + "=" * 60)
print("4. Relationship checks")
company_ids = set(companies["company_id"])
loan_ids = set(loans["loan_id"])

orphan_financials = int((~financials["company_id"].isin(company_ids)).sum())
orphan_loans = int((~loans["company_id"].isin(company_ids)).sum())
orphan_performance = int((~performance["loan_id"].isin(loan_ids)).sum())

print(f"Financial rows with unknown company_id: {orphan_financials}")
print(f"Loan rows with unknown company_id: {orphan_loans}")
print(f"Performance rows with unknown loan_id: {orphan_performance}")

months_per_loan = performance.groupby("loan_id")["observation_month"].nunique()
wrong_month_count = int((months_per_loan != 12).sum())
missing_loan_performance = len(set(loans["loan_id"]) - set(performance["loan_id"]))
print(f"Loans without exactly 12 distinct observation months: {wrong_month_count}")
print(f"Loans with no performance records: {missing_loan_performance}")

print("\n" + "=" * 60)
print("5. Risk-label consistency")
expected_default = (performance["days_past_due"] >= 90).astype(int)
label_mismatches = int((expected_default != performance["default_90d"]).sum())
loan_bad_label = performance.groupby("loan_id")["default_90d"].max()
print(f"Rows where default_90d disagrees with days_past_due >= 90: {label_mismatches}")
print(f"Loans with 90+ DPD during 12-month window: {int(loan_bad_label.sum()):,}")
print(f"Synthetic 90+ DPD loan rate: {loan_bad_label.mean():.2%}")

print("\n" + "=" * 60)
print("6. Basic value checks")
print(f"Companies with non-positive total assets: "
      f"{int((financials['total_assets_wan'] <= 0).sum())}")
print(f"Loans with non-positive requested amount: "
      f"{int((loans['requested_amount_wan'] <= 0).sum())}")
print(f"Loans where approved amount exceeds requested amount: "
      f"{int((loans['approved_amount_wan'] > loans['requested_amount_wan']).sum())}")
print(f"Performance rows with negative days past due: "
      f"{int((performance['days_past_due'] < 0).sum())}")

# Summary result: key structural checks
key_failures = (
    (not companies["company_id"].is_unique)
    or (not financials["company_id"].is_unique)
    or (not loans["loan_id"].is_unique)
    or orphan_financials > 0
    or orphan_loans > 0
    or orphan_performance > 0
    or wrong_month_count > 0
    or missing_loan_performance > 0
    or label_mismatches > 0
)

print("\n" + "=" * 60)
if key_failures:
    print("RESULT: Some key checks failed. Review the messages above before proceeding.")
else:
    print("RESULT: All key structural checks passed.")
print("Reminder: these are synthetic data and labels for learning only.")
