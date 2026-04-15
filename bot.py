import os
import json
import asyncio
from threading import Thread
from flask import Flask, render_template

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from github import Github
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- CẤU HÌNH BIẾN MÔI TRƯỜNG ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
GH_TOKEN = os.getenv("GH_TOKEN")
REPO_NAME = os.getenv("REPO_NAME")
SHEET_ID = os.getenv("SHEET_ID")
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS")
PORT = int(os.getenv("PORT", 8000))

# --- KHỞI TẠO FLASK ---
app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/health')
def health():
    return "OK", 200

# --- LOGIC GITHUB (LOCKET GOLD) ---
def deploy_locket_module(username):
    g = Github(GH_TOKEN)
    repo = g.get_repo(REPO_NAME)
    
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
#!desc=Unlock Premium Locket Gold vĩnh viễn
[MITM]
hostname = api.revenuecat.com
[Script]
LocketGold = type=http-response,pattern=^https?:\/\/api\.revenuecat\.com\/v1\/(subscribers|receipts),requires-body=1,script-path=https://raw.githubusercontent.com/{REPO_NAME}/main/locket.js
"""
    
    try:
        # Cập nhật script gốc
        try:
            contents = repo.get_contents("locket.js")
            repo.update_file("locket.js", "Update Script", js_content, contents.sha)
        except:
            repo.create_file("locket.js", "Initial Script", js_content)
            
        # Tạo file module cá nhân
        path = f"modules/{username}.sgmodule"
        repo.create_file(path, f"Create module for {username}", module_content)
    except Exception as e:
        print(f"GitHub Error: {e}")
        
    return f"https://raw.githubusercontent.com/{REPO_NAME}/main/modules/{username}.sgmodule"

# --- TELEGRAM BOT HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 Hệ thống Locket Gold & NextDNS sẵn sàng!\nDùng /get [username] để lấy module.")

async def get_module(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Vui lòng nhập: /get [username]")
        return
    
    username = context.args[0]
    msg = await update.message.reply_text("⏳ Đang xử lý trên GitHub...")
    
    try:
        url = deploy_locket_module(username)
        await msg.edit_text(f"✅ Thành công!\nLink Shadowrocket:\n`{url}`", parse_mode='Markdown')
    except Exception as e:
        await msg.edit_text(f"❌ Lỗi: {str(e)}")

# --- RUNNER ---
def run_flask():
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)

if __name__ == '__main__':
    # Chạy Flask ở luồng phụ
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()
    
    # Chạy Bot ở luồng chính
    print("Bot is starting...")
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("get", get_module))
    application.run_polling()
