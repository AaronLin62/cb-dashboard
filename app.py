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
def load_current_data():
    response = supabase.table('convertible_bonds').select("*").execute()
    df = pd.DataFrame(response.data)
    if not df.empty:
        df['current_price'] = pd.to_numeric(df['current_price'], errors='coerce')
        df = df.dropna(subset=['current_price'])
    return df

# ==========================================
# 2. 👑 老闆專屬：手動對照表 (代替 CSV 資料庫)
# 這裡我們先設定兩檔作為測試樣本，讓 yfinance 知道要抓誰
# ==========================================
MOCK_MAPPING = {
    "11011": {"stock_code": "1101.TW", "conversion_price": 35.6},
    "31052": {"stock_code": "3105.TWO", "conversion_price": 140.0} # 假設的穩懋可轉債
}

# ==========================================
# 3. 網頁介面設計
# ==========================================
st.set_page_config(page_title="可轉債戰情儀表板", page_icon="📈", layout="wide")
st.title("📈 企業級可轉債戰情室 - yfinance 套利雷達版")
st.markdown("---")

df_current = load_current_data()

if df_current.empty:
    st.warning("目前資料庫中沒有報價資料。")
else:
    st.subheader("🔥 負溢價套利雷達 (即時股價連線)")
    
    # 只篩選出我們有寫在 MOCK_MAPPING 裡的測試標的
    test_bonds = df_current[df_current['bond_code'].isin(MOCK_MAPPING.keys())]
    
    if test_bonds.empty:
        st.info("目前資料庫最新的報價中，沒有包含我們測試的標的 (11011 或 31052)。")
    else:
        bond_options = test_bonds['bond_code'] + " - " + test_bonds['bond_name']
        selected_option = st.selectbox("請選擇要進行套利分析的標的：", bond_options)
        
        selected_code = selected_option.split(" - ")[0]
        selected_name = selected_option.split(" - ")[1]
        
        # 從我們手寫的對照表拿出參數
        target_stock = MOCK_MAPPING[selected_code]["stock_code"]
        conv_price = MOCK_MAPPING[selected_code]["conversion_price"]
        bond_price = test_bonds[test_bonds['bond_code'] == selected_code]['current_price'].values[0]
        
        with st.spinner(f'📡 正在透過 yfinance 連線取得 {target_stock} 即時股價...'):
            try:
                # 呼叫 yfinance 抓取即時股價
                ticker = yf.Ticker(target_stock)
                stock_price = ticker.history(period="1d")['Close'].iloc[-1]
                
                # --- 執行套利演算法數學公式 ---
                # 1. 轉換價值 = (100 / 轉換價) * 股票市價
                conversion_value = (100 / conv_price) * stock_price
                
                # 2. 轉換溢價率 = (可轉債市價 - 轉換價值) / 轉換價值 * 100%
                premium_rate = ((bond_price - conversion_value) / conversion_value) * 100
                
                # --- 渲染視覺化戰情看板 ---
                col1, col2, col3 = st.columns(3)
                col1.metric("可轉債最新市價", f"{bond_price:.2f} 元")
                col2.metric(f"對應股票 ({target_stock}) 即時市價", f"{stock_price:.2f} 元")
                col3.metric("合約轉換價", f"{conv_price:.2f} 元")
                
                st.markdown("### 📊 套利分析結果")
                
                # 根據溢價率給予不同的顏色與警語
                if premium_rate < 0:
                    st.success(f"🔥 發現潛在套利空間！目前折價 **{premium_rate:.2f}%**")
                    st.write(f"💡 解讀：這張債券目前的理論價值應該是 {conversion_value:.2f} 元，但市場只賣 {bond_price:.2f} 元，被低估了！")
                else:
                    st.info(f"⚖️ 目前為溢價狀態：**{premium_rate:.2f}%** (無套利空間)")
                    st.write(f"💡 解讀：這張債券目前的理論價值是 {conversion_value:.2f} 元，市場賣 {bond_price:.2f} 元，價格合理包含保本價值。")
                    
            except Exception as e:
                st.error(f"連線 yfinance 發生錯誤：{e}")

    st.markdown("---")
    st.subheader("📊 全市場低價尋寶區 (原有功能)")
    st.dataframe(df_current[['bond_code', 'bond_name', 'current_price']], use_container_width=True)
