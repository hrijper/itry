import pandas as pd
from data.fetch import get_price_and_currency, get_fx_to_eur


def calculate_portfolio(df):
    if df.empty:
        return pd.DataFrame(), 0.0

    holdings = {}
    for _, row in df.iterrows():
        multiplier = 1 if row["type"].lower() == "buy" else -1
        holdings[row["ticker"]] = holdings.get(row["ticker"], 0) + multiplier * row["amount"]

    result = []
    total_eur = 0.0

    for ticker, quantity in holdings.items():
        if quantity == 0:
            continue

        price, currency = get_price_and_currency(ticker)
        fx = get_fx_to_eur(currency) if currency else 1.0
        value_native = round(price * quantity, 2) if price else 0
        value_eur = round(value_native * fx, 2) if fx else 0
        total_eur += value_eur

        result.append({
            "Ticker": ticker,
            "Quantity": quantity,
            "Price": price,
            "Currency": currency,
            "FX to EUR": fx,
            "Value (€)": value_eur
        })

    df_result = pd.DataFrame(result).sort_values(by="Value (€)", ascending=False)
    return df_result, round(total_eur, 2)


def calculate_cash(df):
    cash_df = df[df["type"].isin(["Deposit", "Withdrawal"])].copy()
    cash_df["date"] = pd.to_datetime(cash_df["date"])
    cash_df = cash_df.sort_values("date")

    # Use amount as-is: already negative for withdrawals
    cash_df["signed_amount"] = cash_df["amount"]

    cash_df["cumulative_total"] = cash_df["signed_amount"].cumsum()
    return cash_df

def calculate_div(df):
    div_df = df[df["type"].isin(["Dividend Gross", "Dividend Tax"])].copy()
    div_df["amount"] = pd.to_numeric(div_df["amount"], errors="coerce")
    return div_df