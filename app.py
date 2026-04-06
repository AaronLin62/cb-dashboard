import streamlit as st
from supabase import create_client, Client
import pandas as pd
import yfinance as yf

# ==========================================
# 1. 資料庫連線設定
# ==========================================
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

@st.cache_resource
def init_connection():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_connection()

@st.cache_data(ttl=600)
def load_all_data():
    # 讀取最新可轉債市價
    cb_response = supabase.table('convertible_bonds').select("*").execute()
    df_cb = pd.DataFrame(cb_response.data)
    if not df_cb.empty:
        df_cb['current_price'] = pd.to_numeric(df_cb['current_price'], errors='coerce')
        df_cb = df_cb.dropna(subset=['current_price'])
        
    # 讀取全市場轉換價對照表
    mapping_response = supabase.table('bond_stock_mapping').select("*").execute()
    df_mapping = pd.DataFrame(mapping_response.data)
    
    return df_cb, df_mapping

# ==========================================
# 2. 網頁介面設計與核心邏輯
# ==========================================
st.set_page_config(page_title="可轉債戰情儀表板", page_icon="📈", layout="wide")
st.title("📈 企業級可轉債戰情室 - 全市場雷達版")
st.markdown("---")

df_cb, df_mapping = load_all_data()

if df_cb.empty or df_mapping.empty:
    st.warning("⚠️ 系統正在等待資料庫初始化，請確認市價或對照表已匯入。")
else:
    st.subheader("🔥 負溢價套利雷達 (全市場動態連線)")
    
    # 將兩張表進行交集比對 (只顯示既有報價又有轉換價的標的)
    valid_bonds = df_cb[df_cb['bond_code'].isin(df_mapping['bond_code'])]
    bond_options = valid_bonds['bond_code'] + " - " + valid_bonds['bond_name']
    
    selected_option = st.selectbox("🎯 請選擇要進行套利分析的標的：", bond_options)
    
    if selected_option:
        selected_code = selected_option.split(" - ")[0]
        
        # 動態從資料庫對照表中提取參數
        mapping_info = df_mapping[df_mapping['bond_code'] == selected_code].iloc[0]
        target_stock = mapping_info['stock_code']
        conv_price = mapping_info['conversion_price']
        bond_price = valid_bonds[valid_bonds['bond_code'] == selected_code]['current_price'].values[0]
        
        # 處理 yfinance 台股代碼後綴邏輯 (上市 .TW / 上櫃 .TWO)
        yf_ticker = target_stock if ".TW" in target_stock or ".TWO" in target_stock else f"{target_stock}.TW"
        
        with st.spinner(f'📡 正在透過 yfinance 連線取得 {target_stock} 即時股價...'):
            try:
                ticker = yf.Ticker(yf_ticker)
                # 抓取最近一天的收盤價
                stock_price = ticker.history(period="1d")['Close'].iloc[-1]
                
                # --- 執行套利演算法數學公式 ---
                conversion_value = (100 / conv_price) * stock_price
                premium_rate = ((bond_price - conversion_value) / conversion_value) * 100
                
                # --- 渲染視覺化戰情看板 ---
                col1, col2, col3 = st.columns(3)
                col1.metric("可轉債最新市價", f"{bond_price:.2f} 元")
                col2.metric(f"對應股票 ({target_stock}) 即時市價", f"{stock_price:.2f} 元")
                col3.metric("資料庫合約轉換價", f"{conv_price:.2f} 元")
                
                st.markdown("### 📊 套利分析結果")
                
                if premium_rate < 0:
                    st.success(f"🔥 發現潛在套利空間！目前折價 **{premium_rate:.2f}%**")
                    st.write(f"💡 解讀：理論價值為 {conversion_value:.2f} 元，市場僅售 {bond_price:.2f} 元，存在低估套利空間！")
                else:
                    st.info(f"⚖️ 目前為溢價狀態：**{premium_rate:.2f}%** (無套利空間)")
                    st.write(f"💡 解讀：理論價值為 {conversion_value:.2f} 元，市場售價 {bond_price:.2f} 元，價格合理包含保本價值。")
                    
            except Exception as e:
                st.error(f"連線 yfinance 或計算過程發生錯誤：{e}")
                st.write("🔧 提示：若股票代碼抓取不到，可能是上櫃股票需後綴 `.TWO`，可於對照表中修正。")

    st.markdown("---")
    st.subheader("📊 全市場市價總覽")
    st.dataframe(df_cb[['bond_code', 'bond_name', 'current_price']], use_container_width=True)
