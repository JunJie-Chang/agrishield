import pandas as pd
import numpy as np
import yfinance as yf
# import matplotlib.pyplot as plt # 若您後續需要繪圖功能可保留
# import seaborn as sns

# ---------------------------------------------------------
# 1. 金融數據抓取 (Financial Data Fetcher)
# ---------------------------------------------------------
def get_financial_universe(start_date, end_date):
    """
    抓取四大資產池 (Logic Filter)
    """
    tickers_map = {
        'CL=F': 'Oil (Cost)',
        'NG=F': 'Gas (Fertilizer)',
        'MOO': 'Agri-Business ETF',
        'DBC': 'Commodity Index',
        'GLD': 'Gold',
        'XLP': 'Consumer Staples',
        'TWD=X': 'USD/TWD',
        '^TWII': 'Taiwan Weighted'
    }

    print(f"正在下載金融指標 ({len(tickers_map)} 檔)...")
    try:
        tickers = list(tickers_map.keys())
        # yfinance 下載
        df = yf.download(tickers, start=start_date, end=end_date, progress=False)['Close']
        
        # 處理 column 名稱 (MultiIndex 問題)
        if isinstance(df.columns, pd.MultiIndex):
            try:
                df.columns = df.columns.get_level_values(0)
            except: pass
            
        df.rename(columns=tickers_map, inplace=True)
        valid_cols = [c for c in df.columns if c in tickers_map.values()]
        
        return df[valid_cols]
    except Exception as e:
        print(f"Yahoo Finance API 錯誤: {e}")
        return pd.DataFrame()

# ---------------------------------------------------------
# 2. 核心引擎：Macro-Agri Scanner
# ---------------------------------------------------------
def run_scanner(agri_series, finance_df, crop_name):
    """
    計算單一作物的相關性報告
    """
    # 轉換 Series 為 DataFrame 方便合併
    agri_df = agri_series.to_frame(name='Price')

    # 合併：Left Join (保留農產品日期)，並用 ffill 補齊金融數據 (處理週末/休市)
    merged = agri_df.join(finance_df, how='left').fillna(method='ffill')
    merged.dropna(inplace=True) # 刪除最前面的空值
    merged.to_csv(f'merged/merged_data_{crop_name}.csv')


    if len(merged) < 30:
        print(f"[{crop_name}] 有效交易日過少 ({len(merged)}天)，跳過分析")
        return pd.DataFrame()

    results = []
    target_col = 'Price'
    feature_cols = finance_df.columns

    for asset in feature_cols:
        # A. 同步相關 (T=0)
        corr_0 = merged[target_col].corr(merged[asset])
        
        # B. 領先相關 (T-1週, T-1月)
        lag_1w = merged[target_col].corr(merged[asset].shift(5))
        lag_1m = merged[target_col].corr(merged[asset].shift(20))

        # 找最強
        candidates = [corr_0, lag_1w, lag_1m]
        # 過濾掉 NaN
        candidates = [c for c in candidates if not np.isnan(c)]
        
        if not candidates: continue
        
        best_corr = max(candidates, key=abs)
        
        if best_corr == corr_0: timing = "Synchronized"
        elif best_corr == lag_1w: timing = "Leading (1 Week)"
        else: timing = "Leading (1 Month)"

        results.append({
            'Crop': crop_name,
            'Asset': asset,
            'Best_Correlation': round(best_corr, 4),
            'Timing': timing,
            'Sync_Corr': round(corr_0, 4),
            'Lag_1W_Corr': round(lag_1w, 4),
            'Lag_1M_Corr': round(lag_1m, 4)
        })

    if not results: return pd.DataFrame()

    res_df = pd.DataFrame(results)
    res_df['Abs_Corr'] = res_df['Best_Correlation'].abs()
    res_df = res_df.sort_values('Abs_Corr', ascending=False).drop(columns=['Abs_Corr'])
    
    return res_df
