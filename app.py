import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px

# ==========================================
# 1. 資料庫連線設定
# ==========================================
SUPABASE_URL = "https://ljkqyvoupfvpszkiwwef.supabase.co/"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imxqa3F5dm91cGZ2cHN6a2l3d2VmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI0NDU3MzgsImV4cCI6MjA4ODAyMTczOH0.OTTFEl25LiXZhmVhStUvvb9t2FVZhbTJElC5riM2sQE"

@st.cache_resource
def init_connection():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_connection()

@st.cache_data
def load_data():
    response = supabase.table('convertible_bonds').select("*").execute()
    df = pd.DataFrame(response.data)
    # 確保價格是數字型態，並排除沒有價格的無效資料
    df['current_price'] = pd.to_numeric(df['current_price'], errors='coerce')
    df = df.dropna(subset=['current_price'])
    return df

# ==========================================
# 2. 網頁介面與排版設計
# ==========================================
st.set_page_config(page_title="可轉債戰情儀表板", page_icon="📈", layout="wide")
st.title("📈 企業級可轉債戰情儀表板")
st.markdown("---")

# 讀取資料
with st.spinner('📡 正在從 Supabase 金庫同步最新市場數據...'):
    df = load_data()

if df.empty:
    st.warning("目前資料庫中沒有可用的報價資料，請確認爬蟲是否正常執行。")
else:
    # ==========================================
    # 3. 數據視覺化戰情區 (上半部)
    # ==========================================
    st.subheader("📊 市場總覽與熱區分析")
    
    # 使用 Streamlit 的列 (columns) 排版，將畫面切成左右兩半
    col1, col2 = st.columns(2)
    
    with col1:
        # 圖表 A：市場價格分佈圖 (Histogram)
        # 這能幫助我們一眼看出目前市場上的可轉債，大多集中在哪個價格區間，判斷市場冷熱。
        fig_dist = px.histogram(
            df, 
            x="current_price", 
            nbins=30,
            title="🎯 全市場可轉債價格分佈區間",
            labels={"current_price": "目前收市價", "count": "檔數"},
            color_discrete_sequence=['#3b82f6']
        )
        # 畫一條 100 元票面價的基準線
        fig_dist.add_vline(x=100, line_dash="dash", line_color="red", annotation_text="100元票面價")
        st.plotly_chart(fig_dist, use_container_width=True)

    with col2:
        # 圖表 B：跌破票面價的 Top 10 潛力標的 (Bar Chart)
        # 自動篩選出最便宜的 10 檔，用長條圖呈現，尋找低基期標的。
        top_10_cheap = df.sort_values(by='current_price').head(10)
        fig_bar = px.bar(
            top_10_cheap, 
            x="current_price", 
            y="bond_name", 
            orientation='h', # 水平長條圖
            title="🔥 破發尋寶：目前市場最便宜 Top 10",
            labels={"current_price": "收市價", "bond_name": "債券名稱"},
            color="current_price",
            color_continuous_scale="Viridis"
        )
        fig_bar.update_layout(yaxis={'categoryorder':'total ascending'}) # 讓最便宜的排在最上面
        st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("---")

    # ==========================================
    # 4. 互動式篩選報表區 (下半部)
    # ==========================================
    st.subheader("🎯 策略篩選與明細")
    
    # 側邊欄篩選器
    st.sidebar.header("⚙️ 篩選面板")
    max_price = st.sidebar.slider("尋找價格低於：", min_value=50.0, max_value=200.0, value=100.0, step=1.0)
    
    filtered_df = df[df['current_price'] <= max_price].sort_values(by='current_price')
    
    st.markdown(f"**💡 尋找價格低於 {max_price} 元的標的，共找到 {len(filtered_df)} 檔：**")
    
    if not filtered_df.empty:
        display_df = filtered_df[['bond_code', 'bond_name', 'current_price']]
        display_df.columns = ['債券代碼', '債券名稱', '最新收市價']
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.info("老闆，目前沒有符合此條件的標的喔！")