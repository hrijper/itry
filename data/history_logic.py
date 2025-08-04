import pandas as pd
import yfinance as yf
from data.fetch import fetch_index_value
from datetime import datetime, timedelta
from supabase_client import supabase
from data.fetch import get_transactions, get_deposits_divs  # assume these exist
import streamlit as st

@st.cache_data(ttl=300)
def get_historic(df, df_div):
    response = supabase.table("historic_data").select("*").execute()
    historic = pd.DataFrame(response.data)

    if historic.empty:
        start_date = historic["date"].min()  # fallback
    else:
        start_date = pd.to_datetime(historic["date"].max()) + timedelta(days=1)

    end_date = pd.Timestamp("today").normalize() - timedelta(days=1)
    missing_days = pd.date_range(start=start_date, end=end_date, freq="B")  # B = business days

    new_records = []
    for day in missing_days:
        value = calculate_portfolio_value_on_date(df, day)
        deposits = calculate_net_deposit_up_to(df_div, day)
        wv = round(value - deposits, 2)

        aex = fetch_index_value("^AEX", day)
        sp500 = fetch_index_value("^GSPC", day)

        new_records.append({
            "date": day.strftime("%Y-%m-%d"),
            "value": round(value, 2),
            "wv": wv,
            "aex": aex.iloc[0],
            "sp": sp500.iloc[0]
        })

    if new_records:
        supabase.table("historic_data").upsert(new_records).execute()
        print("✅ Historic data updated.")
        response = supabase.table("historic_data").select("*").execute()
    else:
        print("⚠️ No missing days to update.")

    return pd.DataFrame(response.data)


def get_fx_rate_to_eur(currency, date):
    if currency == "EUR":
        return 1.0
    try:
        fx_pair = f"{currency}EUR=X"
        hist = yf.Ticker(fx_pair).history(start=date, end=date + pd.Timedelta(days=1))
        if not hist.empty:
            return hist["Close"].iloc[0]
    except Exception as e:
        print(f"⚠️ FX error for {currency} on {date}: {e}")
    return None


def calculate_portfolio_value_on_date(transactions_df, date):
    transactions_df["date"] = pd.to_datetime(transactions_df["date"]).dt.tz_localize(None)
    date = pd.to_datetime(date).tz_localize(None)

    filtered = transactions_df[transactions_df["date"] <= date]

    # Determine net holdings per ticker
    holdings = (
        filtered.groupby(["ticker", "type"])["amount"]
        .sum()
        .unstack(fill_value=0)
        .fillna(0)
    )
    holdings["net"] = holdings.get("buy", 0) - holdings.get("sell", 0)
    net_holdings = holdings["net"]

    total_value_eur = 0.0

    for ticker, amount in net_holdings.items():
        if amount == 0:
            continue

        # ⚠️ Get most recent currency used for this ticker before or on the date
        currency_series = filtered[filtered["ticker"] == ticker].sort_values("date")["currency"]
        currency = currency_series.iloc[-1] if not currency_series.empty else "EUR"

        try:
            hist = yf.Ticker(ticker).history(start=date, end=date + pd.Timedelta(days=1))
            if hist.empty:
                continue
            price = hist["Close"].iloc[0]
            fx_rate = get_fx_rate_to_eur(currency, date)
            if fx_rate is None:
                print(f"❌ No FX rate for {currency}, skipping {ticker}")
                continue
            # print(str(ticker) + ' amount ' + str(amount) + ' and value = ' + str(price * amount * fx_rate))
            total_value_eur += price * amount * fx_rate
        except Exception as e:
            print(f"⚠️ Error with {ticker}: {e}")
            continue

    return round(total_value_eur, 2)


def calculate_net_deposit_up_to(cashflows_df,date):
    cashflows_df["date"] = pd.to_datetime(cashflows_df["date"]).dt.tz_localize(None)
    filtered = cashflows_df[cashflows_df["date"] <= date]
    return filtered["amount"].sum()