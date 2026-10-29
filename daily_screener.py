import time
import requests
import pandas as pd
from datetime import datetime, timedelta

def get_daily_chips(stock_id, start_date):
    url = "https://api.finmindtrade.com/api/v4/data"
    institutional_params = {
        "dataset": "TaiwanStockInstitutionalInvestors",
        "data_id": stock_id,
        "start_date": start_date,
    }
    margin_params = {
        "dataset": "TaiwanStockMarginPurchaseShortSale",
        "data_id": stock_id,
        "start_date": start_date,
    }
    try:
        res_inst = requests.get(url, params=institutional_params, timeout=10).json()
        df_inst = pd.DataFrame(res_inst["data"]) if "data" in res_inst and len(res_inst["data"]) > 0 else pd.DataFrame()
        
        res_margin = requests.get(url, params=margin_params, timeout=10).json()
        df_margin = pd.DataFrame(res_margin["data"]) if "data" in res_margin and len(res_margin["data"]) > 0 else pd.DataFrame()
        
        return df_inst, df_margin
    except Exception:
        return pd.DataFrame(), pd.DataFrame()

def analyze_locking_signals(df_inst, df_margin):
    if df_inst.empty or df_margin.empty:
        return False, 0, 0
    
    df_inst['date'] = pd.to_datetime(df_inst['date'])
    df_margin['date'] = pd.to_datetime(df_margin['date'])
    
    if 'buy' in df_inst.columns and 'sell' in df_inst.columns:
        df_inst['net'] = df_inst['buy'] - df_inst['sell']
        df_daily_inst = df_inst.groupby('date')['net'].sum().reset_index()
    else:
        return False, 0, 0

    if 'MarginPurchaseTodayBalance' in df_margin.columns:
        df_daily_margin = df_margin[['date', 'MarginPurchaseTodayBalance']].copy()
    else:
        return False, 0, 0

    merged = pd.merge(df_daily_inst, df_daily_margin, on='date', how='inner').sort_values('date')
    if len(merged) < 5:
        return False, 0, 0
    
    recent_5 = merged.tail(5)
    inst_buy_days = (recent_5['net'] > 0).sum()
    margin_balances = recent_5['MarginPurchaseTodayBalance'].tolist()
    is_margin_decreasing = margin_balances[-1] < margin_balances[0] and (margin_balances[-1] < margin_balances[-2])
    
    is_locked = (inst_buy_days >= 4) and is_margin_decreasing
    return is_locked, margin_balances[-1], margin_balances[-1] - margin_balances[0]

if __name__ == "__main__":
    sample_stocks = ["2330", "2317", "2454", "2881", "3037", "2303", "2603"]
    start_date = (datetime.now() - timedelta(days=20)).strftime("%Y-%m-%d")
    results = []
    
    print("=== 開始執行每日鎖碼篩選 ===")
    for stock_id in sample_stocks:
        df_inst, df_margin = get_daily_chips(stock_id, start_date)
        is_locked, latest_margin, margin_change = analyze_locking_signals(df_inst, df_margin)
        
        if is_locked:
            results.append(f"股票代號: {stock_id} | 最新融資: {latest_margin}張 (5日增減: {margin_change}張)")
        time.sleep(0.4)
        
    today_str = datetime.now().strftime("%Y-%m-%d")
    if results:
        print(f"\n🔥 【大戶日頻鎖碼通知】 ({today_str})\n" + "\n".join(results))
    else:
        print(f"\nℹ️ 【大戶日頻鎖碼通知】 ({today_str})\n今日無符合「法人連買+融資減少」條件的標的。")
