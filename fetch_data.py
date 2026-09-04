import pandas as pd
from datetime import datetime, timedelta
from jugaad_data.nse import full_bhavcopy_save
import os
import json

def run():
    print("Initializing Multi-Timeframe Data Engine...")
    current_date = datetime.today().date()
    historical_dfs = []
    
    # 1. Fetch the last 20 valid trading days
    while len(historical_dfs) < 20:
        if current_date.weekday() < 5:  # Skip weekends
            try:
                file_path = full_bhavcopy_save(current_date, ".")
                df = pd.read_csv(file_path)
                df.columns = df.columns.str.strip()
                df = df[df['SERIES'] == ' EQ'].copy()
                
                # Clean Data
                df['CLOSE_PRICE'] = pd.to_numeric(df['CLOSE_PRICE'], errors='coerce')
                df['PREV_CLOSE'] = pd.to_numeric(df['PREV_CLOSE'], errors='coerce')
                df['TTL_TRD_QNTY'] = pd.to_numeric(df['TTL_TRD_QNTY'], errors='coerce')
                df['DELIV_QTY'] = pd.to_numeric(df['DELIV_QTY'], errors='coerce')
                
                # Add Date indicator
                df['T_INDEX'] = len(historical_dfs) # 0 is today, 19 is oldest
                historical_dfs.append(df)
                os.remove(file_path) # Clean up large CSV
                print(f"Successfully fetched: {current_date}")
            except Exception:
                pass # Holiday or data not published yet
                
        current_date -= timedelta(days=1)
        if len(historical_dfs) == 0 and (datetime.today().date() - current_date).days > 10:
            print("Could not find recent NSE data.")
            return

    # 2. Merge all 20 days of data
    master_df = pd.concat(historical_dfs)
    
    final_output = []
    symbols = master_df['SYMBOL'].unique()
    
    print("Calculating Weekly and Monthly aggregations...")
    for sym in symbols:
        stock_data = master_df[master_df['SYMBOL'] == sym].sort_values('T_INDEX')
        if len(stock_data) < 20 or stock_data['CLOSE_PRICE'].iloc[0] < 50:
            continue # Skip illiquid or new listings
            
        # Daily Stats (T_INDEX == 0)
        day_0 = stock_data.iloc[0]
        ltp = day_0['CLOSE_PRICE']
        daily_chg = ((ltp - day_0['PREV_CLOSE']) / day_0['PREV_CLOSE']) * 100
        daily_deliv = (day_0['DELIV_QTY'] / day_0['TTL_TRD_QNTY']) * 100 if day_0['TTL_TRD_QNTY'] > 0 else 0
        daily_turnover = (ltp * day_0['DELIV_QTY']) / 10000000
        
        if daily_turnover < 5: continue # Ignore penny volume
        
        # Weekly Stats (Last 5 Days)
        week_data = stock_data.head(5)
        week_qty = week_data['TTL_TRD_QNTY'].sum()
        week_deliv_qty = week_data['DELIV_QTY'].sum()
        week_deliv_pct = (week_deliv_qty / week_qty) * 100 if week_qty > 0 else 0
        week_chg = ((ltp - week_data['PREV_CLOSE'].iloc[-1]) / week_data['PREV_CLOSE'].iloc[-1]) * 100
        week_turnover = (week_data['CLOSE_PRICE'] * week_data['DELIV_QTY']).sum() / 10000000
        
        # Monthly Stats (Last 20 Days)
        month_data = stock_data
        month_qty = month_data['TTL_TRD_QNTY'].sum()
        month_deliv_qty = month_data['DELIV_QTY'].sum()
        month_deliv_pct = (month_deliv_qty / month_qty) * 100 if month_qty > 0 else 0
        month_chg = ((ltp - month_data['PREV_CLOSE'].iloc[-1]) / month_data['PREV_CLOSE'].iloc[-1]) * 100
        month_turnover = (month_data['CLOSE_PRICE'] * month_data['DELIV_QTY']).sum() / 10000000
        
        final_output.append({
            "symbol": sym, "ltp": round(ltp, 2),
            "daily": {"change": round(daily_chg, 2), "deliv": round(daily_deliv, 1), "turnover": round(daily_turnover, 1)},
            "weekly": {"change": round(week_chg, 2), "deliv": round(week_deliv_pct, 1), "turnover": round(week_turnover, 1)},
            "monthly": {"change": round(month_chg, 2), "deliv": round(month_deliv_pct, 1), "turnover": round(month_turnover, 1)}
        })
        
    with open('market_data.json', 'w') as f:
        json.dump(final_output, f, indent=2)
    print("Multi-timeframe JSON generated successfully!")

if __name__ == "__main__":
    run()
