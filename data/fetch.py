import yfinance as yf
import requests
import pandas as pd
from supabase_client import supabase
import streamlit as st
from datetime import datetime, timedelta

def get_transactions():
    response = supabase.table("transactions").select("*").execute()
    return pd.DataFrame(response.data)


@st.cache_data(ttl=300)
def get_deposits_divs():
    response = supabase.table("transactions_div").select("*").execute()
    return pd.DataFrame(response.data)


@st.cache_data(ttl=3600)
def get_price_and_currency(ticker):
    try:
        yf_ticker = yf.Ticker(ticker)
        info = yf_ticker.info
        currency = info.get("currency", "EUR")
        data = yf_ticker.history(period="1d")
        price = round(data["Close"].iloc[-1], 2)
        return price, currency
    except:
        return None, None


@st.cache_data(ttl=3600)
def get_fx_to_eur(from_currency):
    if from_currency == "EUR":
        return 1.0
    try:
        url = f"https://open.er-api.com/v6/latest/{from_currency}"
        response = requests.get(url)
        data = response.json()
        if data["result"] == "success":
            return data["rates"]["EUR"]
    except:
        pass
    return None


@st.cache_data(ttl=86400)
def get_price_history(ticker, start_date):
    try:
        data = yf.Ticker(ticker).history(start=start_date)
        return data["Close"]
    except:
        return pd.Series()


@st.cache_data(ttl=86400)
def get_benchmark(name):
    tickers = {
        "AEX": "^AEX",
        "NASDAQ": "^IXIC",
        "S&P 500": "^GSPC"
    }
    try:
        return yf.Ticker(tickers[name]).history(period="1y")["Close"]
    except:
        return pd.Series()


def fetch_index_value(ticker, date):
    try:
        data = yf.download(ticker, start=date, end=date + timedelta(days=1), progress=False)
        return round(data["Close"].iloc[0], 2) if not data.empty else None
    except:
        return None


@st.cache_data(ttl=3600)
def get_yesterday_price(ticker):
    try:
        # Get last 7 calendar days of daily data
        data = yf.download(ticker, period="7d", interval="1d", progress=False)
        closes = data["Close"].dropna()

        if len(closes) >= 2:
            # Most recent and second most recent closes
            price_check = closes.iloc[-1].item()
            price_yesterday = closes.iloc[-2].item()
            return price_check, price_yesterday
    except Exception as e:
        print(f"⚠️ Failed to fetch price history for {ticker}: {e}")
    return None, None
