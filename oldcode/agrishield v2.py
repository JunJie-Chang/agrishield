import pandas as pd
import numpy as np
import yfinance as yf
import requests
import json
import os
import urllib3
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta

# 關閉 requests 的 SSL 警告 (針對農委會 API)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ---------------------------------------------------------
# 1. 農產品數據抓取器 (API + Cache)
# ---------------------------------------------------------
def get_moa_agri_data(crop_code, crop_name="Unknown", days=365, force_update=False):
    """
    從農委會 API 抓取資料，自動存成 json，下次直接讀檔
    """
    json_filename = f"agri_data_{crop_code}.json"
    
    # A. 嘗試讀取本地快取
    if not force_update and os.path.exists(json_filename):
        print(f"[{crop_name}] 發現本地快取 '{json_filename}'，讀取中...")
        try:
            with open(json_filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return process_agri_json(data)
        except Exception as e:
            print(f"[{crop_name}] 快取讀取失敗，改用 API 下載...")

    # B. API 下載
    base_url = "https://data.moa.gov.tw/api/v1/AgriProductsTransType/"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    def to_roc_date(dt):
        return f"{dt.year - 1911}.{dt.month:02d}.{dt.day:02d}"
    
    params = {
        "Start_time": to_roc_date(start_date),
        "End_time": to_roc_date(end_date),
        "CropCode": crop_code, 
        "MarketName": "台北一", # 鎖定台北一市場，避免全台平均失真
        "format": "json"
    }
    
    print(f"[{crop_name}] 呼叫 API中... ({crop_code})")
    
    try:
        response = requests.get(base_url, params=params, verify=False)
        response.raise_for_status()
        data = response.json()
        
        if "Data" in data and len(data["Data"]) > 0:
            print(f"[{crop_name}] API 下載成功，存檔至 '{json_filename}'")
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            return process_agri_json(data)
        else:
            print(f"[{crop_name}] API 回傳無資料 (可能代碼錯誤或休市)")
            return pd.Series(dtype='float64')
            
    except Exception as e:
        print(f"[{crop_name}] API 請求失敗: {e}")
        return pd.Series(dtype='float64')

def process_agri_json(data):
    """處理 JSON 轉 Pandas Series"""
    if "Data" in data and len(data["Data"]) > 0:
        df = pd.DataFrame(data["Data"])
        clean_df = df[['TransDate', 'Avg_Price']].copy()
        
        def roc_to_ad(date_str):
            try:
                y, m, d = date_str.split('.')
                return f"{int(y)+1911}-{m}-{d}"
            except: return None
        
        clean_df['Date'] = pd.to_datetime(clean_df['TransDate'].apply(roc_to_ad))
        clean_df['Price'] = pd.to_numeric(clean_df['Avg_Price'], errors='coerce')
        
        clean_df.dropna(inplace=True)
        clean_df.set_index('Date', inplace=True)
        clean_df.sort_index(inplace=True)
        
        # 這裡很重要：農產品市場週末有開，金融市場沒開
        # 但我們回傳原始 Series，留給後面 merge 時去對齊
        return clean_df['Price']
    return pd.Series(dtype='float64')

# ---------------------------------------------------------
# 2. 金融數據抓取 (Financial Data Fetcher)
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
# 3. 核心引擎：Macro-Agri Scanner
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
        # 過濾掉 NaN (如果資料不足)
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

# ---------------------------------------------------------
# 主程式執行區
# ---------------------------------------------------------
if __name__ == "__main__":
    
    # === A. 設定你想分析的作物清單 ===
    # 你可以在這裡自由新增 (去查代碼表)
    TARGET_CROPS = [
        {"code": "LA2", "name": "茭白筍"},
        {"code": "LA1", "name": "甘藍(高麗菜)"}, 
        {"code": "LC1", "name": "包心白菜"},
        {"code": "LD1", "name": "小白菜"},
        {"code": "LC2", "name": "青江白菜"},
        {"code": "LF2", "name": "空心菜"},
        {"code": "SA3", "name": "蘿蔔"},
        {"code": "SF1", "name": "洋蔥"},
        {"code": "SD1", "name": "馬鈴薯"},
        {"code": "SE1", "name": "青蔥"},
        {"code": "FB1", "name": "花椰菜"},
        {"code": "FI1", "name": "玉米筍"}, 
        {"code": "FJ3", "name": "番茄"}
    ]
    
    # === B. 抓取所有農產品資料 ===
    agri_dataset = {}
    min_date = datetime.now()
    
    print("=== Step 1: 啟動農產品數據下載引擎 ===")
    for crop in TARGET_CROPS:
        series = get_moa_agri_data(crop["code"], crop["name"], days=365*2) # 抓2年
        if not series.empty:
            agri_dataset[crop["name"]] = series
            # 記錄最早日期，為了抓金融數據用
            if series.index.min() < min_date:
                min_date = series.index.min()
    
    if not agri_dataset:
        print("錯誤：沒有抓到任何農產品資料，程式終止。")
        exit()

    # === C. 抓取金融資料 (一次抓足) ===
    print("\n=== Step 2: 下載全球金融數據 ===")
    start_str = min_date.strftime('%Y-%m-%d')
    end_str = datetime.now().strftime('%Y-%m-%d')
    finance_df = get_financial_universe(start_str, end_str)
    
    if finance_df.empty:
        print("錯誤：金融數據下載失敗。")
        exit()

    # === D. 執行掃描與產出報告 ===
    print("\n=== Step 3: 執行 Macro-Agri 相關性掃描 ===")
    
    all_reports = []
    
    for crop_name, series in agri_dataset.items():
        print(f"正在分析: {crop_name}...")
        report = run_scanner(series, finance_df, crop_name)
        if not report.empty:
            all_reports.append(report)
            
            # 印出該作物的第一名
            top = report.iloc[0]
            print(f"  -> 發現最佳指標: {top['Asset']} (Corr: {top['Best_Correlation']}, {top['Timing']})")

    # === E. 總結報告存檔 ===
    if all_reports:
        final_df = pd.concat(all_reports, ignore_index=True)
        
        # 存 CSV
        final_df.to_csv("AgriShield_Full_Report.csv", index=False)
        print("\n" + "="*60)
        print("【AgriShield 完整分析完成】")
        print("報告已儲存至: AgriShield_Full_Report.csv")
        print("="*60)
        print(final_df.head(10).to_string(index=False))
    else:
        print("沒有產生任何有效報告。")
