# cb-dashboard
# 🚨 CB-Quant-V8 全自動可轉債套利戰情室

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Supabase](https://img.shields.io/badge/Database-Supabase-green.svg)
![Streamlit](https://img.shields.io/badge/UI-Streamlit-red.svg)
![GitHub Actions](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-2088FF.svg)

> **企業級全自動量化交易系統**：結合數據無損清洗、雲端自動化、精確成本核算與 AI 趨勢預測的台股可轉債套利雷達。

## 📊 系統架構 (Data Pipeline)

```text
[公開資訊觀測站] & [櫃買中心 CSV]
        │ (Daily Schedule: 16:30)
        ▼
[GitHub Actions 雲端伺服器 (auto_pipeline.py)]
  ├─ 1. 反稀釋爬蟲 (BeautifulSoup4 解析除權息公告)
  ├─ 2. 動態均價鎖定 (破解「收市留白」與「零成交」陷阱)
  └─ 3. 交易摩擦成本核算 (動態扣除手續費折讓、0.3% 證交稅)
        │
        ▼
[Supabase (PostgreSQL 關聯式資料庫)]
  ├─ convertible_bonds (最新報價與狀態)
  └─ bond_price_history (時序歷史資料)
        │
  ┌─────┴─────┐
  ▼           ▼
[Discord 警報]   [Streamlit 戰情室 (app.py)]
(推播黃金標的)     (AI 預測 / 視覺化儀表板 / 參數微調)
