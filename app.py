import streamlit as st
from data.fetch import get_transactions, get_deposits_divs
from data.history_logic import get_historic
from data.portfolio import calculate_portfolio, calculate_cash, calculate_div
from visualizations.charts import show_allocation_chart, show_graph_deposits, show_graph_div, show_portfolio,\
    show_graph_development
from data.submit import submit_transaction_form, submit_deposits_divs_form


# --- Streamlit Setup ---
st.set_page_config(page_title="itry", layout="wide")
st.title("lets try")

# Allow for updating transactions & deposits
submit_transaction_form()
submit_deposits_divs_form()

# load transaction, deposits, dividends
df = get_transactions()
df_div = get_deposits_divs()
cash_df = calculate_cash(df_div)
history = get_historic(df, cash_df)


if df.empty:
    st.warning("No transactions found in Supabase.")
else:
    # Add filter
    all_tickers = df["ticker"].unique().tolist()
    selected_tickers = st.sidebar.multiselect("Filter by ticker", all_tickers, default=all_tickers)
    filtered_df = df[df["ticker"].isin(selected_tickers)]

    # Logic
    portfolio_df, total_value = calculate_portfolio(filtered_df)
    dividends = calculate_div(df_div)

    # Start dashboard
    portfolio_change = show_portfolio(portfolio_df)
    st.metric(
        label="Total Portfolio Value",
        value=f"€{total_value:,.2f}",
        delta=f"{round(portfolio_change, 2)}%"
    )

    # Plot
    show_allocation_chart(portfolio_df)
    show_graph_deposits(cash_df)
    show_graph_development(history, cash_df)
    show_graph_div(dividends)

