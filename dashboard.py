"""
dashboard.py  —  Project Analytics Dashboard
=============================================
Visualizes two tasks:
  1. Northwind SQL Database queries (live from SQL Server OR demo data)
  2. Currency Exchange Rate Tracker (live from frankfurter.app OR demo data)

Run with:
    pip install streamlit pandas plotly pyodbc requests
    streamlit run dashboard.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta
import requests
import logging
from pathlib import Path

# ─────────────────────────────────────────────
#  PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title  = "Project Dashboard",
    page_icon   = "",
    layout      = "wide",
    initial_sidebar_state = "expanded",
)

# ─────────────────────────────────────────────
#  CUSTOM CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #f8f9fb; }
    .block-container { padding: 2rem 2.5rem; }
    .metric-card {
        background: white;
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        border: 1px solid #e8eaf0;
        box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    }
    .section-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #1a1a2e;
        margin-bottom: 0.5rem;
    }
    .badge-delayed {
        background: #fee2e2; color: #991b1b;
        padding: 3px 10px; border-radius: 20px;
        font-size: 12px; font-weight: 600;
    }
    .badge-sig {
        background: #fef3c7; color: #92400e;
        padding: 3px 10px; border-radius: 20px;
        font-size: 12px; font-weight: 600;
    }
    div[data-testid="stMetricValue"] { font-size: 2rem !important; }
    .stTabs [data-baseweb="tab"] { font-size: 15px; font-weight: 500; }
    .stTabs [aria-selected="true"] { color: #4f46e5; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Configuration")
    st.divider()

    st.markdown("### 🗄️ SQL Server (Northwind)")
    use_live_sql = st.toggle("Connect to live SQL Server", value=False)
    if use_live_sql:
        sql_server   = st.text_input("Server",   value=r".\SQLEXPRESS")
        sql_db       = st.text_input("Database", value="Northwind")
        sql_driver   = st.text_input("Driver",   value="ODBC Driver 17 for SQL Server")
    else:
        st.info("Using demo Northwind data. Toggle above to connect live.", icon="ℹ️")

    st.divider()

    st.markdown("### 💱 Currency Tracker")
    use_live_fx = st.toggle("Fetch live exchange rates", value=False)
    sig_threshold = st.slider("Significant change threshold (%)", 0.1, 2.0, 0.5, 0.1)

    st.divider()
    st.markdown("### 📅 Date Filter (SQL)")
    min_date = st.date_input("From", value=date(1996, 1, 1))
    max_date = st.date_input("To",   value=date(1998, 12, 31))

    st.divider()
    st.caption("Dashboard by Suraj · Built with Streamlit + Plotly")


# ─────────────────────────────────────────────
#  DEMO DATA  —  Northwind
# ─────────────────────────────────────────────
DEMO_CATEGORY = pd.DataFrame({
    "CategoryName" : ["Beverages","Dairy Products","Confections","Meat/Poultry",
                       "Seafood","Produce","Condiments","Grains/Cereals"],
    "TotalRevenue" : [267868,234507,167357,163022,131261,99984,106047,95744],
    "ProductsSold" : [12,10,13,6,12,5,12,7],
    "TotalLineItems":[404,366,334,173,330,140,218,196],
})

DEMO_CUSTOMERS = pd.DataFrame({
    "CustomerID"       : ["QUICK","ERNSH","SAVEA","RATTC","HUNGO","FOLKO","MEREP","SIMOB","SUPRD","QUEEN"],
    "CompanyName"      : ["QUICK-Stop","Ernst Handel","Save-a-lot Markets","Rattlesnake Canyon",
                           "Hungry Owl","Folk och fä HB","Mère Paillarde","Simons bistro",
                           "Suprêmes délices","Queen Cozinha"],
    "Country"          : ["Germany","Austria","USA","USA","Ireland","Sweden","Canada","Denmark","Belgium","Brazil"],
    "LifetimeOrderValue": [110277,104874,104361,51097,49979,45682,43008,37283,36310,34006],
    "TotalOrders"      : [28,30,31,18,19,19,19,18,13,13],
    "MostRecentOrderDate": pd.to_datetime(["1998-05-06","1998-05-09","1998-05-01","1998-03-25",
                                            "1998-04-30","1998-04-29","1998-04-09","1998-05-01",
                                            "1998-04-22","1998-04-09"]),
})

DEMO_DELAYED = pd.DataFrame({
    "OrderID"     : [10264,10280,10429,10526,10558,10578,10634,10658,10672,10703],
    "CompanyName" : ["Folk och fä HB","Berglunds snabbköp","Hungry Owl","Wartian Herkku",
                      "Around the Horn","B's Beverages","Blondel père et fils","Quick-Stop",
                      "Berglunds snabbköp","Around the Horn"],
    "OrderDate"   : pd.to_datetime(["1996-07-24","1996-08-14","1997-01-29","1997-05-05",
                                     "1997-06-04","1997-06-26","1997-08-01","1997-09-09",
                                     "1997-09-17","1997-10-13"]),
    "ShippedDate" : pd.to_datetime(["1996-08-23","1996-09-12","1997-02-26","1997-05-15",
                                     "1997-06-14","1997-07-25","1997-08-15","1997-09-19",
                                     "1997-10-17","1997-10-23"]),
    "DaysToShip"  : [30,29,28,10,10,29,14,10,30,10],
    "PastRequiredDate": ["YES","YES","NO","NO","NO","YES","NO","NO","YES","NO"],
    "ShipmentStatus"  : ["DELAYED"]*10,
})

# ─────────────────────────────────────────────
#  LIVE SQL FETCH
# ─────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def fetch_sql(server, db, driver, date_from, date_to):
    try:
        import pyodbc
        conn_str = (
            f"DRIVER={{{driver}}};"
            f"SERVER={server};"
            f"DATABASE={db};"
            "Trusted_Connection=yes;"
            "TrustServerCertificate=yes;"
        )
        conn = pyodbc.connect(conn_str, timeout=8)

        q_cat = f"""
            SELECT c.CategoryName,
                   SUM(od.UnitPrice*od.Quantity*(1-od.Discount)) AS TotalRevenue,
                   COUNT(DISTINCT od.ProductID) AS ProductsSold,
                   COUNT(*) AS TotalLineItems
            FROM Categories c
            JOIN Products p  ON p.CategoryID=c.CategoryID
            JOIN [Order Details] od ON od.ProductID=p.ProductID
            JOIN Orders o ON o.OrderID=od.OrderID
            WHERE o.OrderDate BETWEEN '{date_from}' AND '{date_to}'
            GROUP BY c.CategoryName ORDER BY TotalRevenue DESC
        """
        q_cust = f"""
            SELECT TOP 10 cu.CustomerID, cu.CompanyName, cu.Country,
                   SUM(od.UnitPrice*od.Quantity*(1-od.Discount)) AS LifetimeOrderValue,
                   COUNT(DISTINCT o.OrderID) AS TotalOrders,
                   MAX(o.OrderDate) AS MostRecentOrderDate
            FROM Customers cu
            JOIN Orders o ON o.CustomerID=cu.CustomerID
            JOIN [Order Details] od ON od.OrderID=o.OrderID
            WHERE o.OrderDate BETWEEN '{date_from}' AND '{date_to}'
            GROUP BY cu.CustomerID,cu.CompanyName,cu.Country
            ORDER BY LifetimeOrderValue DESC
        """
        q_delay = f"""
            SELECT o.OrderID, cu.CompanyName, o.OrderDate, o.ShippedDate,
                   DATEDIFF(DAY,o.OrderDate,o.ShippedDate) AS DaysToShip,
                   CASE WHEN o.ShippedDate>o.RequiredDate THEN 'YES' ELSE 'NO' END AS PastRequiredDate,
                   'DELAYED' AS ShipmentStatus
            FROM Orders o JOIN Customers cu ON cu.CustomerID=o.CustomerID
            WHERE o.ShippedDate IS NOT NULL
              AND DATEDIFF(DAY,o.OrderDate,o.ShippedDate)>7
              AND o.OrderDate BETWEEN '{date_from}' AND '{date_to}'
            ORDER BY DaysToShip DESC
        """
        df_cat   = pd.read_sql(q_cat,   conn)
        df_cust  = pd.read_sql(q_cust,  conn)
        df_delay = pd.read_sql(q_delay, conn)
        conn.close()
        return df_cat, df_cust, df_delay, None
    except Exception as e:
        return None, None, None, str(e)


# ─────────────────────────────────────────────
#  DEMO DATA  —  Currency
# ─────────────────────────────────────────────
CURRENCIES = ["USD","EUR","GBP","INR","AED","BRL","MXN"]
DEMO_FX = pd.DataFrame({
    "currency"       : CURRENCIES,
    "today_rate"     : [1.0, 0.9213, 0.7912, 83.412, 3.6725, 4.971, 16.823],
    "yesterday_rate" : [1.0, 0.9241, 0.7889, 83.378, 3.6725, 4.989, 16.791],
})
DEMO_FX["pct_change"] = ((DEMO_FX["today_rate"] - DEMO_FX["yesterday_rate"])
                          / DEMO_FX["yesterday_rate"] * 100).round(4)
DEMO_FX["significant"] = DEMO_FX["pct_change"].abs().apply(
    lambda x: "✅ SIGNIFICANT" if x > 0.5 else ""
)

# ─────────────────────────────────────────────
#  LIVE FX FETCH
# ─────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_fx(threshold):
    try:
        symbols = ",".join(c for c in CURRENCIES if c != "USD")
        today_str = date.today().isoformat()
        yest_str  = (date.today() - timedelta(days=1)).isoformat()

        r_t = requests.get(f"https://api.frankfurter.app/{today_str}",
                           params={"base":"USD","symbols":symbols}, timeout=10)
        r_y = requests.get(f"https://api.frankfurter.app/{yest_str}",
                           params={"base":"USD","symbols":symbols}, timeout=10)
        r_t.raise_for_status(); r_y.raise_for_status()

        rates_t = r_t.json()["rates"]; rates_t["USD"] = 1.0
        rates_y = r_y.json()["rates"]; rates_y["USD"] = 1.0

        rows = []
        for c in CURRENCIES:
            rt = rates_t.get(c); ry = rates_y.get(c)
            chg = ((rt-ry)/ry*100) if rt and ry and ry != 0 else None
            rows.append({
                "currency"      : c,
                "today_rate"    : round(rt,6) if rt else None,
                "yesterday_rate": round(ry,6) if ry else None,
                "pct_change"    : round(chg,4) if chg is not None else None,
                "significant"   : "✅ SIGNIFICANT" if chg and abs(chg)>threshold else "",
            })
        return pd.DataFrame(rows), None
    except Exception as e:
        return None, str(e)


# ─────────────────────────────────────────────
#  HEADER
# ─────────────────────────────────────────────
st.markdown("# 📊 Project Analytics Dashboard")
st.markdown("Interactive visualization for **Northwind SQL queries** and **Currency Exchange Tracker**")
st.divider()

tab1, tab2 = st.tabs(["🗄️  SQL — Northwind Database", "💱  Currency Exchange Tracker"])


# ══════════════════════════════════════════════
#  TAB 1  —  NORTHWIND SQL
# ══════════════════════════════════════════════
with tab1:
    # Load data
    if use_live_sql:
        with st.spinner("Connecting to SQL Server..."):
            df_cat, df_cust, df_delay, sql_err = fetch_sql(
                sql_server, sql_db, sql_driver, min_date, max_date
            )
        if sql_err:
            st.error(f"SQL connection failed: {sql_err}")
            st.info("Falling back to demo data.")
            df_cat, df_cust, df_delay = DEMO_CATEGORY, DEMO_CUSTOMERS, DEMO_DELAYED
        else:
            st.success(f"Connected to {sql_server} → {sql_db}", icon="✅")
    else:
        df_cat, df_cust, df_delay = DEMO_CATEGORY, DEMO_CUSTOMERS, DEMO_DELAYED

    # ── KPI row ──
    k1, k2, k3, k4 = st.columns(4)
    total_rev = df_cat["TotalRevenue"].sum()
    k1.metric("💰 Total Revenue",        f"${total_rev:,.0f}")
    k2.metric("📦 Product Categories",   len(df_cat))
    k3.metric("🏆 Top Customer Value",   f"${df_cust['LifetimeOrderValue'].max():,.0f}")
    k4.metric("⚠️ Delayed Orders",       len(df_delay))

    st.divider()

    # ── Query 1: Category Revenue ──
    st.markdown("### Query 1 — Total revenue by product category")
    c1, c2 = st.columns([3, 2])

    with c1:
        fig_bar = px.bar(
            df_cat.sort_values("TotalRevenue"),
            x="TotalRevenue", y="CategoryName",
            orientation="h",
            color="TotalRevenue",
            color_continuous_scale="Blues",
            labels={"TotalRevenue":"Revenue (USD)","CategoryName":"Category"},
            text=df_cat.sort_values("TotalRevenue")["TotalRevenue"].apply(lambda x: f"${x:,.0f}"),
        )
        fig_bar.update_traces(textposition="outside")
        fig_bar.update_layout(
            showlegend=False, coloraxis_showscale=False,
            margin=dict(l=0,r=40,t=10,b=0), height=340,
            plot_bgcolor="white", paper_bgcolor="white",
            xaxis=dict(showgrid=True, gridcolor="#f0f0f0"),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with c2:
        fig_pie = px.pie(
            df_cat, values="TotalRevenue", names="CategoryName",
            hole=0.45, color_discrete_sequence=px.colors.sequential.Blues_r,
        )
        fig_pie.update_layout(margin=dict(l=0,r=0,t=10,b=0), height=340,
                               paper_bgcolor="white", showlegend=True,
                               legend=dict(font=dict(size=11)))
        fig_pie.update_traces(textposition="inside", textinfo="percent")
        st.plotly_chart(fig_pie, use_container_width=True)

    with st.expander("📋 View raw category data"):
        st.dataframe(
            df_cat.style.format({"TotalRevenue":"${:,.2f}"}),
            use_container_width=True, hide_index=True
        )

    st.divider()

    # ── Query 2: Top Customers ──
    st.markdown("### Query 2 — Top 10 customers by lifetime order value")
    c3, c4 = st.columns([2, 3])

    with c3:
        st.dataframe(
            df_cust[["CompanyName","Country","LifetimeOrderValue","TotalOrders","MostRecentOrderDate"]]
            .rename(columns={
                "CompanyName":"Company","LifetimeOrderValue":"Lifetime Value",
                "TotalOrders":"Orders","MostRecentOrderDate":"Last Order"
            })
            .style.format({"Lifetime Value":"${:,.0f}"}),
            use_container_width=True, hide_index=True, height=380
        )

    with c4:
        fig_cust = px.bar(
            df_cust.sort_values("LifetimeOrderValue"),
            x="LifetimeOrderValue", y="CompanyName",
            orientation="h",
            color="Country",
            labels={"LifetimeOrderValue":"Lifetime Value (USD)","CompanyName":""},
            text=df_cust.sort_values("LifetimeOrderValue")["LifetimeOrderValue"]
                       .apply(lambda x: f"${x:,.0f}"),
        )
        fig_cust.update_traces(textposition="outside")
        fig_cust.update_layout(
            margin=dict(l=0,r=60,t=10,b=0), height=380,
            plot_bgcolor="white", paper_bgcolor="white",
            xaxis=dict(showgrid=True, gridcolor="#f0f0f0"),
            legend=dict(font=dict(size=11)),
        )
        st.plotly_chart(fig_cust, use_container_width=True)

    st.divider()

    # ── Query 3: Delayed Orders ──
    st.markdown("### Query 3 — Delayed orders (shipped > 7 days after order date)")

    c5, c6 = st.columns([3, 2])
    with c5:
        fig_delay = px.histogram(
            df_delay, x="DaysToShip", nbins=15,
            labels={"DaysToShip":"Days to Ship"},
            color_discrete_sequence=["#ef4444"],
        )
        fig_delay.add_vline(x=7, line_dash="dash", line_color="#6b7280",
                             annotation_text="7-day threshold")
        fig_delay.update_layout(
            margin=dict(l=0,r=0,t=10,b=0), height=280,
            plot_bgcolor="white", paper_bgcolor="white",
            yaxis_title="Number of orders",
        )
        st.plotly_chart(fig_delay, use_container_width=True)

    with c6:
        col_a, col_b = st.columns(2)
        col_a.metric("Avg delay",  f"{df_delay['DaysToShip'].mean():.1f} days")
        col_b.metric("Max delay",  f"{df_delay['DaysToShip'].max()} days")
        past_req = (df_delay["PastRequiredDate"] == "YES").sum()
        col_a.metric("Also past required date", past_req)
        col_b.metric("On-time %",
                     f"{100 - round(len(df_delay)/830*100,1)}%",
                     help="Estimated from ~830 total Northwind orders")

    with st.expander("📋 View all delayed orders"):
        display_delay = df_delay.copy()
        display_delay["ShipmentStatus"] = "🔴 DELAYED"
        st.dataframe(display_delay, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════
#  TAB 2  —  CURRENCY TRACKER
# ══════════════════════════════════════════════
with tab2:
    if use_live_fx:
        with st.spinner("Fetching rates from frankfurter.app..."):
            df_fx, fx_err = fetch_fx(sig_threshold)
        if fx_err:
            st.error(f"API error: {fx_err}")
            st.info("Falling back to demo data.")
            df_fx = DEMO_FX.copy()
        else:
            st.success(f"Live rates fetched from frankfurter.app  ·  {date.today()}", icon="✅")
    else:
        df_fx = DEMO_FX.copy()
        st.info("Using demo FX data. Toggle 'Fetch live exchange rates' in sidebar for real data.", icon="ℹ️")

    # ── KPI ──
    sig_count  = (df_fx["significant"] != "").sum()
    max_change = df_fx["pct_change"].abs().max()
    top_mover  = df_fx.loc[df_fx["pct_change"].abs().idxmax(), "currency"]

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Currencies tracked",  len(df_fx))
    k2.metric("Significant movers",  sig_count)
    k3.metric("Biggest move",        top_mover)
    k4.metric("Max % change",        f"{max_change:.4f}%")

    st.divider()

    # ── Rate table ──
    st.markdown("### Exchange rates vs USD — today vs yesterday")

    col_a, col_b = st.columns([2, 3])
    with col_a:
        display_fx = df_fx.copy()
        display_fx["pct_change_display"] = display_fx["pct_change"].apply(
            lambda x: f"+{x:.4f}%" if x > 0 else f"{x:.4f}%"
        )
        st.dataframe(
            display_fx[["currency","today_rate","yesterday_rate","pct_change_display","significant"]]
            .rename(columns={
                "currency":"Currency","today_rate":"Today","yesterday_rate":"Yesterday",
                "pct_change_display":"% Change","significant":"Flag",
            }),
            use_container_width=True, hide_index=True, height=300,
        )

    with col_b:
        colors = ["#ef4444" if x < 0 else "#22c55e" for x in df_fx["pct_change"]]
        fig_fx = go.Figure(go.Bar(
            x=df_fx["currency"],
            y=df_fx["pct_change"],
            marker_color=colors,
            text=[f"{v:+.4f}%" for v in df_fx["pct_change"]],
            textposition="outside",
        ))
        fig_fx.add_hline(y=sig_threshold,  line_dash="dot", line_color="#f59e0b",
                          annotation_text=f"+{sig_threshold}% threshold")
        fig_fx.add_hline(y=-sig_threshold, line_dash="dot", line_color="#f59e0b")
        fig_fx.add_hline(y=0, line_color="#d1d5db", line_width=1)
        fig_fx.update_layout(
            margin=dict(l=0,r=0,t=20,b=0), height=300,
            plot_bgcolor="white", paper_bgcolor="white",
            yaxis_title="% Change vs USD",
            xaxis_title="",
            showlegend=False,
        )
        st.plotly_chart(fig_fx, use_container_width=True)

    st.divider()

    # ── Gauge for each currency ──
    st.markdown("### % change gauge per currency")
    gauge_cols = st.columns(len(CURRENCIES))
    for i, (_, row) in enumerate(df_fx.iterrows()):
        chg = row["pct_change"]
        color = "#ef4444" if chg < -sig_threshold else "#22c55e" if chg > sig_threshold else "#6b7280"
        fig_g = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=row["today_rate"],
            delta={"reference": row["yesterday_rate"], "valueformat": ".4f"},
            title={"text": row["currency"], "font": {"size": 14}},
            gauge={
                "axis":  {"range": [row["today_rate"]*0.99, row["today_rate"]*1.01]},
                "bar":   {"color": color},
                "bgcolor": "white",
                "bordercolor": "#e5e7eb",
            },
            number={"font": {"size": 16}},
        ))
        fig_g.update_layout(
            height=160, margin=dict(l=10,r=10,t=30,b=10),
            paper_bgcolor="white",
        )
        gauge_cols[i].plotly_chart(fig_g, use_container_width=True)

    st.divider()

    # ── Log viewer ──
    st.markdown("###  Log file viewer")
    log_path = Path("currency_tracker.log")
    if log_path.exists():
        log_text = log_path.read_text(encoding="utf-8")
        st.text_area("currency_tracker.log", value=log_text, height=200)
    else:
        st.text_area("currency_tracker.log (sample)",
                     height=180,
                     value="""2026-04-23 08:00:01 | INFO     | ══ Currency Tracker | base=USD ══
2026-04-23 08:00:01 | INFO     | Fetching rates for 2026-04-23
2026-04-23 08:00:02 | INFO     | Received 6 rate(s): ['INR','AED','EUR','GBP','BRL','MXN']
2026-04-23 08:00:02 | INFO     | Fetching rates for 2026-04-22
2026-04-23 08:00:03 | INFO     | Received 6 rate(s): ['INR','AED','EUR','GBP','BRL','MXN']
2026-04-23 08:00:03 | INFO     | Run complete | currencies_fetched=7 | errors=none
2026-04-23 08:00:03 | INFO     | CSV report written → exchange_rate_report.csv""")

    # ── CSV download ──
    st.divider()
    st.markdown("### ⬇️ Download report")
    csv_bytes = df_fx.to_csv(index=False).encode("utf-8")
    st.download_button(
        label     = "📥 Download exchange_rate_report.csv",
        data      = csv_bytes,
        file_name = "exchange_rate_report.csv",
        mime      = "text/csv",
    )




