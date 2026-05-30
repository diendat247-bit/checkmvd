import time
import requests
import gspread
import threading
from flask import Flask
from oauth2client.service_account import ServiceAccountCredentials

# === Tạo một trang web ảo để Render chấp nhận gói FREE ===
app = Flask('')

@app.route('/')
def home():
    return "Robot check don dang hoat dong binh thuong!"

def run_web_server():
    # Chạy trang web ở cổng 10000 (mặc định của Render)
    app.run(host='0.0.0.0', port=10000)

# === ĐIỀN THÔNG TIN CỦA BẠN VÀO ĐÂY ===
TELEGRAM_TOKEN = "8652940672:AAGoNUoa2KkBZgwiT1sjbltUNS_fjdDl0JM"
TELEGRAM_CHAT_ID = "8470245336"
GOOGLE_SHEET_NAME = "QuanLyDonHang"
JSON_KEY_FILE = "checkdon-spx-e9f223d40593.json" 

def connect_google_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(JSON_KEY_FILE, scope)
    client = gspread.authorize(creds)
    return client.open(GOOGLE_SHEET_NAME).sheet1

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try: requests.post(url, json=payload)
    except: pass

def check_spx_status_api(tracking_number):
    try:
        url = f"https://tramavandon.com/api/spx?id={tracking_number}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://tramavandon.com/"
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if "logs" in data and len(data["logs"]) > 0:
                return data["logs"][0]["status"].strip()
    except:
        pass
    return None

def main_process():
    sheet = connect_google_sheet()
    records = sheet.get_all_records()
    
    for index, row in enumerate(records, start=2):
        ma_don = str(row.get('Mã vận đơn', '')).strip()
        ten_don = str(row.get('Tên đơn / Tên khách', '')).strip()
        trang_thai_cu = str(row.get('Trạng thái mới nhất', '')).strip()
        robot_note = str(row.get('Ghi chú của Robot', '')).strip()
        
        if not ma_don or "Đã xong" in robot_note:
            continue
            
        print(f"Đang check: {ten_don} ({ma_don})...")
        trang_thai_moi = check_spx_status_api(ma_don)
        
        if trang_thai_moi and trang_thai_moi != trang_thai_cu:
            current_time = time.strftime("%H:%M %d/%m")
            
            if "thành công" in trang_thai_moi.lower() or "đã hủy" in trang_thai_moi.lower():
                new_robot_note = f"Đã xong ({current_time})"
            else:
                new_robot_note = f"Đang check ({current_time})"
                
            sheet.update_cell(index, 3, trang_thai_moi)
            sheet.update_cell(index, 4, new_robot_note)
            
            msg = (f"⚡ *CẬP NHẬT ĐƠN HÀNG HỎA TỐC!*\n"
                   f"📦 Đơn hàng: *{ten_don}*\n"
                   f"🆔 Mã: `{ma_don}`\n"
                   f"🚚 Trạng thái: *{trang_thai_moi}*")
            send_telegram(msg)
            time.sleep(2)

# Hàm vòng lặp chạy ngầm quét đơn sau mỗi 1 phút
def bot_loop():
    while True:
        try:
            print("=== BẮT ĐẦU LƯỢT QUẾT 1 PHÚT (WEB) ===")
            main_process()
        except Exception as e:
            print(f"Lỗi hệ thống: {e}")
        print("Xong lượt quét. Đang đợi đúng 60 giây...")
        time.sleep(60)

if __name__ == "__main__":
    # Chạy vòng lặp bot tách biệt ở một luồng ngầm (Thread)
    t = threading.Thread(target=bot_loop)
    t.daemon = True
    t.start()
    
    # Chạy server web chính để Render thấy gói Free
    run_web_server()
