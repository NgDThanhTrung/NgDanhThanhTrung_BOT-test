import os
import asyncio
from flask import Flask, render_template
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from github import Github
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- CẤU HÌNH BIẾN MÔI TRƯỜNG ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
GH_TOKEN = os.getenv("GH_TOKEN")
REPO_NAME = os.getenv("REPO_NAME")
PORT = int(os.getenv("PORT", 8000))

# --- KHỞI TẠO FLASK (DASHBOARD) ---
app = Flask(__name__)

@app.route('/')
def index():
    return "Locket Gold & NextDNS System is Running!" # Có thể thay bằng render_template('index.html')

# --- LOGIC XỬ LÝ LOCKET GOLD (GitHub API) ---
def create_locket_module(username):
    g = Github(GH_TOKEN)
    repo = g.get_repo(REPO_NAME)
    
    js_content = "/* Script bẻ khóa RevenueCat logic */"
    module_content = f"#!name=Locket Gold\n#!desc=Unlock Premium\n[Script]\n..."
    
    # Đẩy file lên GitHub
    repo.create_file(f"modules/{username}.js", "Update JS", js_content)
    repo.create_file(f"modules/{username}.sgmodule", "Update Module", module_content)
    return f"https://raw.githubusercontent.com/{REPO_NAME}/main/modules/{username}.sgmodule"

# --- TELEGRAM BOT COMMANDS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Chào mừng bạn đến với Locket Gold Manager!")

async def get_locket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = context.args[0] if context.args else update.effective_user.username
    link = create_locket_module(username)
    await update.message.reply_text(f"Module của bạn: {link}")

# --- CHẠY SONG SONG WEB & BOT ---
if __name__ == '__main__':
    # Khởi chạy Telegram Bot
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("get", get_locket))
    
    # Chạy Flask ở luồng riêng hoặc dùng web server tích hợp
    from threading import Thread
    Thread(target=lambda: app.run(host='0.0.0.0', port=PORT, use_reloader=False)).start()
    
    application.run_polling()
