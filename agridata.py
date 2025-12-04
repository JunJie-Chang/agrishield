import requests
import pandas as pd
import json
import os
import urllib3
from datetime import datetime, timedelta

# 關閉 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_moa_agri_data(crop_code, crop_name="Unknown", days=365, force_update=False):
    """
    通用版農產品抓取器
    參數:
    - crop_code: 作物代碼 (必填, e.g., "LA2", "LA1")
    - crop_name: 作物中文名 (選填, 用於顯示訊息)
    - days: 抓取天數
    - force_update: 是否強制刷新 API
    """
    # 1. 自動生成檔名
    target_dir = "agridata"
    json_filename = f"agri_data_{crop_code}.json"
    json_file_path = os.path.join(target_dir, json_filename)

    # 2. 檢查本地快取
    if not force_update and os.path.exists(json_file_path):
        print(f"[{crop_name}] 發現本地快取 '{json_file_path}'，直接讀取...")
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return process_agri_json(data)
        except Exception as e:
            print(f"[{crop_name}] 讀取快取失敗，轉為 API 下載...")

    # 3. 準備 API 請求
    base_url = "https://data.moa.gov.tw/api/v1/AgriProductsTransType/"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    def to_roc_date(dt):
        return f"{dt.year - 1911}.{dt.month:02d}.{dt.day:02d}"

    params = {
        "Start_time": to_roc_date(start_date),
        "End_time": to_roc_date(end_date),
        "CropCode": crop_code,
        "MarketName": "台北一",
        "format": "json"
    }

    print(f"[{crop_name}] 正在呼叫 API... (Code: {crop_code})")
    try:
        response = requests.get(base_url, params=params, verify=False)
        response.raise_for_status()
        data = response.json()

        # 4. 存檔
        if "Data" in data and len(data["Data"]) > 0:
            print(f"[{crop_name}] 下載成功！存檔至 '{json_file_path}'")
            with open(json_file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            return process_agri_json(data)
        else:
            print(f"[{crop_name}] API 回傳無資料 (可能代碼錯誤或休市)")
            return pd.Series(dtype='float64')

    except Exception as e:
        print(f"[{crop_name}] API 請求失敗: {e}")
        return pd.Series(dtype='float64')

def process_agri_json(data):
    if "Data" in data and len(data["Data"]) > 0:
        df = pd.DataFrame(data["Data"])
        # 確保欄位存在
        if 'TransDate' not in df.columns or 'Avg_Price' not in df.columns:
            return pd.Series(dtype='float64')
            
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
        
        return clean_df['Price']
    
    return pd.Series(dtype='float64')
