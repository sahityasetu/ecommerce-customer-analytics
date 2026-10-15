"""Interactive e-commerce dashboard (Streamlit + DuckDB + Plotly).

Run:  streamlit run dashboard.py
"""
from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

from src.run_analysis import SQL, connect

st.set_page_config(page_title="E-commerce Customer Analytics", layout="wide")


@st.cache_resource
def get_con():
    return connect()


con = get_con()


@st.cache_data
def countries():
    return con.sql("SELECT country FROM sales GROUP BY 1 ORDER BY sum(revenue) DESC").df()["country"].tolist()


@st.cache_data
def filtered(start: date, end: date, picked: tuple):
    where = "invoice_date BETWEEN ? AND ?"
    params = [start, end]
    if picked:
        where += f" AND country IN ({','.join('?' * len(picked))})"
        params += list(picked)
    return con.execute(f"SELECT * FROM sales WHERE {where}", params).df()


st.title("E-commerce Customer Analytics")
st.caption("UK online gift retailer, Dec 2009 - Nov 2011 (UCI Online Retail II). All values in GBP.")

with st.sidebar:
    st.header("Filters")
    start, end = st.date_input("Date range", (date(2010, 12, 1), date(2011, 11, 30)),
                               min_value=date(2009, 12, 1), max_value=date(2011, 11, 30))
    picked = st.multiselect("Countries (empty = all)", countries())

df = filtered(start, end, tuple(picked))
if df.empty:
    st.warning("No sales for these filters.")
    st.stop()

# Previous period of the same length, for KPI deltas.
span = end - start
prev = filtered(start - span - pd.Timedelta(days=1), start - pd.Timedelta(days=1), tuple(picked))


def kpis(d):
    orders = d["Invoice"].nunique()
    rev = d["revenue"].sum()
    return rev, orders, d["customer_id"].nunique(), rev / orders if orders else 0


cur, old = kpis(df), kpis(prev)
cols = st.columns(4)
for col, label, fmt, c, o in zip(cols, ["Revenue", "Orders", "Customers", "Avg order value"],
                                 ["£{:,.0f}", "{:,.0f}", "{:,.0f}", "£{:,.2f}"], cur, old):
    delta = f"{100 * (c / o - 1):+.1f}% vs previous period" if o else None
    col.metric(label, fmt.format(c), delta)

trend, cohort, segments, products, geo = st.tabs(["Trend", "Cohorts", "RFM segments", "Products", "Countries"])

with trend:
    m = (df.assign(month=df["invoice_date"].dt.to_period("M").dt.to_timestamp())
           .groupby("month").agg(revenue=("revenue", "sum"), orders=("Invoice", "nunique")).reset_index())
    st.plotly_chart(px.bar(m, x="month", y="revenue", title="Monthly revenue"), width="stretch")
    dow = (df.assign(day=df["invoice_ts"].dt.day_name(), hour=df["invoice_ts"].dt.hour)
             .groupby(["day", "hour"])["revenue"].sum().reset_index())
    order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    st.plotly_chart(px.density_heatmap(dow, x="hour", y="day", z="revenue", category_orders={"day": order},
                                       title="When do customers buy? (revenue by weekday and hour)",
                                       color_continuous_scale="Blues"), width="stretch")

with cohort:
    c = con.sql((SQL / "03_cohort_retention.sql").read_text()).df()
    c = c[c["month_number"].between(1, 12)]
    c["cohort_month"] = c["cohort_month"].dt.strftime("%Y-%m")
    heat = c.pivot(index="cohort_month", columns="month_number", values="retention_pct")
    st.plotly_chart(px.imshow(heat, text_auto=True, aspect="auto", color_continuous_scale="Blues",
                              labels={"x": "Months since first purchase", "y": "First purchase month",
                                      "color": "% buying"},
                              title="Cohort retention (all countries, full period)"), width="stretch")

with segments:
    rfm = con.sql((SQL / "04_rfm_segments.sql").read_text()).df()
    seg = rfm.groupby("segment").agg(customers=("customer_id", "count"), revenue=("monetary", "sum"),
                                     avg_recency_days=("recency_days", "mean")).reset_index()
    left, right = st.columns(2)
    left.plotly_chart(px.treemap(seg, path=["segment"], values="revenue", title="Revenue by RFM segment"),
                      width="stretch")
    right.dataframe(seg.sort_values("revenue", ascending=False).round(0), width="stretch", hide_index=True)
    pick = st.selectbox("Export a customer list for a campaign", sorted(seg["segment"]))
    out = rfm[rfm["segment"] == pick].sort_values("monetary", ascending=False)
    st.download_button(f"Download {len(out):,} '{pick}' customers", out.to_csv(index=False),
                       f"{pick.lower().replace(' ', '_')}.csv")

with products:
    top = (df.groupby("description").agg(revenue=("revenue", "sum"), units=("quantity", "sum"))
             .nlargest(15, "revenue").reset_index())
    st.plotly_chart(px.bar(top, x="revenue", y="description", orientation="h", title="Top 15 products by revenue")
                    .update_yaxes(autorange="reversed"), width="stretch")
    st.subheader("Frequently bought together (full period)")
    st.dataframe(con.sql((SQL / "05_product_pairs.sql").read_text()).df(), width="stretch", hide_index=True)

with geo:
    g = df.groupby("country").agg(revenue=("revenue", "sum"), customers=("customer_id", "nunique")).reset_index()
    st.plotly_chart(px.choropleth(g, locations="country", locationmode="country names", color="revenue",
                                  color_continuous_scale="Blues", title="Revenue by country"),
                    width="stretch")
    st.dataframe(g.sort_values("revenue", ascending=False).round(0), width="stretch", hide_index=True)
