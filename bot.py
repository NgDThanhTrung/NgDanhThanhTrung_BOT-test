import os
import json
import asyncio
from flask import Flask, render_template_string
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from github import Github
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from threading import Thread

# --- CẤU HÌNH BIẾN MÔI TRƯỜNG ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
GH_TOKEN = os.getenv("GH_TOKEN")
REPO_NAME = os.getenv("REPO_NAME")
SHEET_ID = os.getenv("SHEET_ID")
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS")
PORT = int(os.getenv("PORT", 8000))

# --- KHỞI TẠO GOOGLE SHEETS ---
def get_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(GOOGLE_CREDS_JSON)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID)

# --- KHỞI TẠO FLASK (DASHBOARD) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "<h1>System Active</h1><p>Locket Gold & NextDNS Manager is running on Koyeb.</p>"

@app.route('/health')
def health():
    return "OK", 200

# --- XỬ LÝ LOCKET GOLD (GITHUB API) ---
def deploy_locket_module(username):
    g = Github(GH_TOKEN)
    repo = g.get_repo(REPO_NAME)
    
    # Nội dung script giả lập RevenueCat (Locket Gold)
    js_content = """
    var obj = JSON.parse($response.body);
    obj.subscriber.subscriptions["gold"] = {
        "expires_date": "2999-01-01T00:00:00Z",
        "original_purchase_date": "2023-01-01T00:00:00Z",
        "purchase_date": "2023-01-01T00:00:00Z"
    };
    obj.subscriber.entitlements["gold"] = {
        "expires_date": "2999-01-01T00:00:00Z",
        "product_identifier": "locket_gold_yearly"
    };
    $done({body: JSON.stringify(obj)});
    """
    
    module_content = f"""#!name=Locket Gold ({username})
#!desc=Unlock Premium Locket Gold
[MITM]
hostname = api.revenuecat.com
[Script]
LocketGold = type=http-response,pattern=^https?:\/\/api\.revenuecat\.com\/v1\/(subscribers|receipts),requires-body=1,script-path=https://raw.githubusercontent.com/{REPO_NAME}/main/locket.js
"""
    
    # Cập nhật file lên GitHub
    try:
        repo.update_file("locket.js", "Update Script", js_content, repo.get_contents("locket.js").sha)
        repo.update_file(f"modules/{username}.sgmodule", f"Create module for {username}", module_content, branch="main")
    except:
        repo.create_file("locket.js", "Initial Script", js_content)
        repo.create_file(f"modules/{username}.sgmodule", f"Initial module for {username}", module_content)
    
    return f"https://raw.githubusercontent.com/{REPO_NAME}/main/modules/{username}.sgmodule"

# --- TELEGRAM BOT COMMANDS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 Hệ thống Locket Gold & NextDNS sẵn sàng!\nSử dụng /get [username] để tạo module.")

async def get_module(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Vui lòng nhập username. VD: /get thanh_trung")
        return
    
    username = context.args[0]
    wait_msg = await update.message.reply_text("⏳ Đang khởi tạo module trên GitHub...")
    
    try:
        raw_url = deploy_locket_module(username)
        await wait_msg.edit_text(f"✅ Thành công!\nLink Shadowrocket của bạn:\n`{raw_url}`", parse_mode='Markdown')
    except Exception as e:
        await wait_msg.edit_text(f"❌ Lỗi: {str(e)}")

# --- HÀM CHẠY BOT ---
def run_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("get", get_module))
    
    print("Bot is polling...")
    application.run_polling()

if __name__ == '__main__':
    # Chạy Bot trong một Thread riêng để Flask không bị chặn
    bot_thread = Thread(target=run_bot)
    bot_thread.start()
    
    # Chạy Flask Server cho Koyeb Health Check
    app.run(host='0.0.0.0', port=PORT)
