"""Run every SQL file in order, save result tables, headline metrics and README figures.

Run from the project root:  python -m src.run_analysis
"""
import json
from pathlib import Path

import duckdb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import seaborn as sns

ROOT = Path(__file__).resolve().parents[1]
SQL = ROOT / "sql"
TABLES = ROOT / "reports" / "tables"
FIG = ROOT / "reports" / "figures"
DATA = ROOT / "data" / "online_retail_ii.parquet"


def connect():
    con = duckdb.connect()
    con.execute(f"CREATE VIEW raw AS SELECT * FROM '{DATA.as_posix()}'")
    con.execute((SQL / "01_clean.sql").read_text())
    return con


def query(con, name):
    return con.sql((SQL / name).read_text()).df()


def main():
    TABLES.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    con = connect()

    raw_rows = con.sql("SELECT count(*) FROM raw").fetchone()[0]
    clean_rows = con.sql("SELECT count(*) FROM lines").fetchone()[0]

    monthly = query(con, "02_monthly_kpis.sql")
    cohorts = query(con, "03_cohort_retention.sql")
    rfm = query(con, "04_rfm_segments.sql")
    pairs = query(con, "05_product_pairs.sql")
    countries = query(con, "06_country_returns.sql")
    for name, df in [("monthly_kpis", monthly), ("cohort_retention", cohorts), ("rfm_customers", rfm),
                     ("product_pairs", pairs), ("country_returns", countries)]:
        df.to_csv(TABLES / f"{name}.csv", index=False)

    # ---------- headline metrics ----------
    seg = (rfm.groupby("segment")
              .agg(customers=("customer_id", "count"), revenue=("monetary", "sum"),
                   avg_recency_days=("recency_days", "mean"), avg_orders=("frequency", "mean"))
              .sort_values("revenue", ascending=False))
    seg["customer_share_pct"] = (100 * seg["customers"] / seg["customers"].sum()).round(1)
    seg["revenue_share_pct"] = (100 * seg["revenue"] / seg["revenue"].sum()).round(1)
    seg = seg.round(1)
    seg.to_csv(TABLES / "segment_summary.csv")

    sorted_rev = rfm["monetary"].sort_values(ascending=False)
    top20_share = sorted_rev.head(int(len(sorted_rev) * 0.2)).sum() / sorted_rev.sum()
    repeat_rate = (rfm["frequency"] > 1).mean()
    y1 = monthly[monthly["month"] < "2010-12-01"]["revenue"].sum()
    y2 = monthly[monthly["month"] >= "2010-12-01"]["revenue"].sum()
    m1 = cohorts[cohorts["month_number"] == 1].set_index("cohort_month")["retention_pct"]
    m3 = cohorts[cohorts["month_number"] == 3].set_index("cohort_month")["retention_pct"]
    total_returns = con.sql("SELECT sum(revenue) FROM returns WHERE invoice_date < DATE '2011-12-01'").fetchone()[0]

    metrics = {
        "rows_raw": int(raw_rows),
        "rows_clean": int(clean_rows),
        "customers": int(len(rfm)),
        "revenue_year1_gbp": round(float(y1)),
        "revenue_year2_gbp": round(float(y2)),
        "revenue_growth_pct": round(100 * (y2 / y1 - 1), 1),
        "top20pct_customers_revenue_share_pct": round(100 * top20_share, 1),
        "repeat_customer_rate_pct": round(100 * repeat_rate, 1),
        "median_month1_retention_pct": round(float(m1.median()), 1),
        "median_month3_retention_pct": round(float(m3.median()), 1),
        "return_rate_pct": round(100 * total_returns / (y1 + y2), 1),
        "peak_month": str(monthly.loc[monthly["revenue"].idxmax(), "month"].date()),
    }
    (ROOT / "reports" / "metrics.json").write_text(json.dumps(metrics, indent=2))
    print(json.dumps(metrics, indent=2))
    print(seg)
    print(pairs.head(8).to_string())
    print(countries.to_string())

    # ---------- figures ----------
    sns.set_theme(style="whitegrid")
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.bar(monthly["month"], monthly["revenue"] / 1000, width=20, color="#4C72B0")
    ax.set(title="Monthly revenue (GBP thousands)", ylabel="£k")
    fig.tight_layout(); fig.savefig(FIG / "monthly_revenue.png", dpi=150); plt.close(fig)

    heat = cohorts[cohorts["month_number"].between(0, 12)].pivot(index="cohort_month", columns="month_number",
                                                                   values="retention_pct")
    heat.index = heat.index.strftime("%Y-%m")
    fig, ax = plt.subplots(figsize=(12, 8))
    # Month 0 is always 100%; cap the scale so differences between later months stay visible.
    sns.heatmap(heat, annot=True, fmt=".0f", cmap="Blues", vmax=40, linewidths=0.5,
                cbar_kws={"label": "% of cohort buying"}, ax=ax)
    ax.set(title="Cohort retention: % of new customers who buy again N months later",
           xlabel="Months since first purchase", ylabel="First purchase month")
    fig.tight_layout(); fig.savefig(FIG / "cohort_retention.png", dpi=150); plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 4.5))
    plot = seg[["customer_share_pct", "revenue_share_pct"]].rename(
        columns={"customer_share_pct": "% of customers", "revenue_share_pct": "% of revenue"})
    plot.plot.barh(ax=ax, color=["#BBBBBB", "#4C72B0"])
    ax.invert_yaxis()
    ax.xaxis.set_major_formatter(mtick.PercentFormatter())
    ax.set(title="RFM segments: share of customers vs share of revenue", ylabel="")
    fig.tight_layout(); fig.savefig(FIG / "rfm_segments.png", dpi=150); plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 4.5))
    cum = sorted_rev.cumsum().values / sorted_rev.sum() * 100
    x = [100 * (i + 1) / len(cum) for i in range(len(cum))]
    ax.plot(x, cum, color="#4C72B0")
    ax.axvline(20, ls="--", color="crimson")
    ax.axhline(100 * top20_share, ls="--", color="crimson")
    ax.set(title=f"Top 20% of customers = {100 * top20_share:.0f}% of revenue",
           xlabel="% of customers (highest spend first)", ylabel="% of revenue")
    fig.tight_layout(); fig.savefig(FIG / "pareto.png", dpi=150); plt.close(fig)


if __name__ == "__main__":
    main()
