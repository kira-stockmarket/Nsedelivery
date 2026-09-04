import pandas as pd
from datetime import datetime, timedelta
from jugaad_data.nse import full_bhavcopy_save
import os
import json

# Broad universe of NSE ETFs
ETF_WATCHLIST = [
    "NIFTYBEES", "BANKBEES", "ITBEES", "AUTOBEES", "PHARMABEES", 
    "GOLDBEES", "SILVERBEES", "MIDCPBEES", "CONSUMBEES", "PSUBNKBEES",
    "JUNIORBEES", "HDFCSILVER", "HDFCGOLD", "SETFGOLD", "MID150BEES",
    "NIFTY100", "QNIFTY", "CPSEETF"
]

def run():
    print("Fetching High-Volume ETF Trend Data...")
    current_date = datetime.today().date()
    historical_dfs = []
    
    target_days = 180
    while len(historical_dfs) < target_days:
        if current_date.weekday() < 5:
            try:
                file_path = full_bhavcopy_save(current_date, ".")
                df = pd.read_csv(file_path)
                df.columns = df.columns.str.strip()
                
                df = df[df['SYMBOL'].isin(ETF_WATCHLIST)].copy()
                if not df.empty:
                    df['CLOSE_PRICE'] = pd.to_numeric(df['CLOSE_PRICE'], errors='coerce')
                    df['PREV_CLOSE'] = pd.to_numeric(df['PREV_CLOSE'], errors='coerce')
                    df['TTL_TRD_QNTY'] = pd.to_numeric(df['TTL_TRD_QNTY'], errors='coerce')
                    
                    df['T_INDEX'] = len(historical_dfs)
                    historical_dfs.append(df)
                
                os.remove(file_path)
                print(f"Fetched session index {len(historical_dfs)}/{target_days}: {current_date}")
            except Exception:
                pass
        current_date -= timedelta(days=1)
        if (datetime.today().date() - current_date).days > (target_days * 2):
            break

    if not historical_dfs:
        print("Error: No historical data fetched.")
        return

    master_df = pd.concat(historical_dfs)
    etf_output = []

    for symbol in ETF_WATCHLIST:
        etf_df = master_df[master_df['SYMBOL'] == symbol]
        if etf_df.empty:
            continue

        latest_idx = etf_df['T_INDEX'].min()
        day_0 = etf_df[etf_df['T_INDEX'] == latest_idx].iloc[0]
        
        ltp = day_0['CLOSE_PRICE']
        prev_close = day_0['PREV_CLOSE']
        change_pct = ((ltp - prev_close) / prev_close) * 100 if prev_close > 0 else 0
        turnover_cr = (ltp * day_0['TTL_TRD_QNTY']) / 10000000

        # STRICT LIQUIDITY FILTER: Skip ETFs with less than ₹10 Crore daily turnover
        if turnover_cr < 10.0:
            continue

        # 9-Month rolling liquidity & price trend blocks
        trend_9m = []
        for block in range(9):
            block_data = etf_df[(etf_df['T_INDEX'] >= block * 20) & (etf_df['T_INDEX'] < (block + 1) * 20)]
            if not block_data.empty:
                b_qty = block_data['TTL_TRD_QNTY'].mean()
                b_price = block_data['CLOSE_PRICE'].mean()
                b_turn = (b_price * b_qty) / 10000000
                trend_9m.append({"block": block + 1, "turnover_cr": round(b_turn, 1), "price": round(b_price, 2)})

        etf_output.append({
            "symbol": symbol,
            "ltp": round(ltp, 2),
            "change": round(change_pct, 2),
            "turnover_cr": round(turnover_cr, 2),
            "trend_9months": trend_9m
        })

    # Sort high volume/turnover to the top
    etf_output = sorted(etf_output, key=lambda x: x['turnover_cr'], reverse=True)

    with open('market_data.json', 'w') as f:
        json.dump(etf_output, f, indent=2)
    print("High-Volume ETF JSON generated successfully!")

if __name__ == "__main__":
    run()
