import json
import pandas as pd
from datetime import datetime

# 引入我們拆分好的模組
import agridata
import agrishield

def main():
    # === A. 讀取作物清單 ===
    json_path = "target_crops.json"
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            target_crops = json.load(f)
        print(f"成功讀取 {len(target_crops)} 個目標作物。")
    except FileNotFoundError:
        print(f"錯誤：找不到 {json_path}，請確認檔案是否存在。")
        return

    # === B. 抓取所有農產品資料 ===
    agri_dataset = {}
    min_date = datetime.now()

    print("\n=== Step 1: 啟動農產品數據下載引擎 (agridata) ===")
    for crop in target_crops:
        # 使用 agridata 模組中的函數
        series = agridata.get_moa_agri_data(crop["code"], crop["name"], days=365*2)
        
        if not series.empty:
            agri_dataset[crop["name"]] = series
            # 記錄最早日期，為了抓金融數據用
            if series.index.min() < min_date:
                min_date = series.index.min()
    
    if not agri_dataset:
        print("錯誤：沒有抓到任何農產品資料，程式終止。")
        return

    # === C. 抓取金融資料 ===
    print("\n=== Step 2: 下載全球金融數據 (agrishield) ===")
    start_str = min_date.strftime('%Y-%m-%d')
    end_str = datetime.now().strftime('%Y-%m-%d')
    
    # 使用 agrishield 模組中的函數
    finance_df = agrishield.get_financial_universe(start_str, end_str)
    
    if finance_df.empty:
        print("錯誤：金融數據下載失敗。")
        return

    # === D. 執行掃描與產出報告 ===
    print("\n=== Step 3: 執行 Macro-Agri 相關性掃描 ===")
    all_reports = []

    for crop_name, series in agri_dataset.items():
        print(f"正在分析: {crop_name}...")
        # 使用 agrishield 模組中的函數
        report = agrishield.run_scanner(series, finance_df, crop_name)
        
        if not report.empty:
            all_reports.append(report)
            top = report.iloc[0]
            print(f" -> 發現最佳指標: {top['Asset']} (Corr: {top['Best_Correlation']}, {top['Timing']})")

    # === E. 總結報告存檔 ===
    if all_reports:
        final_df = pd.concat(all_reports, ignore_index=True)
        
        # 產生時間戳記，格式範例: 20251201_2315 (年月日_時分)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        output_filename = f"Full_report/AgriShield_Full_Report_{timestamp}.csv"
        
        # 存 CSV
        final_df.to_csv(output_filename, index=False)
        
        print("\n" + "="*60)
        print("【AgriShield 完整分析完成】")
        print(f"報告已儲存至: {output_filename}")
        print("="*60)
        print(final_df.head(10).to_string(index=False))
    else:
        print("沒有產生任何有效報告。")


if __name__ == "__main__":
    main()
