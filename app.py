import streamlit as st
from supabase import create_client, Client
import pandas as pd
import yfinance as yf
import numpy as np
import datetime
import altair as alt

# ==========================================
# 1. 核心設定與專業 UI 風格注入
# ==========================================
st.set_page_config(
    page_title="量化套利戰情室 V8", 
    page_icon="🚨", 
    layout="wide", # 寬螢幕模式
    initial_sidebar_state="collapsed"
)

# 注入 CSS 打造深色發光儀表板
st.markdown("""
    <style>
    [data-testid="stMetric"] {
        background-color: #1e1e1e;
        border-left: 5px solid #00ff00;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.5);
    }
    [data-testid="stMetricLabel"] { color: #aaaaaa !important; }
    [data-testid="stMetricValue"] { color: #00ff00 !important; }
    .stAlert { border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 資料庫連線與精確成本核算引擎
# ==========================================
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

@st.cache_resource
def init_connection():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_connection()

def get_net_result(bond_price, stock_price, conv_price, discount_rate):
    """計算套利總成本與扣稅後的淨獲利率"""
    conversion_value = (100 / conv_price) * stock_price
    base_amount = 100000 
    fee_rate = 0.001425 
    buy_fee = max(20, base_amount * fee_rate * discount_rate)
    sell_fee = max(20, base_amount * fee_rate * discount_rate)
    sell_tax = base_amount * 0.003
    total_cost_ratio = (buy_fee + sell_fee + sell_tax) / base_amount * 100
    gross_premium = ((bond_price - conversion_value) / conversion_value) * 100
    net_premium = gross_premium + total_cost_ratio
    return conversion_value, gross_premium, net_premium, total_cost_ratio

@st.cache_data(ttl=3600)
def load_data():
    # ⭐️ 核心修正：只撈取活躍中的標的 (過濾下市債券)
    response = supabase.table('convertible_bonds').select("*").eq('is_active', True).execute()
    return pd.DataFrame(response.data)

# ==========================================
# 3. 戰情室主畫面
# ==========================================
st.title("🚨 全自動可轉債套利戰情室")
st.caption(f"數據更新時間: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")

df = load_data()

with st.sidebar:
    st.header("⚙️ 參數設定")
    broker_discount = st.slider("券商手續費折讓 (例如 6 折)", 0.1, 1.0, 0.6)
    
if df.empty:
    st.warning("目前資料庫中無活躍標的，請確認爬蟲是否正常執行。")
else:
    # --- 啟動全市場雷達掃描 ---
    if st.button("🚀 啟動全市場套利機會掃描"):
        golden_list = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for index, row in df.iterrows():
            bond_code = row['bond_code']
            bond_price = row['current_price']
            
            # 更新進度
            progress = (index + 1) / len(df)
            progress_bar.progress(progress)
            status_text.text(f"📡 正在分析: {bond_code} {row['bond_name']}...")
            
            # 撈取轉換價
            mapping = supabase.table('bond_stock_mapping').select("*").eq('bond_code', bond_code).execute()
            
            if mapping.data:
                m_data = mapping.data[0]
                stock_symbol = m_data['stock_code'] + ".TW"
                conv_price = m_data['conversion_price']
                
                try:
                    stock_data = yf.Ticker(stock_symbol).history(period="1d")
                    if not stock_data.empty:
                        stock_price = stock_data['Close'].iloc[-1]
                        # 核心計算
                        conv_val, gross_p, net_p, cost_r = get_net_result(bond_price, stock_price, conv_price, broker_discount)
                        
                        # 只抓淨利潤大於 0 的黃金標的
                        if net_p < 0:
                            golden_list.append({
                                "可轉債代碼": bond_code,
                                "名稱": row['bond_name'],
                                "債券市價": round(bond_price, 2),
                                "股票現價": round(stock_price, 2),
                                "轉換價": round(conv_price, 2),
                                "🎯 預估淨利": f"{abs(net_p):.2f}%"
                            })
                except:
                    pass
        
        status_text.text("✅ 掃描完成！")
        
        # ==========================================
        # 4. 企業級儀表板與結果顯示
        # ==========================================
        if golden_list:
            df_golden = pd.DataFrame(golden_list)
            
            # 頂部三大指標
            st.markdown("### 📊 今日戰情報告")
            m1, m2, m3 = st.columns(3)
            m1.metric("📡 雷達掃描標的", f"{len(df)} 檔")
            m2.metric("🎯 發現黃金機會", f"{len(df_golden)} 檔", delta="可進場")
            
            # 處理最高淨利顯示
            max_profit = df_golden['🎯 預估淨利'].str.replace('%','').astype(float).max()
            m3.metric("🔥 最高預估淨利", f"{max_profit:.2f} %")
            
            st.markdown("---")
            st.success(f"🎉 發現 {len(df_golden)} 檔具有正報酬空間的標的！")
            st.dataframe(df_golden.sort_values(by="🎯 預估淨利", ascending=False), use_container_width=True)
        else:
            st.info("今日市場波動平穩，暫無符合成本效益之套利機會。")

# ==========================================
# 5. AI 趨勢預測區塊 (保留原本預測邏輯)
# ==========================================
st.markdown("---")
st.subheader("🔮 個別標的 AI 趨勢預測")
target_bond = st.selectbox("請選擇要分析的標的代碼", df['bond_code'].unique() if not df.empty else [])

if target_bond:
    hist_response = supabase.table('bond_price_history').select("*").eq('bond_code', target_bond).order('record_date').execute()
    if hist_response.data:
        df_hist = pd.DataFrame(hist_response.data)
        df_hist['record_date'] = pd.to_datetime(df_hist['record_date'])
        
        if len(df_hist) > 5:
            # NumPy OLS 預測邏輯
            x_days = np.arange(len(df_hist))
            y_prices = df_hist['close_price'].values
            coefficients = np.polyfit(x_days, y_prices, 1)
            poly_func = np.poly1d(coefficients)
            
            future_x = np.arange(len(df_hist), len(df_hist) + 5)
            future_y = poly_func(future_x)
            future_dates = [df_hist['record_date'].iloc[-1] + datetime.timedelta(days=i) for i in range(1, 6)]
            
            chart_data = pd.DataFrame({
                "日期": list(df_hist['record_date']) + future_dates,
                "實際歷史價格": list(y_prices) + [None]*5,
                "AI 趨勢預測線": [None] * (len(df_hist)-1) + [y_prices[-1]] + list(future_y)
            }).set_index("日期")
            
            df_melted = chart_data.reset_index().melt(id_vars=['日期'], var_name='線條種類', value_name='價格')
            chart = alt.Chart(df_melted).mark_line(point=True).encode(
                x=alt.X('日期:T', title='日期'),
                y=alt.Y('價格:Q', scale=alt.Scale(zero=False), title='價格'),
                color=alt.Color('線條種類:N', legend=alt.Legend(title="圖例")),
                tooltip=['日期', '價格', '線條種類']
            ).properties(height=400).interactive()
            
            st.altair_chart(chart, use_container_width=True)
            st.caption("💡 註：預測線基於最小平方法線性回歸，僅供趨勢參考，不構成投資建議。")
