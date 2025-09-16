import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import pandas as pd
import altair as alt
import math

def _rebase_per_year(values: pd.Series, dates: pd.Series) -> pd.Series:
    # Make a datetime-indexed series
    s = pd.Series(pd.to_numeric(values, errors="coerce").values,
                  index=pd.to_datetime(dates).tz_localize(None)).sort_index()

    # Rebase within each calendar year
    out_parts = []
    for year, seg in s.groupby(s.index.year):
        seg = seg.copy()
        # first valid value in the year
        first_valid = seg.first_valid_index()
        if first_valid is None:
            out_parts.append(seg)
            continue
        base = seg.loc[first_valid]
        if pd.notna(base) and base != 0:
            seg = seg / base * 100.0
        out_parts.append(seg)
    out = pd.concat(out_parts).sort_index()
    # Align to original order of dates
    return out.reindex(s.index)

def show_portfolio(portfolio_df, currency_symbol="€", columns_per_row=4):
    st.subheader("📊 Portfolio Overview")

    # --- Calculate weighted change ---
    valid = portfolio_df[portfolio_df["% Change (1d)"].notna()]
    total_value = valid["Value (€)"].sum()
    if total_value > 0:
        weighted_changes = (valid["Value (€)"] * valid["% Change (1d)"]) / total_value
        weighted_change = weighted_changes.sum()
    else:
        weighted_change = 0.0

    # --- Show grouped metrics ---
    for group in ["EQUITY", "ETF"]:
        group_df = portfolio_df[portfolio_df["type"] == group]

        if group_df.empty:
            continue

        st.markdown(f"### {group}s")
        rows = math.ceil(len(group_df) / columns_per_row)
        for i in range(rows):
            cols = st.columns(columns_per_row)
            for j in range(columns_per_row):
                idx = i * columns_per_row + j
                if idx >= len(group_df):
                    break

                row = group_df.iloc[idx]
                ticker = row.get("Ticker", "")
                value = row.get("Value (€)", 0.0)
                change = row.get("% Change (1d)", None)

                delta = f"{round(change, 2)}%" if pd.notna(change) else "n/a"
                delta_color = "green" if change and change > 0 else "red" if change and change < 0 else "gray"

                html = f"""
                <div style="text-align: center; padding: 6px; border: 1px solid #e0e0e0; border-radius: 8px;">
                    <div style="font-size: 18px; font-weight: 600;">{ticker}</div>
                    <div style="font-size: 13px; color: #666;">{currency_symbol}{round(value, 2):,.2f}</div>
                    <div style="font-size: 14px; font-weight: bold; color: {delta_color};">
                        {delta}
                    </div>
                </div>
                """
                cols[j].markdown(html, unsafe_allow_html=True)

    return round(weighted_change, 2)


def show_allocation_chart(portfolio_df):
    if portfolio_df.empty:
        st.info("No portfolio data available.")
        return

    # Drop rows with missing type, Ticker, or Value (€)
    required_cols = ["type", "Ticker", "Value (€)"]
    portfolio_df = portfolio_df.dropna(subset=required_cols)

    # Ensure correct data types
    portfolio_df["type"] = portfolio_df["type"].astype(str)
    portfolio_df["Ticker"] = portfolio_df["Ticker"].astype(str)
    portfolio_df["Value (€)"] = pd.to_numeric(portfolio_df["Value (€)"], errors="coerce")
    portfolio_df = portfolio_df[portfolio_df["Value (€)"].notnull() & (portfolio_df["Value (€)"] > 0)]

    if portfolio_df.empty:
        st.info("No valid portfolio entries with defined type and value.")
        return

    fig = px.sunburst(
        portfolio_df,
        path=["type", "Ticker"],
        values="Value (€)",
        title="Portfolio Allocation by Type and Ticker",
    )
    fig.update_traces(textinfo="label+percent entry")

    st.plotly_chart(fig, use_container_width=True)


def show_graph_deposits(cash_df):
    # Base chart (shared X)
    base = alt.Chart(cash_df).encode(
        x=alt.X("date:T", title="Date")
    )

    # Bar chart for cash movements
    bars = base.mark_bar(color="#4e79a7").encode(
        y=alt.Y("signed_amount:Q", title="Daily Cash Flow (€)"),
        tooltip=["date", "type", "amount"]
    )

    # Line chart for cumulative total (right Y-axis)
    line = base.mark_line(color="#f28e2b", strokeWidth=3).encode(
        y=alt.Y("cumulative_total:Q", title="Cumulative Balance (€)", axis=alt.Axis(titleColor="#f28e2b")),
        tooltip=["date", "cumulative_total"]
    )

    # Combine with layered chart
    combined_chart = alt.layer(bars, line).resolve_scale(
        y="independent"  # Two separate Y axes
    ).properties(
        width="container",
        height=400,
        title="Deposits & Withdrawals with Cumulative Balance"
    )

    st.altair_chart(combined_chart, use_container_width=True)


def show_graph_div(div_df):
    # Group per ticker and type
    div_summary = div_df.groupby(["ticker", "type"])["amount"].sum().reset_index()

    # Pivot to get net = gross + tax
    net_df = div_summary.pivot(index="ticker", columns="type", values="amount").fillna(0)
    net_df["Dividend Net"] = net_df.get("Dividend Gross", 0) + net_df.get("Dividend Tax", 0)

    # Keep only Net and Tax
    plot_df = net_df[["Dividend Net", "Dividend Tax"]].reset_index().melt(
        id_vars="ticker", var_name="type", value_name="amount"
    )

    # Flip tax to negative if it's not already
    plot_df.loc[plot_df["type"] == "Dividend Tax", "amount"] \
        = plot_df.loc[plot_df["type"] == "Dividend Tax", "amount"].abs() * -1

    # 🔢 Calculate totals for annotation (but don't plot as bar)
    total_net = plot_df.loc[plot_df["type"] == "Dividend Net", "amount"].sum()
    total_tax = plot_df.loc[plot_df["type"] == "Dividend Tax", "amount"].sum()
    total_label = f"TOTAL: €{total_net:,.1f} Net / €{total_tax:,.1f} Tax"

    # 🎨 Base bar chart
    bar_chart = alt.Chart(plot_df).mark_bar().encode(
        x=alt.X("ticker:N", title="Ticker"),
        y=alt.Y("amount:Q", title="Amount (€)"),
        color=alt.Color("type:N", title="Component", scale=alt.Scale(scheme='set2')),
        tooltip=["ticker", "type", "amount"]
    )

    # 🏷️ Add label as annotation above the highest bar
    max_y = plot_df.groupby("ticker")["amount"].sum().max()
    label_df = pd.DataFrame({
        "ticker": [plot_df["ticker"].iloc[0]],  # place over first bar (or choose another logic)
        "y": [max_y * 1.1],  # position slightly above the tallest bar
        "label": [total_label]
    })

    text = alt.Chart(label_df).mark_text(
        align='left',
        baseline='bottom',
        fontSize=14,
        fontWeight="bold",
        dy=-10
    ).encode(
        x=alt.X("ticker:N"),
        y=alt.Y("y:Q"),
        text="label:N"
    )

    # 🧩 Combine chart
    final_chart = (bar_chart + text).properties(
        width="container",
        height=400,
        title="Dividends: Net (positive) vs Tax (negative)"
    )

    st.altair_chart(final_chart, use_container_width=True)


import pandas as pd
import plotly.graph_objects as go
import streamlit as st

def _to_naive_series(s):
    """Coerce to datetime Series (tz-naive), sorted, with NaT rows dropped."""
    if s is None or len(s) == 0:
        return pd.Series([], dtype="datetime64[ns]")
    out = pd.to_datetime(s, errors="coerce")
    # If it's already dtype datetime64[ns, tz], remove tz; for plain datetime64, .dt works too
    if hasattr(out, "dt"):
        try:
            out = out.dt.tz_localize(None)
        except (TypeError, AttributeError):
            # already tz-naive or not tz-aware
            pass
    out = out.dropna()
    return out

def _rebase_per_year(values: pd.Series, dates: pd.Series) -> pd.Series:
    s_dates = _to_naive_series(dates)
    if s_dates.empty:
        return pd.Series([], dtype=float)
    s_vals = pd.to_numeric(values, errors="coerce")
    s = pd.Series(s_vals.values, index=s_dates).sort_index()

    parts = []
    for _, seg in s.groupby(s.index.year):
        seg = seg.copy()
        first_valid = seg.first_valid_index()
        if first_valid is not None:
            base = seg.loc[first_valid]
            if pd.notna(base) and base != 0:
                seg = seg / base * 100.0
        parts.append(seg)
    out = pd.concat(parts).sort_index()
    return out.reindex(s.index)

def show_graph_development(history: pd.DataFrame, cash_div: pd.DataFrame):
    if history.empty:
        st.info("No historic portfolio data.")
        return

    # Ensure numeric columns
    for c in ("value", "wv", "aex", "sp"):
        if c in history.columns:
            history[c] = pd.to_numeric(history[c], errors="coerce")

    # ===== Absolute chart =====
    hist_dates = _to_naive_series(history["date"])
    hist_sorted = history.loc[hist_dates.index].copy()
    hist_sorted["date"] = hist_dates

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist_sorted["date"], y=hist_sorted["value"], mode="lines", name="Portfolio (€)", line=dict(width=2)))
    fig.add_trace(go.Scatter(x=hist_sorted["date"], y=hist_sorted["wv"],    mode="lines", name="Profit (W/V)",  line=dict(width=2, dash="dot")))
    fig.add_trace(go.Scatter(x=hist_sorted["date"], y=hist_sorted["aex"],   mode="lines", name="AEX",           line=dict(width=1)))
    fig.add_trace(go.Scatter(x=hist_sorted["date"], y=hist_sorted["sp"],    mode="lines", name="S&P 500",       line=dict(width=1, dash="dash")))

    # Deposits (align date range)
    df_cash_sorted = pd.DataFrame()
    if cash_div is not None and not cash_div.empty and "date" in cash_div.columns:
        cash_dates = _to_naive_series(cash_div["date"])
        df_cash_sorted = cash_div.loc[cash_dates.index].copy()
        df_cash_sorted["date"] = cash_dates
        if "cumulative_total" not in df_cash_sorted.columns:
            # fallback if you only have 'amount'
            if "amount" in df_cash_sorted.columns:
                df_cash_sorted = df_cash_sorted.sort_values("date")
                df_cash_sorted["cumulative_total"] = pd.to_numeric(df_cash_sorted["amount"], errors="coerce").fillna(0).cumsum()
            else:
                df_cash_sorted["cumulative_total"] = pd.Series(dtype=float)

        # same date window as history
        start_dt, end_dt = hist_sorted["date"].min(), hist_sorted["date"].max()
        df_cash_sorted = df_cash_sorted[(df_cash_sorted["date"] >= start_dt) & (df_cash_sorted["date"] <= end_dt)]

        fig.add_trace(go.Scatter(
            x=df_cash_sorted["date"], y=df_cash_sorted["cumulative_total"],
            mode="lines", name="Deposits (€)", line=dict(width=1, dash="dot")
        ))

    fig.update_layout(
        title="📈 Historic Portfolio Overview",
        xaxis_title="Date",
        yaxis_title="EUR / Index Value",
        hovermode="x unified",
        height=600
    )
    st.plotly_chart(fig, use_container_width=True)

    # ===== Indexed chart (rebased each year) =====
    value_idx = _rebase_per_year(hist_sorted["value"], hist_sorted["date"])
    wv_idx    = _rebase_per_year(hist_sorted["wv"],    hist_sorted["date"])
    aex_idx   = _rebase_per_year(hist_sorted["aex"],   hist_sorted["date"])
    sp_idx    = _rebase_per_year(hist_sorted["sp"],    hist_sorted["date"])

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=hist_sorted["date"], y=value_idx, mode="lines", name="Portfolio Indexed",    line=dict(width=2)))
    fig2.add_trace(go.Scatter(x=hist_sorted["date"], y=wv_idx,    mode="lines", name="Profit (W/V) Indexed", line=dict(width=2, dash="dot")))
    fig2.add_trace(go.Scatter(x=hist_sorted["date"], y=aex_idx,   mode="lines", name="AEX Indexed",          line=dict(width=1)))
    fig2.add_trace(go.Scatter(x=hist_sorted["date"], y=sp_idx,    mode="lines", name="S&P 500 Indexed",      line=dict(width=1, dash="dash")))

    if not df_cash_sorted.empty and df_cash_sorted["cumulative_total"].notna().any():
        dep_idx = _rebase_per_year(df_cash_sorted["cumulative_total"], df_cash_sorted["date"])
        fig2.add_trace(go.Scatter(x=df_cash_sorted["date"], y=dep_idx, mode="lines", name="Deposits Indexed", line=dict(width=1, dash="dot")))

    fig2.update_layout(
        title="📊 Indexed Performance (rebased to 100 each year)",
        xaxis_title="Date",
        yaxis_title="Index Value (Start of Year = 100)",
        hovermode="x unified",
        height=600
    )
    st.plotly_chart(fig2, use_container_width=True)
