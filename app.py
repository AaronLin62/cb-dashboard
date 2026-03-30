import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import timedelta

# ==========================================
# 1. 資料庫連線設定 (機密不落地原則)
# ==========================================
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

@st.cache_resource
def init_connection():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_connection()

# 讀取最新報價 (給上半部儀表板用)
@st.cache_data(ttl=600)
def load_current_data():
    response = supabase.table('convertible_bonds').select("*").execute()
    df = pd.DataFrame(response.data)
    if not df.empty:
        df['current_price'] = pd.to_numeric(df['current_price'], errors='coerce')
        df = df.dropna(subset=['current_price'])
    return df

# 讀取單一個股的歷史報價 (給預測模型用)
def load_history_data(bond_code):
    response = supabase.table('bond_price_history').select("*").eq('bond_code', bond_code).execute()
    df = pd.DataFrame(response.data)
    if not df.empty:
        df['close_price'] = pd.to_numeric(df['close_price'], errors='coerce')
        df['record_date'] = pd.to_datetime(df['record_date'])
        df = df.sort_values('record_date') # 確保日期由舊到新排序
    return df

# ==========================================
# 2. 網頁介面與排版設計
# ==========================================
st.set_page_config(page_title="可轉債戰情儀表板", page_icon="📈", layout="wide")
st.title("📈 企業級可轉債戰情室與 AI 預測系統")
st.markdown("---")

df_current = load_current_data()

if df_current.empty:
    st.warning("目前資料庫中沒有報價資料，請確認爬蟲是否正常執行。")
else:
    # ==========================================
    # 3. 🔮 AI 趨勢預測與歷史回測專區 (期中專案火力展示)
    # ==========================================
    st.subheader("🔮 個股歷史走勢與 AI 趨勢預測")
    
    # 讓老闆透過下拉選單挑選想看的標的 (格式：11011 - 台泥一永)
    bond_options = df_current['bond_code'] + " - " + df_current['bond_name']
    selected_option = st.selectbox("請選擇要進行 AI 分析的標的：", bond_options)
    
    # 萃取出代碼
    selected_code = selected_option.split(" - ")[0]
    selected_name = selected_option.split(" - ")[1]
    
    with st.spinner('📡 正在從歷史檔案室調閱數據，並啟動 AI 預測引擎...'):
        df_hist = load_history_data(selected_code)
        
    if not df_hist.empty and len(df_hist) > 3: # 至少要有幾天資料才能畫趨勢
        # --- AI 線性預測邏輯 ---
        # 將日期轉換為數字 (距離第一天的天數) 以利計算斜率
        days_since_start = (df_hist['record_date'] - df_hist['record_date'].min()).dt.days
        prices = df_hist['close_price'].values
        
        # 使用 numpy 算出最佳線性趨勢線 (斜率與截距)
        slope, intercept = np.polyfit(days_since_start, prices, 1)
        
        # 建立預測未來的時間軸 (往後推 5 天)
        last_date = df_hist['record_date'].max()
        future_dates = [last_date + timedelta(days=i) for i in range(1, 6)]
        future_days_num = [(d - df_hist['record_date'].min()).days for d in future_dates]
        
        # 計算預測價格
        future_prices = [slope * d + intercept for d in future_days_num]
        
        # --- 繪製進階互動圖表 ---
        fig = go.Figure()
        
        # 1. 畫出「真實歷史走勢」 (實線)
        fig.add_trace(go.Scatter(
            x=df_hist['record_date'], y=df_hist['close_price'],
            mode='lines+markers', name='歷史收市價',
            line=dict(color='#3b82f6', width=3),
            marker=dict(size=6)
        ))
        
        # 2. 畫出「AI 未來預測走勢」 (虛線)
        fig.add_trace(go.Scatter(
            x=future_dates, y=future_prices,
            mode='lines+markers', name='AI 趨勢預測 (未來5天)',
            line=dict(color='#ef4444', width=3, dash='dash'),
            marker=dict(size=8, symbol='star')
        ))
        
        # 美化圖表
        fig.update_layout(
            title=f"【{selected_name}】歷史走勢回測與線性趨勢預測",
            xaxis_title="日期",
            yaxis_title="價格",
            hovermode="x unified" # 游標移過去時顯示整排數據
        )
        
        # 將 100 元票面價基準線加上去
        fig.add_hline(y=100, line_dash="dot", line_color="green", annotation_text="100元 面額基準", annotation_position="bottom right")
        
        st.plotly_chart(fig, use_container_width=True)
        
        # 商業解讀警語
        trend_status = "📈 向上" if slope > 0 else "📉 向下"
        st.info(f"💡 **AI 分析報告**：根據過去 30 天數據，{selected_name} 的整體趨勢為 **{trend_status}**。*(註：此為基於歷史數據之線性推估，僅供參考，非投資建議)*")
        
    else:
        st.warning("⚠️ 該標的歷史資料不足，無法啟動預測引擎。")

    st.markdown("---")
    
    # ==========================================
    # 4. 全市場總覽 (保留原本的戰情圖表)
    # ==========================================
    st.subheader("📊 全市場低價尋寶區")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown("### ⚙️ 快速篩選")
        max_price = st.slider("尋找價格低於：", min_value=50.0, max_value=200.0, value=100.0, step=1.0)
        filtered_df = df_current[df_current['current_price'] <= max_price].sort_values(by='current_price')
        st.metric(label="符合條件標的數量", value=f"{len(filtered_df)} 檔")

    with col2:
        if not filtered_df.empty:
            display_df = filtered_df[['bond_code', 'bond_name', 'current_price']]
            display_df.columns = ['債券代碼', '債券名稱', '最新收市價']
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.info("目前沒有符合此條件的標的喔！")
