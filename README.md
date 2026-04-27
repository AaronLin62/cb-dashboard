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

🌟 核心技術與實戰亮點 (Key Features)
1. 動態均價鎖定與資料無損清洗 (Edge Case Handling)
突破傳統爬蟲僅抓取「收市價」的盲點。針對市場上常見的「零成交」流動性陷阱標的，系統具備動態尋標邏輯，自動切換抓取「均價」或「參考價」，確保特殊標的 100% 無損入庫，不漏接任何隱藏套利機會。

2. 反稀釋防禦機制 (Anti-dilution Mechanism)
台股除權息旺季常導致可轉債轉換價依比例調降。本系統內建 BeautifulSoup4 爬蟲，主動追蹤公開資訊觀測站的調整公告，自動更新資料庫中的轉換價，徹底拆除「假套利、真虧損」的報價地雷。

3. 真實交易摩擦成本精算引擎
捨棄無效的表面「帳面溢價」。演算法內建真實交易模型，動態扣除：

券商買進/賣出實體手續費 (支援自訂 VIP 折讓參數，如 6 折或更低)

0.3% 法定證券交易稅
確保戰情室雷達篩選出的名單，皆為「扣除摩擦成本後，淨利潤仍大於零」的黃金標的。

4. AI 趨勢預測模型 (OLS Trend Prediction)
無縫串接歷史資料庫，使用 NumPy 最小平方法 (Ordinary Least Squares) 對個股歷史價格軌跡進行線性回歸，並結合 Altair 繪製未來 5 日的 AI 預測曲線，輔助進出場之趨勢判斷。

5. 雲端無人化生產線與主動警報 (CI/CD & Webhook)
完全脫離本機端依賴。透過 GitHub Actions 設定 Cron Job 每日下午定時觸發爬蟲管線，並將執行結果與套利名單透過 Webhook 封裝成精美的卡片式訊息，主動推播至專屬 Discord 頻道，實現 24 小時無人值守。

💻 安裝與運行指南 (Installation)
Clone 專案與安裝環境

Bash
git clone [https://github.com/yourusername/CB-Quant-V8.git](https://github.com/yourusername/CB-Quant-V8.git)
cd CB-Quant-V8
pip install -r requirements.txt
設定環境變數 (.streamlit/secrets.toml)

Ini, TOML
SUPABASE_URL = "您的 Supabase 網址"
SUPABASE_KEY = "您的 Service Role Key"
啟動戰情室

Bash
streamlit run app.py
⚠️ 免責聲明 (Disclaimer)
本專案為學術研究與程式開發實作，系統產出之預測線與套利空間僅供參考。金融市場具備高度風險，本系統不構成任何投資建議。使用者應自行評估交易風險，對於任何因使用本系統而產生之財務損失，開發者概不負責。
[Discord 警報]   [Streamlit 戰情室 (app.py)]
(推播黃金標的)     (AI 預測 / 視覺化儀表板 / 參數微調)
