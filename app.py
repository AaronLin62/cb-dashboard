import streamlit as st
from supabase import create_client, Client
import pandas as pd
import yfinance as yf
import numpy as np
import datetime
import altair as alt

# ==========================================
# 1. 核心設定與資料庫連線
# ==========================================
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

@st.cache_resource
def init_connection():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_connection()

# --- 新增：精確成本計算邏輯 ---
def get_net_result(bond_price, stock_price, conv_price, discount_rate):
    """
    計算套利總成本與扣稅後的淨獲利率
    """
    # 1. 理論價值
    conversion_value = (100 / conv_price) * stock_price
    
    # 2. 交易成本 (假設操作金額為 10 萬元)
    base_amount = 100000 
    fee_rate = 0.001425 # 券商公定手續費
    
    # 買進可轉債成本 (最低 20 元)
    buy_fee = max(20, base_amount * fee_rate * discount_rate)
    
    # 賣出轉換後股票成本 (手續費 + 0.3% 證交稅)
    sell_fee = max(20, base_amount * fee_rate * discount_rate)
    sell_tax = base_amount * 0.003
    
    total_cost_ratio = (buy_fee + sell_fee + sell_tax) / base_amount * 100
    
    # 3. 原始溢價率 (Gross)
    gross_premium = ((bond_price - conversion_value) / conversion_value) * 100
    
    # 4. 淨溢價率 (Net) -> 負值越大代表套利淨賺越多
    net_premium = gross_premium + total_cost_ratio
    
    return conversion_value, gross_premium, net_premium, total_cost_ratio

@st.cache_data(ttl=600)
def load_all_data():
    cb_response = supabase.table('convertible_bonds').select("*").execute()
    df_cb = pd.DataFrame(cb_response.data)
    if not df_cb.empty:
        df_cb['current_price'] = pd.to_numeric(df_cb['current_price'], errors='coerce')
        df_cb = df_cb.dropna(subset=['current_price'])
    mapping_response = supabase.table('bond_stock_mapping').select("*").execute()
    df_mapping = pd.DataFrame(mapping_response.data)
    return df_cb, df_mapping

# ==========================================
# 2. 網頁介面設計
# ==========================================
st.set_page_config(page_title="可轉債戰情儀表板 V7", page_icon="📈", layout="wide")
st.title("📈 企業級可轉債戰情室 - 策略優化與成本核算版")

# --- 側邊欄：交易參數設定 ---
st.sidebar.header("⚙️ 交易策略設定")
broker_discount = st.sidebar.slider("券商手續費折讓 (例如: 6折選0.6)", 0.1, 1.0, 0.6, 0.05)
st.sidebar.info(f"💡 目前設定：賣出證交稅 0.3% + 手續費折讓 {broker_discount} 折")

df_cb, df_mapping = load_all_data()

if df_cb.empty or df_mapping.empty:
    st.warning("⚠️ 資料庫初始化中...")
else:
    st.subheader("🎯 負溢價套利雷達 (精確成本核算)")
    
    valid_bonds = df_cb[df_cb['bond_code'].isin(df_mapping['bond_code'])]
    bond_options = valid_bonds['bond_code'] + " - " + valid_bonds['bond_name']
    selected_option = st.selectbox("請選擇分析標的：", bond_options)
    
    if selected_option:
        selected_code = selected_option.split(" - ")[0]
        mapping_info = df_mapping[df_mapping['bond_code'] == selected_code].iloc[0]
        target_stock = mapping_info['stock_code']
        conv_price = mapping_info['conversion_price']
        bond_price = valid_bonds[valid_bonds['bond_code'] == selected_code]['current_price'].values[0]
        
        yf_ticker = target_stock if ".TW" in target_stock or ".TWO" in target_stock else f"{target_stock}.TW"
        
        with st.spinner('📡 正在計算精確套利獲利...'):
            try:
                ticker = yf.Ticker(yf_ticker)
                stock_price = ticker.history(period="1d")['Close'].iloc[-1]
                
                # 調用成本計算函式
                conv_val, gross_p, net_p, cost_r = get_net_result(bond_price, stock_price, conv_price, broker_discount)
                
                # 渲染視覺化指標
                c1, c2, c3 = st.columns(3)
                c1.metric("可轉債市價", f"{bond_price:.2f}")
                c2.metric(f"股票 {target_stock} 市價", f"{stock_price:.2f}")
                c3.metric("估計交易總成本 (%)", f"{cost_r:.3f}%")
                
                # --- 套利診斷報告 ---
                st.markdown("### 📊 套利診斷報告")
                res_col1, res_col2 = st.columns(2)
                
                with res_col1:
                    st.write(f"原始溢價率 (Gross): **{gross_p:.2f}%**")
                    if gross_p < 0:
                        st.success("✅ 表面上有套利空間")
                    else:
                        st.write("❌ 表面無套利空間")
                
                with res_col2:
                    st.write(f"扣費後淨溢價 (Net): **{net_p:.2f}%**")
                    if net_p < 0:
                        st.error(f"🔥 扣除成本後仍具套利價值！淨利預估 {abs(net_p):.2f}%")
                    else:
                        st.warning("⚠️ 成本過高或空間不足，扣費後將會虧損！")

                st.markdown("---")
                
                # --- 模組 B：AI 趨勢預測 (維持上一版的優化) ---
                st.subheader("🤖 AI 歷史回測與未來 5 日預測")
                hist_response = supabase.table('bond_price_history').select("*").eq('bond_code', selected_code).order('record_date').execute()
                df_hist = pd.DataFrame(hist_response.data)

                if len(df_hist) < 3:
                    st.warning("⚠️ 歷史資料累積不足 3 天，無法繪製趨勢。")
                else:
                    df_hist['record_date'] = pd.to_datetime(df_hist['record_date']).dt.date
                    df_hist['close_price'] = pd.to_numeric(df_hist['close_price'], errors='coerce')
                    x_days = np.arange(len(df_hist))
                    y_prices = df_hist['close_price'].values
                    coefficients = np.polyfit(x_days, y_prices, 1)
                    poly_func = np.poly1d(coefficients)
                    future_x = np.arange(len(df_hist), len(df_hist) + 5)
                    future_y = poly_func(future_x)
                    future_dates = [df_hist['record_date'].iloc[-1] + datetime.timedelta(days=int(i)) for i in range(1, 6)]
                    
                    chart_data = pd.DataFrame({
                        "日期": list(df_hist['record_date']) + future_dates,
                        "實際歷史價格": list(y_prices) + [None]*5,
                        "AI 趨勢預測線": [None] * (len(df_hist)-1) + [y_prices[-1]] + list(future_y)
                    }).set_index("日期")
                    
                    df_melted = chart_data.reset_index().melt(id_vars=['日期'], var_name='線條種類', value_name='價格')
                    chart = alt.Chart(df_melted).mark_line(point=True).encode(
                        x=alt.X('日期:T', title='日期'),
                        y=alt.Y('價格:Q', scale=alt.Scale(zero=False), title='價格'),
                        color=alt.Color('線條種類:N', scale=alt.Scale(domain=['實際歷史價格', 'AI 趨勢預測線'], range=['#1f77b4', '#ff7f0e']))
                    ).interactive()
                    st.altair_chart(chart, use_container_width=True)

            except Exception as e:
                st.error(f"運算過程發生錯誤：{e}")
