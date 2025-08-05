import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import pandas as pd
import altair as alt
import math


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


def show_graph_development(history, cash_div):
    df_cash_sorted = cash_div[cash_div["date"] >= history["date"].min()]

    def rebase(series):
        return series / series.iloc[0] * 100 if not series.empty else series

    fig = go.Figure()

    # Portfolio Value
    fig.add_trace(go.Scatter(
        x=history["date"], y=history["value"],
        mode="lines", name="Portfolio (€)",
        line=dict(width=2)
    ))

    # Profit (W/V)
    fig.add_trace(go.Scatter(
        x=history["date"], y=history["wv"],
        mode="lines", name="Profit (W/V)",
        line=dict(width=2, dash="dot")
    ))

    # AEX
    fig.add_trace(go.Scatter(
        x=history["date"], y=history["aex"],
        mode="lines", name="AEX",
        line=dict(width=1)
    ))

    # S&P
    fig.add_trace(go.Scatter(
        x=history["date"], y=history["sp"],
        mode="lines", name="S&P 500",
        line=dict(width=1, dash="dash")
    ))

    # Cumulative Deposits
    fig.add_trace(go.Scatter(
        x=cash_div["date"], y=cash_div["cumulative_total"],
        mode="lines", name="Deposits (€)",
        line=dict(width=1, dash="dot")
    ))

    fig.update_layout(
        title="📈 Historic Portfolio Overview",
        xaxis_title="Date",
        yaxis_title="EUR / Index Value",
        hovermode="x unified",
        height=600)

    st.plotly_chart(fig, use_container_width=True)

    # Now make an indexed plot

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=history["date"], y=rebase(history["value"]),
        mode="lines", name="Portfolio Indexed",
        line=dict(width=2)
    ))

    fig.add_trace(go.Scatter(
        x=history["date"], y=rebase(history["wv"]),
        mode="lines", name="Profit (W/V) Indexed",
        line=dict(width=2, dash="dot")
    ))

    fig.add_trace(go.Scatter(
        x=history["date"], y=rebase(history["aex"]),
        mode="lines", name="AEX Indexed",
        line=dict(width=1)
    ))

    fig.add_trace(go.Scatter(
        x=history["date"], y=rebase(history["sp"]),
        mode="lines", name="S&P 500 Indexed",
        line=dict(width=1, dash="dash")
    ))

    fig.add_trace(go.Scatter(
        x=df_cash_sorted["date"], y=rebase(df_cash_sorted["cumulative_total"]),
        mode="lines", name="Deposits Indexed",
        line=dict(width=1, dash="dot")
    ))

    fig.update_layout(
        title="📊 Indexed Performance (rebased to 100)",
        xaxis_title="Date",
        yaxis_title="Index Value (Start = 100)",
        hovermode="x unified",
        height=600
    )
    print('success')

    st.plotly_chart(fig, use_container_width=True)
