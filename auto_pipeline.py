import requests
import pandas as pd
from supabase import create_client, Client
import datetime
import os

# ==========================================
# 1. 老闆的設定區 (請使用 service_role 萬能鑰匙)
# ==========================================
# 讓程式自動去作業系統的環境變數裡找鑰匙
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ 找不到 Supabase 鑰匙，請確認環境變數設定！")
    exit()
    
# CSV 下載網址
CSV_DOWNLOAD_URL = "https://www.tpex.org.tw/storage/bond_zone/tradeinfo/cb/2026/202603/RSta0113.20260306-C.csv"

# ==========================================
# 2. 自動下載最新的 CSV 檔案
# ==========================================
# 取得今天日期，作為檔案命名與歷史紀錄的時間戳記
today_date = datetime.datetime.now().date()
today_str = today_date.strftime("%Y%m%d")
file_name = f"cbDaily_{today_str}.csv"

print(f"🌐 報告老闆，正在前往櫃買中心下載 {today_str} 的最新報價...")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

try:
    response = requests.get(CSV_DOWNLOAD_URL, headers=headers)
    response.raise_for_status()
    with open(file_name, "wb") as file:
        file.write(response.content)
    print(f"✅ 檔案 {file_name} 下載成功！")
except Exception as e:
    print(f"❌ 下載失敗：{e}")
    exit()

# ==========================================
# 3. 解析資料與建立「雙軌寫入」資料包
# ==========================================
print(f"📂 正在為老闆解析資料，準備進行雙軌寫入...")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    try:
        df = pd.read_csv(file_name, encoding='utf-8', skiprows=3, on_bad_lines='skip')
    except UnicodeDecodeError:
        df = pd.read_csv(file_name, encoding='cp950', skiprows=3, on_bad_lines='skip')

    df.columns = df.columns.str.strip()
    code_col = [col for col in df.columns if '代號' in col or '代碼' in col][0]
    name_col = [col for col in df.columns if '名稱' in col][0]
    price_col = [col for col in df.columns if '均價' in col][0]

    current_records = []
    history_records = []
    
    for index, row in df.iterrows():
        bond_code = str(row[code_col]).strip()
        bond_name = str(row[name_col]).strip()
        price_str = str(row[price_col]).strip()

        if not bond_code or price_str in ['--', '---', 'nan', ''] or pd.isna(row[price_col]):
            continue

        try:
            current_price = float(price_str.replace(',', ''))
        except ValueError:
            continue 

        # 👉 資料包一：給 convertible_bonds (最新報價看板)
        current_records.append({
            "bond_code": bond_code,
            "bond_name": bond_name,
            "current_price": current_price
        })
        
        # 👉 資料包二：給 bond_price_history (歷史檔案室)
        history_records.append({
            "bond_code": bond_code,
            "record_date": str(today_date),
            "close_price": current_price
        })

    # ==========================================
    # 4. 執行資料庫同步更新 (Upsert)
    # ==========================================
    if current_records and history_records:
        # 任務一：更新最新報價
        supabase.table('convertible_bonds').upsert(current_records, on_conflict='bond_code').execute()
        
        # 任務二：寫入歷史檔案室 (就算一天不小心跑兩次，也會依照日期覆蓋，不會重複寫入)
        supabase.table('bond_price_history').upsert(history_records, on_conflict='bond_code, record_date').execute()
        
        print(f"🎉 報告老闆：雙軌寫入完美結束！")
        print(f"   ➡️ 看板更新：成功更新 {len(current_records)} 檔可轉債最新價格！")
        print(f"   ➡️ 歷史歸檔：成功將 {len(history_records)} 筆紀錄存入歷史檔案室！")
        
        os.remove(file_name)
        print("🧹 已為您清理暫存的 CSV 檔案。")
    else:
        print("⚠️ 沒有讀取到有效的價格資料。")

except Exception as e:
    print(f"❌ 發生錯誤：{e}")
