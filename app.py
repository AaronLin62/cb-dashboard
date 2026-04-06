import streamlit as st
from supabase import create_client, Client
import pandas as pd
import yfinance as yf
import numpy as np
import datetime

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
    # 讀取最新市價與對照表
    cb_response = supabase.table('convertible_bonds').select("*").execute()
    df_cb = pd.DataFrame(cb_response.data)
    if not df_cb.empty:
        df_cb['current_price'] = pd.to_numeric(df_cb['current_price'], errors='coerce')
        df_cb = df_cb.dropna(subset=['current_price'])
        
    mapping_response = supabase.table('bond_stock_mapping').select("*").execute()
    df_mapping = pd.DataFrame(mapping_response.data)
    
    return df_cb, df_mapping

# ==========================================
# 2. 網頁介面設計與核心邏輯
# ==========================================
st.set_page_config(page_title="可轉債戰情儀表板", page_icon="📈", layout="wide")
st.title("📈 企業級可轉債戰情室 - V6 終極版")
st.markdown("---")

df_cb, df_mapping = load_all_data()

if df_cb.empty or df_mapping.empty:
    st.warning("⚠️ 系統正在等待資料庫初始化...")
else:
    st.subheader("🔥 負溢價套利雷達 & AI 趨勢預測")
    
    valid_bonds = df_cb[df_cb['bond_code'].isin(df_mapping['bond_code'])]
    bond_options = valid_bonds['bond_code'] + " - " + valid_bonds['bond_name']
    
    selected_option = st.selectbox("🎯 請選擇要進行分析的標的：", bond_options)
    
    if selected_option:
        selected_code = selected_option.split(" - ")[0]
        
        # --- 模組 A：即時套利雷達 ---
        mapping_info = df_mapping[df_mapping['bond_code'] == selected_code].iloc[0]
        target_stock = mapping_info['stock_code']
        conv_price = mapping_info['conversion_price']
        bond_price = valid_bonds[valid_bonds['bond_code'] == selected_code]['current_price'].values[0]
        
        yf_ticker = target_stock if ".TW" in target_stock or ".TWO" in target_stock else f"{target_stock}.TW"
        
        with st.spinner('📡 正在運算套利空間與 AI 趨勢預測...'):
            try:
                # 取得股價與計算溢價
                ticker = yf.Ticker(yf_ticker)
                stock_price = ticker.history(period="1d")['Close'].iloc[-1]
                conversion_value = (100 / conv_price) * stock_price
                premium_rate = ((bond_price - conversion_value) / conversion_value) * 100
                
                col1, col2, col3 = st.columns(3)
                col1.metric("可轉債最新市價", f"{bond_price:.2f} 元")
                col2.metric(f"對應股票 ({target_stock}) 即時市價", f"{stock_price:.2f} 元")
                col3.metric("資料庫合約轉換價", f"{conv_price:.2f} 元")
                
                if premium_rate < 0:
                    st.success(f"🔥 發現潛在套利空間！目前折價 **{premium_rate:.2f}%**")
                else:
                    st.info(f"⚖️ 目前為溢價狀態：**{premium_rate:.2f}%** (無套利空間)")

                st.markdown("---")
                
                # --- 模組 B：AI 歷史回測與未來 5 日預測 ---
                st.subheader("🤖 AI 歷史回測與未來 5 日價格預測 (NumPy 最小平方法)")
                
                # 從金庫調閱這檔債券的歷史軌跡
                hist_response = supabase.table('bond_price_history').select("*").eq('bond_code', selected_code).order('record_date').execute()
                df_hist = pd.DataFrame(hist_response.data)

                if len(df_hist) < 3:
                    st.warning("⚠️ 歷史資料累積不足 3 天，模型尚無法繪製準確的趨勢線。請等待每日流水線累積更多數據！")
                else:
                    df_hist['record_date'] = pd.to_datetime(df_hist['record_date']).dt.date
                    df_hist['current_price'] = pd.to_numeric(df_hist['current_price'], errors='coerce')
                    
                    # 準備線性迴歸模型資料
                    x_days = np.arange(len(df_hist))
                    y_prices = df_hist['price'].values
                    
                    # 執行一元一次方程式線性迴歸 (y = mx + b)
                    coefficients = np.polyfit(x_days, y_prices, 1)
                    poly_func = np.poly1d(coefficients)
                    
                    # 預測未來 5 天
                    future_x = np.arange(len(df_hist), len(df_hist) + 5)
                    future_y = poly_func(future_x)
                    
                    last_date = df_hist['record_date'].iloc[-1]
                    future_dates = [last_date + datetime.timedelta(days=int(i)) for i in range(1, 6)]
                    
                    # 整合資料以供 Streamlit 畫圖
                    chart_data = pd.DataFrame({
                        "日期": list(df_hist['record_date']) + future_dates,
                        "實際歷史價格": list(y_prices) + [None]*5,
                        "AI 趨勢預測線": list(poly_func(x_days)) + list(future_y)
                    }).set_index("日期")
                    
                    # 繪製精美走勢圖
                    st.line_chart(chart_data, color=["#1f77b4", "#ff7f0e"])
                    
                    st.write(f"📈 **AI 模型解讀：** 根據歷史走勢，預期未來 5 日價格將趨向 **{future_y[-1]:.2f} 元**。斜率狀態：{'向上 ↗' if coefficients[0] > 0 else '向下 ↘'}")

            except Exception as e:
                st.error(f"運算過程發生錯誤：{e}")
