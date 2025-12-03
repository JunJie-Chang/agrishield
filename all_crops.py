import requests
import pandas as pd
import json
import os
import urllib3
from datetime import datetime, timedelta

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# API 基礎 URL
base_url = "https://data.moa.gov.tw/api/v1/AgriProductsTransType/?Start_time=107.07.01&End_time=107.07.10&MarketName=%E5%8F%B0%E5%8C%97%E4%B8%80"

# 從 API 取得資料
response = requests.get(base_url, verify=False)
data = response.json()

# 提取並轉換資料
if data.get("RS") == "OK":
    crop_dict = {}
    
    # 遍歷所有資料項目
    for item in data.get("Data", []):
        crop_code = item.get("CropCode")
        crop_name = item.get("CropName")
        
        # 去重：使用 dict 確保每個 code 只出現一次
        if crop_code and crop_name:
            crop_dict[crop_code] = crop_name
    
    # 轉換成目標格式
    result = [
        {"code": code, "name": name} 
        for code, name in crop_dict.items()
    ]
    
    # 輸出結果
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    # 或存成檔案
    with open("crops.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
else:
    print("API 回應錯誤")
