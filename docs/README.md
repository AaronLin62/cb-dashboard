# cb-dashboard
# 🚨 CB-Quant-V8 全自動可轉債套利戰情室

**作者：[資工系/113502537/林俊綸]**

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Supabase](https://img.shields.io/badge/Database-Supabase-green.svg)
![Streamlit](https://img.shields.io/badge/UI-Streamlit-red.svg)
![GitHub Actions](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-2088FF.svg)

> **企業級全自動量化交易系統**：結合數據無損清洗、雲端自動化、精確成本核算與 AI 趨勢預測的台股可轉債套利雷達。

## 📊 系統架構 (Data Pipeline)
* **自動化數據採集：** 透過 GitHub Actions 定時執行 Python 爬蟲。
* **資料清洗與存儲：** 破解收市留白陷阱，將乾淨數據 Upsert 至 Supabase 關聯式資料庫。
* **前端視覺化：** 使用 Streamlit 打造雙模式戰情室 (單檔狙擊 / 全網雷達)。

## 🌟 核心技術亮點
1. **交易摩擦成本精算引擎：** 演算法內建真實交易模型，動態扣除券商買賣手續費與 0.3% 證交稅，確保淨利潤真實有效。
2. **AI 趨勢預測模型 (OLS)：** 串接歷史資料庫，使用 `NumPy` 最小平方法對價格軌跡進行線性回歸預測。
3. **無損清洗與防禦機制：** 動態均價鎖定技術，破解「零成交」流動性陷阱標的。

## 💻 本機端運行指南
```bash
git clone [https://github.com/yourusername/cb-dashboard.git](https://github.com/yourusername/cb-dashboard.git)
cd cb-dashboard
pip install -r requirements.txt
streamlit run app.py
