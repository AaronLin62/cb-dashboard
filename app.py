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
st.set_page_config(page_title="可轉債戰情儀表板 V8", page_icon="📈", layout="wide")
st.title("📈 企業級可轉債戰情室 - V8 智能掃描版")

# --- 側邊欄：交易參數設定 ---
st.sidebar.header("⚙️ 交易帳戶設定")
broker_discount = st.sidebar.slider("券商手續費折讓", 0.1, 1.0, 0.6, 0.05)
st.sidebar.info(f"💡 目前設定：賣出證交稅 0.3% + 手續費 {broker_discount} 折")

df_cb, df_mapping = load_all_data()

if df_cb.empty or df_mapping.empty:
    st.warning("⚠️ 資料庫初始化中...")
else:
    # 建立頁籤 (Tabs) 讓介面更乾淨專業
    tab1, tab2 = st.tabs(["🎯 單檔深度分析 (狙擊模式)", "🌐 全市場套利掃描 (雷達模式)"])
    
    valid_bonds = df_cb[df_cb['bond_code'].isin(df_mapping['bond_code'])]
    
    # ==========================================
    # 頁籤 1：單檔深度分析 (保留原本強大的 AI 預測)
    # ==========================================
    with tab1:
        bond_options = valid_bonds['bond_code'] + " - " + valid_bonds['bond_name']
        selected_option = st.selectbox("🔍 請選擇要深度分析的標的：", bond_options)
        
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
                    conv_val, gross_p, net_p, cost_r = get_net_result(bond_price, stock_price, conv_price, broker_discount)
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric("可轉債市價", f"{bond_price:.2f}")
                    c2.metric(f"股票 ({target_stock})", f"{stock_price:.2f}")
                    c3.metric("總摩擦成本", f"{cost_r:.3f}%")
                    
                    res_col1, res_col2 = st.columns(2)
                    with res_col1:
                        st.write(f"原始溢價率 (Gross): **{gross_p:.2f}%**")
                    with res_col2:
                        st.write(f"扣費後淨溢價 (Net): **{net_p:.2f}%**")
                        if net_p < 0:
                            st.error("🔥 具備真實套利價值！")
                        else:
                            st.warning("⚠️ 扣費後無利可圖")

                    st.markdown("---")
                    st.subheader("🤖 AI 未來 5 日趨勢預測")
                    hist_response = supabase.table('bond_price_history').select("*").eq('bond_code', selected_code).order('record_date').execute()
                    df_hist = pd.DataFrame(hist_response.data)

                    if len(df_hist) >= 3:
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
                    st.error(f"運算發生錯誤：{e}")

    # ==========================================
    # 頁籤 2：全市場套利掃描 (黃金篩選器)
    # ==========================================
    with tab2:
        st.markdown("### 🌐 全網無風險套利機會掃描")
        st.write("點擊下方按鈕，系統將自動抓取所有股票現價，並幫您扣除手續費與稅金，篩選出真正能賺錢的標的。")
        
        if st.button("🚀 啟動全市場掃描", type="primary"):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            golden_list = []
            total_bonds = len(valid_bonds)
            
            for index, row in valid_bonds.iterrows():
                # 更新進度條
                current_step = index + 1
                progress = min(current_step / total_bonds, 1.0)
                progress_bar.progress(progress)
                status_text.text(f"📡 掃描中... {row['bond_name']} ({current_step}/{total_bonds})")
                
                # 撈取對應股票與轉換價
                bond_code = row['bond_code']
                bond_price = row['current_price']
                mapping_info = df_mapping[df_mapping['bond_code'] == bond_code]
                
                if not mapping_info.empty:
                    target_stock = mapping_info['stock_code'].values[0]
                    conv_price = mapping_info['conversion_price'].values[0]
                    yf_ticker = target_stock if ".TW" in target_stock or ".TWO" in target_stock else f"{target_stock}.TW"
                    
                    try:
                        # 靜默抓取股價 (避免印出一堆雜訊)
                        ticker = yf.Ticker(yf_ticker)
                        hist = ticker.history(period="1d")
                        if not hist.empty:
                            stock_price = hist['Close'].iloc[-1]
                            
                            # 使用我們的精確成本核算引擎
                            conv_val, gross_p, net_p, cost_r = get_net_result(bond_price, stock_price, conv_price, broker_discount)
                            
                            # 🔥 核心過濾邏輯：只把「淨利潤大於 0 (即 net_premium < 0)」的標的加入名單
                            if net_p < 0:
                                golden_list.append({
                                    "可轉債代碼": bond_code,
                                    "名稱": row['bond_name'],
                                    "債券市價": round(bond_price, 2),
                                    "股票現價": round(stock_price, 2),
                                    "轉換價": round(conv_price, 2),
                                    "原始溢價": f"{gross_p:.2f}%",
                                    "🎯 預估淨利": f"{abs(net_p):.2f}%" # 轉成正數方便閱讀
                                })
                    except Exception:
                        pass # 忽略下市或抓不到的股票，繼續掃描下一檔
                        
            status_text.text("✅ 掃描完成！")
            
            if golden_list:
                st.success(f"🎉 發現 {len(golden_list)} 檔扣除成本後仍具套利空間的標的！")
                df_golden = pd.DataFrame(golden_list)
                # 依照淨利高低排序
                df_golden = df_golden.sort_values(by="🎯 預估淨利", ascending=False).reset_index(drop=True)
                st.dataframe(df_golden, use_container_width=True)
            else:
                st.info("⚖️ 目前全市場暫無符合您手續費設定的無風險套利標的。請等待盤中行情波動！")
