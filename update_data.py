import datetime
import os
import pandas as pd
import yfinance as yf

DATA_DIR = "data/yahoo"


def load_yahoo_data(tickers):
    """
    Download daily and intraday data from Yahoo Finance for a set of tickers,
    perform a cleanup step, and save the results as CSV files into the data/yahoo directory.
    """
    # Ensure the data directory exists
    os.makedirs(DATA_DIR, exist_ok=True)

    for ticker in tickers:
        # Skip empty tickers to avoid errors
        if not ticker.strip():
            print(f"Skipping empty ticker entry: {repr(ticker)}")
            continue

        # --------------------------
        # Download DAILY data
        # --------------------------
        daily_data = yf.download(ticker, period="10y", interval="1d", progress=False)
        if daily_data.empty:
            print(f"No daily data returned for {ticker}. Skipping.")
            continue

        # Clean daily data
        if isinstance(daily_data.columns, pd.MultiIndex):
            daily_data.columns = [col[0].lower() for col in daily_data.columns]
        else:
            daily_data.columns = [col.lower() for col in daily_data.columns]

        # Move date index into a column
        daily_data.reset_index(inplace=True)

        # Rename index column to 'date' if needed
        if "date" not in daily_data.columns:
            daily_data.rename(
                columns={"Date": "date", "Datetime": "date"},
                inplace=True,
                errors="ignore"
            )

        # Optional: add publish_time and symbol columns
        daily_data["publish_time"] = pd.Timestamp.utcnow()
        daily_data["symbol"] = f"YF/{ticker}"

        # Save daily data
        daily_file = os.path.join(DATA_DIR, f"{ticker}_daily.csv")
        daily_data.to_csv(daily_file, index=False)
        print(f"Saved daily data for {ticker} to {daily_file}")

        # --------------------------
        # Download INTRADAY data
        # --------------------------
        today = datetime.date.today()
        sixty_days_ago = today - datetime.timedelta(days=58)
        st = sixty_days_ago.strftime('%Y-%m-%d')
        intraday_data = yf.download(ticker, start=st, interval="5m", progress=False)
        if intraday_data.empty:
            print(f"No intraday data returned for {ticker}. Skipping.")
            continue

        # Clean intraday data
        if isinstance(intraday_data.columns, pd.MultiIndex):
            intraday_data.columns = [col[0].lower() for col in intraday_data.columns]
        else:
            intraday_data.columns = [col.lower() for col in intraday_data.columns]

        # Move date index into a column
        intraday_data.reset_index(inplace=True)

        # Rename index column to 'date' if needed
        if "date" not in intraday_data.columns:
            intraday_data.rename(
                columns={"Date": "date", "Datetime": "date"},
                inplace=True,
                errors="ignore"
            )

        # Optional: add publish_time and symbol columns
        intraday_data["publish_time"] = pd.Timestamp.utcnow()
        intraday_data["symbol"] = f"YF/{ticker}"

        # Save intraday data
        intraday_file = os.path.join(DATA_DIR, f"{ticker}_intraday.csv")
        intraday_data.to_csv(intraday_file, index=False)
        print(f"Saved intraday data for {ticker} to {intraday_file}")


if __name__ == "__main__":
    tickers = ["^VIX", "CL=F", "ES=F", "ZN=F"]
    load_yahoo_data(tickers)
