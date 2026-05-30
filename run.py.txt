import time
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

# === ĐIỀN THÔNG TIN CỦA BẠN VÀO ĐÂY ===
TELEGRAM_TOKEN = "8652940672:AAGoNUoa2KkBZgwiT1sjbltUNS_fjdDl0JM"
TELEGRAM_CHAT_ID = "8470245336"
GOOGLE_SHEET_NAME = "QuanLyDonHang"
JSON_KEY_FILE = "checkdon-spx-e9f223d40593" 

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

def check_spx_status(driver, tracking_number):
    try:
        # Đường dẫn tra cứu thật của SPX Express công khai
        driver.get(f"https://spx.vn/track/{tracking_number}")
        time.sleep(4) # Đợi trang web tải dữ liệu
        
        # Tìm phần tử hiển thị trạng thái mới nhất trên trang web SPX
        status_element = driver.find_element(By.CSS_SELECTOR, ".tracking-status-main, .order-status") 
        return status_element.text.strip()
    except:
        return None

def main_process():
    sheet = connect_google_sheet()
    records = sheet.get_all_records()
    
    # Cấu hình chạy Chrome ẩn trên PythonAnywhere
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(options=options)
    
    for index, row in enumerate(records, start=2):
        ma_don = str(row.get('Mã vận đơn', '')).strip()
        ten_don = str(row.get('Tên đơn / Tên khách', '')).strip()
        trang_thai_cu = str(row.get('Trạng thái mới nhất', '')).strip()
        robot_note = str(row.get('Ghi chú của Robot', '')).strip()
        
        if not ma_don or "Đã xong" in robot_note:
            continue
            
        trang_thai_moi = check_spx_status(driver, ma_don)
        
        if trang_thai_moi and trang_thai_moi != trang_thai_cu:
            current_time = time.strftime("%H:%M %d/%m")
            
            if "thành công" in trang_thai_moi.lower() or "đã hủy" in trang_thai_moi.lower():
                new_robot_note = f"Đã xong ({current_time})"
            else:
                new_robot_note = f"Đang check ({current_time})"
                
            sheet.update_cell(index, 3, trang_thai_moi)
            sheet.update_cell(index, 4, new_robot_note)
            
            msg = (f"🔔 *CẬP NHẬT ĐƠN HÀNG!*\n"
                   f"📦 Đơn hàng: *{ten_don}*\n"
                   f"🆔 Mã: `{ma_don}`\n"
                   f"🚚 Trạng thái: *{trang_thai_moi}*")
            send_telegram(msg)
                
    driver.quit()

while True:
    try:
        main_process()
    except Exception as e:
        print(f"Lỗi: {e}")
    time.sleep(300) # Nghỉ 5 phút (300 giây) rồi lặp lại
