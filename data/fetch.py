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
        quote_type = info.get("quoteType", "Equity")  # Default to Equity
        hist = yf_ticker.history(period="1d")
        if hist.empty:
            return None, None, None
        price = round(hist["Close"].iloc[-1], 2)
        return price, currency, quote_type
    except Exception as e:
        print(f"⚠️ get_price_and_currency error for {ticker}: {e}")
        return None, None, None


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


def fetch_index_value(symbol: str, day: pd.Timestamp) -> float | None:
    """Return the last available close <= day as a float, else None."""
    start = pd.to_datetime(day) - pd.Timedelta(days=7)  # small window to tolerate holidays
    end   = pd.to_datetime(day) + pd.Timedelta(days=1)  # yfinance end is exclusive
    try:
        hist = yf.Ticker(symbol).history(start=start, end=end, auto_adjust=False)
        if hist.empty or "Close" not in hist:
            return None
        # take last close at or before 'day'
        s = hist["Close"].loc[:pd.to_datetime(day)]
        if s.empty:
            return None
        return float(s.iloc[-1])
    except Exception:
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
