from supabase import create_client
import streamlit as st
import datetime

url = st.secrets["url"]
key = st.secrets["key"]
supabase = create_client(url, key)


def submit_transaction_form():
    with st.expander("➕ Add New Transaction"):
        with st.form("add_transaction"):
            ticker = st.text_input("Ticker (e.g. ASML.AS)")
            date = st.date_input("Date", value=datetime.date.today())
            amount = st.number_input("Amount", step=1.0)
            price = st.number_input("Price", step=0.01)
            tx_type = st.selectbox("Type", ["buy", "sell"])
            currency = st.selectbox("Currency", ["EUR", "USD", "HKD"])
            fx_rate = st.number_input("FX Rate", value=1.0)
            fee = st.number_input("Transaction Fee", value=0.0)
            total_value = amount * price
            submit = st.form_submit_button("Submit")

        if submit:
            record = {
                "date": str(date),
                "ticker": ticker,
                "amount": amount,
                "price": price,
                "type": tx_type,
                "currency": currency,
                "fx_rate": fx_rate,
                "transaction_fee": fee,
                "total_value": total_value
            }
            try:
                supabase.table("transactions").insert(record).execute()
                st.success("✅ Transaction added.")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Failed to add transaction: {e}")


def submit_deposits_divs_form():
    with st.expander("➕ Add New Deposit/Dividend"):
        with st.form("add_deposit_div"):
            ticker = st.text_input("Ticker (e.g. ASML.AS)")
            date = st.date_input("Date", value=datetime.date.today())
            amount = st.number_input("Amount", step=1.0)
            currency = st.selectbox("Currency", ["EUR", "USD", "HKD"])
            type_text = st.selectbox("Type", ["Deposit", "Dividend Gross", "Dividend Tax", "Withdrawal"])
            submit = st.form_submit_button("Submit")

        if submit:
            record = {
                "date": str(date),
                "ticker": ticker,
                "amount": amount,
                "type": type_text,
                "currency": currency,
            }
            try:
                supabase.table("transactions_div").insert(record).execute()
                st.success("✅ Deposit/Div added.")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Failed to add deposit/div: {e}")
