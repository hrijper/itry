import streamlit as st
from data.fetch import get_transactions, get_transactions_div
from data.portfolio import calculate_portfolio, calculate_cash, calculate_div
from visualizations.charts import show_allocation_chart, show_graph_deposits, show_graph_div

# --- Streamlit Setup ---
st.set_page_config(page_title="Stats", layout="wide")
st.title("Bonjour")

df = get_transactions()
df_div = get_transactions_div()

if df.empty:
    st.warning("No transactions found in Supabase.")
else:
    all_tickers = df["ticker"].unique().tolist()
    selected_tickers = st.sidebar.multiselect("Filter by ticker", all_tickers, default=all_tickers)
    filtered_df = df[df["ticker"].isin(selected_tickers)]

    portfolio_df, total_value = calculate_portfolio(filtered_df)
    cash_df = calculate_cash(df_div)
    dividends = calculate_div(df_div)

    st.subheader("📊 Portfolio Overview")
    st.dataframe(portfolio_df, use_container_width=True)
    st.metric("Total Portfolio Value (€)", f"€{total_value}")

    show_allocation_chart(portfolio_df)
    show_graph_deposits(cash_df)
    show_graph_div(dividends)