import os, json, logging, threading, asyncio, re, uuid, sqlite3
import gspread
from functools import lru_cache
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
from github import Github
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand
)
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)
from flask import Flask, render_template, request, jsonify

# --- CONFIGURATION ---
ROOT_ADMIN_ID = 7346983056 
TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TOKEN")
SHEET_ID = os.getenv("SHEET_ID")
GH_TOKEN = os.getenv("GH_TOKEN")
REPO_NAME = "NgDanhThanhTrung/locket_"
PORT = int(os.getenv("PORT", "8000"))
CONTACT_URL = "https://t.me/NgDanhThanhTrung"
DONATE_URL = "https://ngdanhthanhtrung.github.io/Bank/"
KOYEB_URL = "https://elderly-haddock-ngdthanhtrung-9ea3eabe.koyeb.app/"
WEB_URL = "https://ngdanhthanhtrung.github.io/Modules-NDTT-Premium/"

logging.basicConfig(level=logging.INFO)

# --- DATABASE SETUP (SQLite) ---
DB_PATH = "bot_data.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS extra_admins 
                     (user_id TEXT PRIMARY KEY, added_at TEXT)''')
    conn.commit()
    conn.close()

init_db()

def is_admin(user_id: int) -> bool:
    if user_id == ROOT_ADMIN_ID:
        return True
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM extra_admins WHERE user_id = ?", (str(user_id),))
    res = cursor.fetchone()
    conn.close()
    return res is not None

# --- TEMPLATES ---
JS_TEMPLATE = """const mapping = {{
  '%E8%BD%A6%E7%A5%A8%E7%A5%A8': ['vip', 'watch_vip'],
  'Locket': ['Gold', 'com.{user}.premium.yearly']
}};
const ua = $request.headers["User-Agent"] || $request.headers["user-agent"];
let obj = JSON.parse($response.body);
obj.subscriber = obj.subscriber || {{}};
obj.subscriber.entitlements = obj.subscriber.entitlements || {{}};
obj.subscriber.subscriptions = obj.subscriber.subscriptions || {{}};
const premiumInfo = {{
  is_sandbox: false,
  ownership_type: "PURCHASED",
  billing_issues_detected_at: null,
  period_type: "normal",
  expires_date: "2999-12-18T01:04:17Z",
  original_purchase_date: "{date}T01:04:17Z",
  purchase_date: "{date}T01:04:17Z",
  store: "app_store"
}};
const entitlementInfo = {{
  grace_period_expires_date: null,
  purchase_date: "{date}T01:04:17Z",
  product_identifier: "com.{user}.premium.yearly",
  expires_date: "2999-12-18T01:04:17Z"
}};
const match = Object.keys(mapping).find(e => ua.includes(e));
if (match) {{
  let [entKey, subKey] = mapping[match];
  let finalSubKey = subKey || "com.{user}.premium.yearly";
  entitlementInfo.product_identifier = finalSubKey;
  obj.subscriber.subscriptions[finalSubKey] = premiumInfo;
  obj.subscriber.entitlements[entKey] = entitlementInfo;
}} else {{
  obj.subscriber.subscriptions["com.{user}.premium.yearly"] = premiumInfo;
  obj.subscriber.entitlements["Gold"] = entitlementInfo;
  obj.subscriber.entitlements["pro"] = entitlementInfo;
}}
obj.Attention = "Chúc mừng bạn! Vui lòng không bán hoặc chia sẻ cho người khác!";
$done({{ body: JSON.stringify(obj) }});"""

MODULE_TEMPLATE = """#!name=Locket-Gold ({user})
#!desc=Crack By NgDanhThanhTrung
[Script]
revenuecat = type=http-response, pattern=^https:\\/\\/api\\.revenuecat\\.com\\/.+\\/(receipts$|subscribers\\/[^/]+$), script-path={js_url}, requires-body=true, max-size=-1, timeout=60
deleteHeader = type=http-request, pattern=^https:\\/\\/api\\.revenuecat\\.com\\/.+\\/(receipts|subscribers), script-path=https://raw.githubusercontent.com/NgDanhThanhTrung/locket_/main/Locket_NDTT/deleteHeader.js, timeout=60
[MITM]
hostname = %APPEND% api.revenuecat.com"""

# --- GOOGLE SHEETS LOGIC ---
def get_sheets():
    creds_raw = os.getenv("GOOGLE_CREDS")
    if not creds_raw: raise RuntimeError("Missing GOOGLE_CREDS")
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(creds_raw),
        ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    )
    ss = gspread.authorize(creds).open_by_key(SHEET_ID)
    return ss.worksheet("modules"), ss.worksheet("users"), ss.worksheet("admin"), ss.worksheet("data")

async def auto_reg(u: Update, s_u, s_d):
    user = u.effective_user
    if not user: return
    try:
        uid, uname = str(user.id), (f"@{user.username}" if user.username else "N/A")
        if uid not in s_u.col_values(1):
            s_u.append_row([uid, user.full_name, uname])
        ids = s_d.col_values(1)
        if uid not in ids:
            s_d.append_row([uid, uname, 1])
        else:
            row = ids.index(uid) + 1
            curr = s_d.cell(row, 3).value
            s_d.update_cell(row, 3, (int(curr) if curr and str(curr).isdigit() else 0) + 1)
    except Exception as e: logging.error(f"Auto reg error: {e}")

# --- BOT COMMANDS ---

async def start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    try:
        s_m, s_u, s_a, s_d = get_sheets()
        await auto_reg(u, s_u, s_d)
    except: pass
    
    txt = (f"👋 Chào mừng <b>{u.effective_user.first_name}</b>!\n\n"
           f"🚀 <b>Tính năng:</b> Tạo Module Locket Gold & NextDNS.\n"
           f"🌐 Dashboard: <code>{KOYEB_URL}</code>\n"
           f"👨‍💻 Admin: @NgDanhThanhTrung")
    kb = [[InlineKeyboardButton("📂 Danh sách Module", callback_data="show_list")],
          [InlineKeyboardButton("💬 Liên hệ", url=CONTACT_URL), InlineKeyboardButton("☕ Donate", url=DONATE_URL)]]
    
    # Hỗ trợ gửi tin nhắn mới hoặc sửa tin nhắn cũ từ Callback
    if u.message:
        await u.message.reply_text(txt, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(kb))
    else:
        await u.callback_query.edit_message_text(txt, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(kb))

async def send_module_list(u: Update, c: ContextTypes.DEFAULT_TYPE):
    try:
        s_m, _, _, _ = get_sheets()
        records = s_m.get_all_records()
        m_list = "<b>📂 DANH SÁCH MODULE HỆ THỐNG:</b>\n\n"
        m_list += "\n".join([f"🔹 /{r['key']} - {r['title']}" for r in records])
        
        target = u.message if u.message else u.callback_query.message
        await target.reply_text(m_list, parse_mode=ParseMode.HTML)
    except Exception as e:
        await u.effective_message.reply_text(f"❌ Lỗi lấy dữ liệu: {e}")

async def get_bundle(u: Update, c: ContextTypes.DEFAULT_TYPE):
    raw = " ".join(c.args)
    if "|" not in raw:
        return await u.message.reply_text("⚠️ Cú pháp: `/get tên_user | yyyy-mm-dd`", parse_mode=ParseMode.HTML)
    parts = [p.strip() for p in raw.split("|")]
    status = await u.message.reply_text("⏳ Đang khởi tạo Module...")
    try:
        url = await sync_github_files(parts[0], parts[1])
        await status.edit_text(f"✅ <b>THÀNH CÔNG!</b>\n\n🔗 Link: <code>{url}</code>", parse_mode=ParseMode.HTML)
    except Exception as e:
        await status.edit_text(f"❌ Lỗi: {e}")

async def sync_github_files(user, date):
    repo = Github(GH_TOKEN).get_repo(REPO_NAME)
    js_p, mod_p = f"{user}/Locket_Gold.js", f"{user}/Locket_{user}.sgmodule"
    js_url = f"https://raw.githubusercontent.com/{REPO_NAME}/main/{js_p}"
    js_content = JS_TEMPLATE.format(user=user, date=date)
    mod_content = MODULE_TEMPLATE.format(user=user, js_url=js_url)
    for path, content in [(js_p, js_content), (mod_p, mod_content)]:
        try:
            f = repo.get_contents(path, ref="main")
            repo.update_file(path, f"Sync {user}", content, f.sha, branch="main")
        except:
            repo.create_file(path, f"Sync {user}", content, branch="main")
    return f"https://raw.githubusercontent.com/{REPO_NAME}/main/{mod_p}"

# --- ADMIN COMMANDS (SQLite) ---
async def add_admin(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if u.effective_user.id != ROOT_ADMIN_ID: return
    if not c.args: return await u.message.reply_text("⚠️ Cú pháp: `/addadmin [User_ID]`")
    new_id = c.args[0].strip()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT OR REPLACE INTO extra_admins (user_id, added_at) VALUES (?, ?)", 
                 (new_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()
    await u.message.reply_text(f"✅ Đã thêm phó nhóm: <code>{new_id}</code>", parse_mode=ParseMode.HTML)

async def admin_list(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id): return
    conn = sqlite3.connect(DB_PATH)
    admins = conn.execute("SELECT * FROM extra_admins").fetchall()
    conn.close()
    txt = f"👑 <b>ROOT:</b> <code>{ROOT_ADMIN_ID}</code>\n\n🛡 <b>PHÓ NHÓM:</b>\n"
    txt += "\n".join([f"• <code>{r[0]}</code> ({r[1]})" for r in admins]) if admins else "<i>Chưa có phó nhóm.</i>"
    await u.message.reply_text(txt, parse_mode=ParseMode.HTML)

async def stats(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id): return
    s_m, s_u, s_a, s_d = get_sheets()
    await u.message.reply_text(f"📊 <b>THỐNG KÊ</b>\n\n👥 Users: {len(s_u.col_values(1))-1}\n📦 Modules: {len(s_m.get_all_records())}", parse_mode=ParseMode.HTML)

# --- CALLBACK HANDLER (MỚI) ---
async def callback_handler(u: Update, c: ContextTypes.DEFAULT_TYPE):
    """Xử lý tất cả các sự kiện khi người dùng nhấn nút Inline"""
    query = u.callback_query
    data = query.data
    await query.answer()

    if data == "show_list":
        await send_module_list(u, c)
    elif data == "main_menu":
        await start(u, c)
    elif data.startswith("get_info_"):
        module_key = data.replace("get_info_", "")
        await query.edit_message_text(f"Bạn đang xem chi tiết module: {module_key}")

# --- PLACEHOLDERS (Để tránh lỗi nếu thiếu hàm) ---
async def profile(u, c): await u.message.reply_text("👤 Tính năng Profile đang cập nhật...")
async def hdsd(u, c): await u.message.reply_text("📖 Hướng dẫn sử dụng: [Link HDSD]")
async def myid(u, c): await u.message.reply_text(f"🆔 ID của bạn là: <code>{u.effective_user.id}</code>", parse_mode=ParseMode.HTML)
async def handle_msg(u, c): pass # Hàm xử lý từ sheet nếu cần

# --- FLASK SERVER ---
server = Flask(__name__)
@server.route('/')
def index(): return render_template('index.html')

@server.route('/api/generate', methods=['POST'])
def api_generate():
    data = request.json
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        url = loop.run_until_complete(sync_github_files(data.get('user'), data.get('join_date')))
        return jsonify({"success": True, "url": url})
    except Exception as e: return jsonify({"error": str(e)}), 500

# --- CẬP NHẬT PHẦN KHỞI TẠO BOT ---
async def post_init(application):
    """Thiết lập Menu Bot khi khởi động"""
    await application.bot.set_my_commands([
        BotCommand("start", "🏠 Bắt đầu"),
        BotCommand("list", "📂 Danh sách Module"),
        BotCommand("get", "✨ Tạo Locket riêng"),
        BotCommand("profile", "👤 Hồ sơ cá nhân"),
        BotCommand("hdsd", "📖 Hướng dẫn sử dụng"),
        BotCommand("myid", "🆔 Lấy ID của bạn"),
        BotCommand("adminlist", "🛡 DS Admin"),
        BotCommand("stats", "📊 Thống kê (Admin)")
    ])

# Khởi tạo App duy nhất
app = ApplicationBuilder().token(TOKEN).post_init(post_init).build()

if __name__ == "__main__":
    # Chạy Flask Web Server
    threading.Thread(
        target=lambda: server.run(host="0.0.0.0", port=PORT, use_reloader=False), 
        daemon=True
    ).start()

    # --- ĐĂNG KÝ CÁC HANDLER ---
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("hdsd", hdsd))
    app.add_handler(CommandHandler("list", send_module_list))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("get", get_bundle))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("addadmin", add_admin))
    app.add_handler(CommandHandler("adminlist", admin_list))

    # Xử lý Callback từ các nút bấm
    app.add_handler(CallbackQueryHandler(callback_handler))

    # Xử lý tin nhắn văn bản (cho các module động)
    app.add_handler(MessageHandler(filters.COMMAND, handle_msg))

    print("--- BOT ĐÃ SẴN SÀNG HOẠT ĐỘNG ---")
    app.run_polling(drop_pending_updates=True)
