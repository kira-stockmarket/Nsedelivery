import pandas as pd
import requests
from datetime import datetime, timedelta
from jugaad_data.nse import full_bhavcopy_save
import os

def run():
    # 1. Determine the latest trading day (skip weekends)
    today = datetime.today().date()
    if today.weekday() == 5:   # Saturday -> Friday
        today -= timedelta(days=1)
    elif today.weekday() == 6: # Sunday -> Friday
        today -= timedelta(days=2)

    print(f"Fetching Bhavcopy for: {today}")
    
    # 2. Download NSE Bhavcopy into temporary runner space
    try:
        file_path = full_bhavcopy_save(today, ".")
    except Exception as e:
        print(f"Bhavcopy not released yet: {e}")
        return

    # 3. Read and clean data
    df = pd.read_csv(file_path)
    df.columns = df.columns.str.strip()
    df = df[df['SERIES'] == ' EQ'].copy()

    # Convert numeric fields
    df['CLOSE_PRICE'] = pd.to_numeric(df['CLOSE_PRICE'], errors='coerce')
    df['PREV_CLOSE'] = pd.to_numeric(df['PREV_CLOSE'], errors='coerce')
    df['TTL_TRD_QNTY'] = pd.to_numeric(df['TTL_TRD_QNTY'], errors='coerce')
    df['DELIV_PER'] = pd.to_numeric(df['DELIV_PER'], errors='coerce')

    # Price change and turnover in ₹ Crores
    df['CHANGE_PCT'] = ((df['CLOSE_PRICE'] - df['PREV_CLOSE']) / df['PREV_CLOSE']) * 100
    df['TURNOVER_CR'] = (df['CLOSE_PRICE'] * df['TTL_TRD_QNTY'] * (df['DELIV_PER'] / 100)) / 10000000

    # 4. Filter for institutional focus (Price > 30, High Volume)
    df = df[(df['CLOSE_PRICE'] > 30) & (df['TTL_TRD_QNTY'] > 50000)]
    
    # Sort by delivery turnover (₹ Crores)
    top_stocks = df.sort_values(by='TURNOVER_CR', ascending=False).head(100)

    # 5. Format payload for dashboard
    output = []
    for _, r in top_stocks.iterrows():
        output.append({
            "symbol": r['SYMBOL'],
            "name": r['SYMBOL'],
            "sector": "Equity",
            "ltp": round(r['CLOSE_PRICE'], 2),
            "change": round(r['CHANGE_PCT'], 2),
            "volume": int(r['TTL_TRD_QNTY']),
            "delivery": round(r['DELIV_PER'], 1),
            "turnoverCr": round(r['TURNOVER_CR'], 2),
            "surge": 1.5,
            "streak": 1
        })

    # 6. Save JSON (Discarding the heavy CSV)
    import json
    with open('market_data.json', 'w') as f:
        json.dump(output, f, indent=2)

    # Delete the heavy CSV so it never enters the git repo
    if os.path.exists(file_path):
        os.remove(file_path)

    print("market_data.json generated successfully!")

if __name__ == "__main__":
    run()
