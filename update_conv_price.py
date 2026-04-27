import os
import requests
import pandas as pd
from bs4 import BeautifulSoup
from supabase import create_client
import datetime
import time

# ==========================================
# 1. 系統與資料庫連線設定
# ==========================================
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ 找不到 Supabase 鑰匙，請確認環境變數設定！")
    exit()

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==========================================
# 2. 公開資訊觀測站 (MOPS) 爬蟲模組
# ==========================================
def fetch_mops_conversion_price():
    """
    爬取公開資訊觀測站「轉換公司債轉換價格調整公告」
    """
    # 取得民國年份與月份 (觀測站通常使用民國年)
    now = datetime.datetime.now()
    roc_year = now.year - 1911
    current_month = now.month

    print(f"📡 正在鎖定公開資訊觀測站：{roc_year} 年 {current_month} 月轉換價調整公告...")

    # 觀測站的 AJAX 請求網址 (彙總報表)
    url = "https://mops.twse.com.tw/mops/web/ajax_t108sb08_1"
    
    # 模擬瀏覽器發送 POST 請求所需的參數
    payload = {
        "encodeURIComponent": "1",
        "step": "1",
        "firstin": "1",
        "off": "1",
        "year": str(roc_year),
        "month": str(current_month)
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    try:
        response = requests.post(url, data=payload, headers=headers, timeout=15)
        response.raise_for_status()
        
        # 使用 Pandas 直接解析 HTML 裡的表格
        dfs = pd.read_html(response.text)
        
        if not dfs:
            print("⚠️ 本月目前尚無任何轉換價調整公告。")
            return None
            
        # 找出正確的表格 (通常欄位包含'債券代碼', '新轉換價格')
        target_df = None
        for df in dfs:
            if '債券代碼' in df.columns or any('債券代碼' in str(c) for c in df.columns):
                target_df = df
                break
                
        if target_df is None:
            print("⚠️ 找不到符合格式的公告表格。")
            return None

        # 簡單的資料清洗
        # 觀測站的表格常有多層表頭，我們需要把它平面化並找出我們要的欄位
        target_df.columns = target_df.columns.get_level_values(-1) 
        
        # 萃取我們需要的兩個核心欄位：債券代碼、新轉換價格
        # 注意：觀測站的欄位名稱有時會變，這裡做模糊比對防呆
        code_col = [c for c in target_df.columns if '代碼' in str(c)][0]
        price_col = [c for c in target_df.columns if '新' in str(c) and '價格' in str(c)][0]
        
        # 整理成乾淨的字典清單 { '11011': 45.2, ... }
        updates = {}
        for _, row in target_df.iterrows():
            code = str(row[code_col]).strip()
            price_str = str(row[price_col]).replace(',', '').strip()
            
            if code and price_str.replace('.', '', 1).isdigit():
                updates[code] = float(price_str)
                
        return updates

    except Exception as e:
        print(f"❌ MOPS 爬蟲執行失敗：{e}")
        return None

# ==========================================
# 3. Supabase 資料庫智能更新
# ==========================================
def update_database(new_prices_dict):
    if not new_prices_dict:
        return
        
    print(f"🔍 成功抓取 {len(new_prices_dict)} 筆最新轉換價公告，準備比對資料庫...")
    
    # 撈出目前我們資料庫裡的對照表
    response = supabase.table('bond_stock_mapping').select("bond_code, conversion_price").execute()
    current_db_records = response.data
    
    update_count = 0
    for record in current_db_records:
        bond_code = record['bond_code']
        old_price = record['conversion_price']
        
        # 如果爬蟲抓到的字典裡有這檔債券，且價格不一樣，就進行 Update！
        if bond_code in new_prices_dict:
            new_price = new_prices_dict[bond_code]
            
            if new_price != old_price:
                print(f"🚨 偵測到除權息調整！【{bond_code}】轉換價：{old_price} ➔ {new_price}")
                # 執行單筆更新
                supabase.table('bond_stock_mapping').update({"conversion_price": new_price}).eq("bond_code", bond_code).execute()
                update_count += 1
                time.sleep(0.1) # 避免對資料庫請求過快
                
    if update_count == 0:
        print("✅ 比對完成，今日無須更新任何轉換價。")
    else:
        print(f"🎉 報告老闆！已成功為 {update_count} 檔可轉債完成【反稀釋防禦】，拆除假套利地雷！")

# ==========================================
# 4. 主程式啟動
# ==========================================
if __name__ == "__main__":
    latest_prices = fetch_mops_conversion_price()
    update_database(latest_prices)