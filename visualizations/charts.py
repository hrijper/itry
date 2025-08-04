import plotly.express as px
import streamlit as st
import pandas as pd
import altair as alt


def show_portfolio(portfolio_df):
    def background_day_change(val):
        if pd.isna(val):
            return ""
        try:
            val = float(val)
        except:
            return ""

        # Scale color intensity: 0–5% = 0–1 alpha (capped)
        alpha = min(abs(val), 5) / 5
        if val > 0:
            color = f"rgba(0, 255, 0, {alpha})"  # green background
        elif val < 0:
            color = f"rgba(255, 0, 0, {alpha})"  # red background
        else:
            color = "rgba(255, 255, 255, 0)"  # neutral
        return f"background-color: {color}"

    # st.dataframe(portfolio_df, use_container_width=True)
    st.dataframe(
        portfolio_df.style.applymap(background_day_change, subset=["% Change (1d)"]),
        use_container_width=True
    )


def show_allocation_chart(portfolio_df):
    if not portfolio_df.empty:
        fig = px.pie(
            portfolio_df,
            values="Value (€)",
            names="Ticker",
            title="Portfolio Allocation by Ticker",
            hole=0.3
        )
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