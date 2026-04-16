import os, json, logging, threading, asyncio, sqlite3, uuid, html
from datetime import datetime
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
GH_TOKEN = os.getenv("GH_TOKEN")
REPO_NAME = "NgDanhThanhTrung/locket_"
PORT = int(os.getenv("PORT", "8000"))
CONTACT_URL = "https://t.me/NgDanhThanhTrung"
DONATE_URL = "https://ngdanhthanhtrung.github.io/Bank/"
KOYEB_URL = "https://elderly-haddock-ngdthanhtrung-9ea3eabe.koyeb.app/"

logging.basicConfig(level=logging.INFO)
DB_PATH = "data_system.db"

# --- DATABASE INITIALIZATION ---
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            full_name TEXT,
            username TEXT,
            join_date TEXT,
            interact_count INTEGER DEFAULT 1,
            is_premium INTEGER DEFAULT 0
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS modules (
            key TEXT PRIMARY KEY,
            title TEXT,
            url TEXT
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS admins (
            user_id TEXT PRIMARY KEY,
            added_at TEXT
        )''')
        conn.commit()

init_db()

# --- HELPERS ---
def is_admin(user_id: int) -> bool:
    if user_id == ROOT_ADMIN_ID: return True
    with sqlite3.connect(DB_PATH) as conn:
        res = conn.execute("SELECT 1 FROM admins WHERE user_id = ?", (str(user_id),)).fetchone()
        return res is not None

async def db_auto_reg(u: Update):
    user = u.effective_user
    if not user: return
    uid, uname = str(user.id), (f"@{user.username}" if user.username else "N/A")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''INSERT INTO users (user_id, full_name, username, join_date) VALUES (?, ?, ?, ?)
                        ON CONFLICT(user_id) DO UPDATE SET interact_count = interact_count + 1''', 
                     (uid, user.full_name, uname, now))
        conn.commit()

# --- TEMPLATES ---
JS_TEMPLATE = """const mapping = {{ '%E8%BD%A6%E7%A5%A8%E7%A5%A8': ['vip', 'watch_vip'], 'Locket': ['Gold', 'com.{user}.premium.yearly'] }};
const ua = $request.headers["User-Agent"] || $request.headers["user-agent"];
let obj = JSON.parse($response.body);
obj.subscriber = obj.subscriber || {{}};
const premiumInfo = {{ is_sandbox: false, ownership_type: "PURCHASED", expires_date: "2999-12-18T01:04:17Z", purchase_date: "{date}T01:04:17Z", store: "app_store" }};
const entitlementInfo = {{ purchase_date: "{date}T01:04:17Z", product_identifier: "com.{user}.premium.yearly", expires_date: "2999-12-18T01:04:17Z" }};
obj.subscriber.subscriptions["com.{user}.premium.yearly"] = premiumInfo;
obj.subscriber.entitlements["Gold"] = entitlementInfo;
$done({{ body: JSON.stringify(obj) }});"""

MODULE_TEMPLATE = """#!name=Locket-Gold ({user})\n#!desc=Crack By NgDanhThanhTrung\n[Script]\nrevenuecat = type=http-response, pattern=^https:\\/\\/api\\.revenuecat\\.com\\/.+\\/(receipts$|subscribers\\/[^/]+$), script-path={js_url}, requires-body=true, max-size=-1, timeout=60\n[MITM]\nhostname = %APPEND% api.revenuecat.com"""

NEXTDNS_CONFIG = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict><key>PayloadContent</key><array><dict><key>DNSSettings</key><dict><key>DNSProtocol</key><string>HTTPS</string><key>ServerURL</key><string>https://apple.nextdns.io/{dns_id}</string></dict><key>PayloadIdentifier</key><string>com.nextdns.dns.{dns_id}</string><key>PayloadType</key><string>com.apple.dnsSettings.managed</string><key>PayloadUUID</key><string>{uuid1}</string><key>PayloadVersion</key><integer>1</integer></dict></array><key>PayloadDisplayName</key><string>NextDNS ({dns_id})</string><key>PayloadIdentifier</key><string>com.nextdns.config.{dns_id}</string><key>PayloadType</key><string>Configuration</string><key>PayloadUUID</key><string>{uuid2}</string><key>PayloadVersion</key><integer>1</integer></dict></plist>"""

# --- BOT COMMANDS ---

async def start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await db_auto_reg(u)
    txt = (f"👋 Chào mừng <b>{u.effective_user.first_name}</b>!\n\n"
           f"🚀 <b>Hệ thống NDTT Premium</b>\n"
           f"📂 SQLite Database: Online ✅\n"
           f"👨‍💻 Admin: @NgDanhThanhTrung")
    kb = [[InlineKeyboardButton("📂 Danh sách Module", callback_data="show_list")],
          [InlineKeyboardButton("👤 Hồ sơ", callback_data="profile"), InlineKeyboardButton("📖 HDSD", callback_data="hdsd")]]
    
    target = u.message if u.message else u.callback_query.message
    await target.reply_text(txt, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(kb))

async def profile(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = str(u.effective_user.id)
    with sqlite3.connect(DB_PATH) as conn:
        user = conn.execute("SELECT join_date, interact_count, is_premium FROM users WHERE user_id = ?", (uid,)).fetchone()
    
    if not user: return await u.effective_message.reply_text("❌ Không tìm thấy dữ liệu.")
    
    status = "💎 Premium" if user[2] == 1 else "🆓 Thành viên"
    txt = (f"👤 <b>HỒ SƠ CỦA BẠN</b>\n\n"
           f"🆔 ID: <code>{uid}</code>\n"
           f"📅 Tham gia: {user[0]}\n"
           f"⚡ Tương tác: {user[1]} lần\n"
           f"🌟 Trạng thái: <b>{status}</b>")
    await u.effective_message.reply_text(txt, parse_mode=ParseMode.HTML)

async def hdsd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    txt = ("📖 <b>HƯỚNG DẪN SỬ DỤNG</b>\n\n"
           "1️⃣ Dùng lệnh /get để tạo module Locket cá nhân.\n"
           "2️⃣ Copy link kết quả dán vào <b>Surge/Shadowrocket/Quantumult X</b>.\n"
           "3️⃣ Bật <b>MITM</b> và <b>HTTPS Decryption</b>.\n"
           "⚠️ Lưu ý: Không chia sẻ link cá nhân tránh bị lộ thông tin.")
    await u.effective_message.reply_text(txt, parse_mode=ParseMode.HTML)

async def get_nextdns(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not c.args:
        guide = (
            "🛠 <b>HƯỚNG DẪN TẠO NEXTDNS:</b>\n\n"
            "👉 Để lấy mã cấu hình, gõ: <code>/nextdns [ID_của_bạn]</code>\n"
            "<i>Ví dụ: /nextdns ndtt-dns</i>"
        )
        return await u.message.reply_text(guide, parse_mode=ParseMode.HTML)

    dns_id = c.args[0].strip()
    xml_content = NEXTDNS_CONFIG.format(
        dns_id=dns_id,
        uuid1=str(uuid.uuid4()),
        uuid2=str(uuid.uuid4())
    )
    safe_xml = html.escape(xml_content)
    
    msg = (f"✅ <b>Mã cấu hình cho ID:</b> <code>{dns_id}</code>\n\n"
           f"👇 Copy đoạn code bên dưới dán vào ứng dụng Ghi chú, sau đó Chia sẻ qua Shortcuts NextDNS:\n\n"
           f"<pre>{safe_xml}</pre>")
    
    await u.message.reply_text(msg, parse_mode=ParseMode.HTML)

async def get_bundle(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not c.args or "|" not in " ".join(c.args):
        return await u.message.reply_text("⚠️ Cú pháp: `/get user | yyyy-mm-dd`")
    parts = [p.strip() for p in " ".join(c.args).split("|")]
    status = await u.message.reply_text("⏳ Đang khởi tạo...")
    try:
        repo = Github(GH_TOKEN).get_repo(REPO_NAME)
        js_p, mod_p = f"{parts[0]}/L.js", f"{parts[0]}/L.sgmodule"
        js_url = f"https://raw.githubusercontent.com/{REPO_NAME}/main/{js_p}"
        js_c = JS_TEMPLATE.format(user=parts[0], date=parts[1])
        mod_c = MODULE_TEMPLATE.format(user=parts[0], js_url=js_url)
        
        for p, cnt in [(js_p, js_c), (mod_p, mod_c)]:
            try:
                f = repo.get_contents(p)
                repo.update_file(p, "Update", cnt, f.sha)
            except: repo.create_file(p, "Create", cnt)
            
        await status.edit_text(f"✅ <b>Xong!</b>\n🔗 <code>https://raw.githubusercontent.com/{REPO_NAME}/main/{mod_p}</code>", parse_mode=ParseMode.HTML)
    except Exception as e: await status.edit_text(f"❌ Lỗi: {e}")

# --- ADMIN ACTIONS ---

async def set_link(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id): return
    try:
        raw = " ".join(c.args)
        k, t, l = [p.strip() for p in raw.split("|")]
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("INSERT OR REPLACE INTO modules (key, title, url) VALUES (?, ?, ?)", (k.lower(), t, l))
            conn.commit()
        await u.message.reply_text(f"✅ Đã lưu module: <b>{t}</b>", parse_mode=ParseMode.HTML)
    except:
        await u.message.reply_text("⚠️ Cú pháp: `/setlink key | Tên | URL`")

async def del_mod(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id) or not c.args: return
    key = c.args[0].lower()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM modules WHERE key = ?", (key,))
        conn.commit()
    await u.message.reply_text(f"🗑 Đã xóa module: <b>{key}</b>")

async def broadcast(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id): return
    msg = " ".join(c.args)
    if not msg: return await u.message.reply_text("⚠️ Nhập nội dung thông báo.")
    with sqlite3.connect(DB_PATH) as conn:
        users = conn.execute("SELECT user_id FROM users").fetchall()
    count = 0
    for user in users:
        try:
            await c.bot.send_message(user[0], f"📢 <b>THÔNG BÁO TỪ ADMIN:</b>\n\n{msg}", parse_mode=ParseMode.HTML)
            count += 1
        except: pass
    await u.message.reply_text(f"✅ Đã gửi tới {count} người dùng.")

async def approve_user(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id): return
    if not c.args: return await u.message.reply_text("⚠️ Cú pháp: `/approve ID_USER`")
    target_id = c.args[0]
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE users SET is_premium = 1 WHERE user_id = ?", (target_id,))
        conn.commit()
    await u.message.reply_text(f"✅ Đã nâng cấp Premium cho {target_id}")

async def stats(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id): return
    with sqlite3.connect(DB_PATH) as conn:
        total_u = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        total_m = conn.execute("SELECT COUNT(*) FROM modules").fetchone()[0]
    await u.message.reply_text(f"📊 <b>THỐNG KÊ HỆ THỐNG</b>\n\n👥 Users: {total_u}\n📦 Modules: {total_m}", parse_mode=ParseMode.HTML)

# --- CALLBACK & MESSAGE HANDLER ---

# Đảm bảo hàm này tồn tại và truy vấn đúng bảng 'modules'
async def send_module_list(u: Update, c: ContextTypes.DEFAULT_TYPE):
    with sqlite3.connect(DB_PATH) as conn:
        # Lưu ý: bảng phải là 'modules', nếu bạn đặt tên bảng khác sẽ lỗi
        mods = conn.execute("SELECT key, title FROM modules").fetchall()
    
    if not mods:
        await u.effective_message.reply_text("📭 Danh sách module trống. Admin hãy dùng /setlink để thêm.")
        return

    txt = "<b>📂 DANH SÁCH MODULE:</b>\n\n" + "\n".join([f"🔹 /{m[0]} - {m[1]}" for m in mods])
    await u.effective_message.reply_text(txt, parse_mode=ParseMode.HTML)
    

async def dynamic_module_handler(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not u.message or not u.message.text.startswith('/'): return
    cmd = u.message.text.split()[0][1:].lower()
    
    # Bỏ qua nếu là lệnh hệ thống
    system_cmds = ['start', 'profile', 'get', 'nextdns', 'hdsd', 'broadcast', 'approve', 'stats', 'setlink', 'delmodule', 'list']
    if cmd in system_cmds: return

    with sqlite3.connect(DB_PATH) as conn:
        res = conn.execute("SELECT title, url FROM modules WHERE key = ?", (cmd,)).fetchone()
    
    if res:
        guide = (f"✨ <b>HƯỚNG DẪN: {res[0]}</b>\n\n"
                 f"🔗 Link Module: <code>{res[1]}</code>\n\n"
                 f"👉 Copy link trên dán vào Shadowrocket/Surge và bật MITM.")
        await u.message.reply_text(guide, parse_mode=ParseMode.HTML)

# --- APP START ---
async def post_init(app):
    await app.bot.set_my_commands([
        BotCommand("start", "🏠 Bắt đầu"),
        BotCommand("profile", "👤 Hồ sơ"),
        BotCommand("list", "📂 Danh sách module"),
        BotCommand("get", "✨ Tạo Locket"),
        BotCommand("nextdns", "🌐 Cấu hình DNS"),
        BotCommand("hdsd", "📖 Hướng dẫn"),
        BotCommand("stats", "📊 Thống kê (Admin)"),
        BotCommand("setlink", "➕ Thêm module (Admin)"),
        BotCommand("delmodule", "🗑 Xóa module (Admin)"),
        BotCommand("broadcast", "📢 Thông báo (Admin)"),
        BotCommand("approve", "✅ Duyệt Premium (Admin)")
    ])

app = ApplicationBuilder().token(TOKEN).post_init(post_init).build()

if __name__ == "__main__":
    server = Flask(__name__)
    @server.route('/')
    def h(): return "Bot SQLite Active"
    threading.Thread(target=lambda: server.run(host="0.0.0.0", port=PORT), daemon=True).start()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("hdsd", hdsd))
    app.add_handler(CommandHandler("nextdns", get_nextdns))
    app.add_handler(CommandHandler("get", get_bundle))
    app.add_handler(CommandHandler("list", send_module_list))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("approve", approve_user))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("setlink", set_link))
    app.add_handler(CommandHandler("delmodule", del_mod))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.COMMAND, dynamic_module_handler))

    print("--- NDTT SYSTEM READY ---")
    app.run_polling(drop_pending_updates=True)
