# AgriShield: 農業金融相關性掃描系統

**AgriShield** 是一個自動化的量化分析工具，專門用於探索「台灣農產品價格」與「全球宏觀金融指標」之間的統計相關性。

本專案整合了 **台灣農業部開放資料 (MOA)** 與 **Yahoo Finance** 金融數據，透過滑動視窗與滯後分析 (Lag Analysis)，自動尋找影響農產品價格的潛在先行指標（如原油、天然氣、美元匯率等）。

## 🚀 核心功能

- **自動化數據抓取**
  - **農產品端**：直接對接台灣農業部 API，抓取指定作物在「台北一」市場的批發交易價格，並支援本地 JSON 快取以減少請求次數。
  - **金融端**：自動下載全球關鍵資產數據，包括原油 (CL=F)、天然氣 (NG=F)、農業 ETF (MOO)、黃金 (GLD)、美元兌台幣 (TWD=X) 等。

- **Macro-Agri 掃描引擎**
  - **多維度相關性分析**：計算同步 (T=0)、領先一週 (T-1w) 及領先一個月 (T-1m) 的相關係數。
  - **智慧清洗**：自動處理台股/美股休市日不同步的問題，並透過 Forward Fill 補齊數據。

- **分析報告產出**
  - 自動生成 CSV 綜合報告，列出每項作物與其「最強相關」的金融資產及領先時間，作為避險或投資決策參考。

## 📂 檔案結構

- `main.py`: 主程式入口。負責協調數據流、執行掃描並輸出最終報告。
- `agridata.py`: **資料層 (Data Layer)**。負責處理農業部 API 請求、民國年/西元年轉換及數據清洗。
- `agrishield.py`: **核心層 (Core Layer)**。負責抓取 Yahoo Finance 數據及執行相關性運算邏輯。
- `target_crops.json`: (需自行建立) 設定檔，定義要分析的作物清單。
- `merged/`: 存放暫存的中間過程數據 (Merged CSV)。
- `Full_report/`: 存放最終產出的分析報告。

## 🛠️ 安裝與設定

### 1. 安裝依賴套件
請確保已安裝 Python 3.8+，並執行以下指令安裝所需套件：
pip install pandas numpy yfinance requests


### 2. 建立作物設定檔
在專案根目錄下建立 `target_crops.json`，填入你想分析的作物代碼 (可至農業部查詢)：

[
{ "code": "LA1", "name": "甘藍" },
{ "code": "SG2", "name": "大蒜" },
{ "code": "FI2", "name": "茄子" }
]

## 🏃 使用方式

1. 確保 `target_crops.json` 已建立。
2. 建立存放報告的資料夾：
mkdir Full_report
mkdir merged
3. 執行主程式：
python main.py

4. 程式執行完畢後，請至 `Full_report/` 資料夾查看帶有時間戳記的 CSV 報告 (例如 `AgriShield_Full_Report_20251203_1000.csv`)。

## 📊 分析指標說明

系統目前內建掃描以下金融資產：
- **能源成本**：原油 (CL=F)
- **肥料成本**：天然氣 (NG=F)
- **匯率影響**：美元/台幣 (TWD=X)
- **市場情緒**：台股加權指數 (^TWII)、美股農業 ETF (MOO)
- **避險資產**：黃金 (GLD)

---
*Created by JunJie-Chang*
