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
    
    # 1. 自動生成檔名 (避免不同作物互相覆蓋)
    # 檔名格式: agri_data_{代碼}.json (例如: agri_data_LA2.json)
    json_filename = f"agri_data_{crop_code}.json"
    
    # 2. 檢查本地快取
    if not force_update and os.path.exists(json_filename):
        print(f"[{crop_name}] 發現本地快取 '{json_filename}'，直接讀取...")
        try:
            with open(json_filename, 'r', encoding='utf-8') as f:
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
        
        # 4. 存檔 (自動對應檔名)
        if "Data" in data and len(data["Data"]) > 0:
            print(f"[{crop_name}] 下載成功！存檔至 '{json_filename}'")
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            
            return process_agri_json(data)
        else:
            print(f"[{crop_name}] API 回傳無資料 (可能代碼錯誤或休市)")
            return pd.Series()
            
    except Exception as e:
        print(f"[{crop_name}] API 請求失敗: {e}")
        return pd.Series()

def process_agri_json(data):
    # (這個函式跟上一個版本一樣，負責轉 DataFrame，這邊省略不重複貼)
    # ... (請保留上一個版本的 process_agri_json) ...
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
        return clean_df['Price']
    return pd.Series()

# --- 實戰：如何一次抓多個作物 ---
if __name__ == "__main__":
    
    # 定義你想抓的清單
    target_crops = [
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
    
    dataset = {}
    
    for crop in target_crops:
        # 迴圈呼叫，自動存成不同檔案
        series = get_moa_agri_data(
            crop_code=crop["code"], 
            crop_name=crop["name"],
            days=365
        )
        dataset[crop["name"]] = series
        
    # 轉成 DataFrame 一次看
    full_df = pd.DataFrame(dataset)
    print("\n=== 抓取結果預覽 ===")
    print(full_df.tail())
