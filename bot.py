import os, json, logging, threading, asyncio, sqlite3, uuid, html, io
import pandas as pd
from datetime import datetime, timedelta, timezone
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
    TypeHandler,
    filters
)
from flask import Flask, request, jsonify

ROOT_ADMIN_ID = 7346983056 
TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TOKEN")
GH_TOKEN = os.getenv("GH_TOKEN")
REPO_NAME = "NgDanhThanhTrung/locket_"
PORT = int(os.getenv("PORT", "8000"))
CONTACT_URL = "https://t.me/NgDanhThanhTrung"
DONATE_URL = "https://ngdanhthanhtrung.github.io/Bank/"
VN_TZ = timezone(timedelta(hours=7))

logging.basicConfig(level=logging.INFO)
DB_PATH = "data_system.db"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            full_name TEXT,
            username TEXT,
            join_date TEXT,
            last_active TEXT,
            interact_count INTEGER DEFAULT 0,
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

def is_admin(user_id: int) -> bool:
    if user_id == ROOT_ADMIN_ID: return True
    with sqlite3.connect(DB_PATH) as conn:
        res = conn.execute("SELECT 1 FROM admins WHERE user_id = ?", (str(user_id),)).fetchone()
        return res is not None

async def db_auto_reg(u: Update, c: ContextTypes.DEFAULT_TYPE = None):
    user = u.effective_user
    if not user or user.is_bot: return
    uid = str(user.id)
    uname = (f"@{user.username}" if user.username else "N/A")
    fname = user.full_name
    now = datetime.now(VN_TZ).strftime("%Y-%m-%d %H:%M:%S")
    is_command = bool(u.message and u.message.text and u.message.text.startswith('/'))
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            INSERT INTO users (user_id, full_name, username, join_date, last_active, interact_count) 
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET 
                full_name = excluded.full_name, 
                username = excluded.username,
                last_active = excluded.last_active, 
                interact_count = interact_count + ?
        ''', (uid, fname, uname, now, now, (1 if is_command else 0), (1 if is_command else 0)))
        conn.commit()

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

async def start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    txt = (f"👋 Chào mừng <b>{u.effective_user.first_name}</b>!\n\n"
           f"🚀 <b>Hệ thống NDTT Premium</b>\n"
           f"📂 Database: NgDanhThanhTrung_BOT Online ✅\n"
           f"👨‍💻 Admin: @NgDanhThanhTrung")
    kb = [[InlineKeyboardButton("📂 Danh sách Module", callback_data="show_list")],
          [InlineKeyboardButton("👤 Hồ sơ", callback_data="profile"), InlineKeyboardButton("💰 Donate", callback_data="donate_info")],
          [InlineKeyboardButton("📖 HDSD", callback_data="hdsd"), InlineKeyboardButton("💬 Liên hệ Admin", url=CONTACT_URL)]]
    await u.effective_message.reply_text(txt, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(kb))

async def profile(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = str(u.effective_user.id)
    with sqlite3.connect(DB_PATH) as conn:
        user = conn.execute("SELECT join_date, interact_count, is_premium, last_active FROM users WHERE user_id = ?", (uid,)).fetchone()
    if not user: return await u.effective_message.reply_text("❌ Không tìm thấy dữ liệu.")
    status = "💎 Premium" if user[2] == 1 else "🆓 Thành viên"
    txt = (f"👤 <b>HỒ SƠ CỦA BẠN</b>\n\n🆔 ID: <code>{uid}</code>\n📅 Tham gia: {user[0]}\n"
           f"⚡ Tương tác: {user[1]} lần\n🕒 Cuối: {user[3]}\n🌟 Trạng thái: <b>{status}</b>")
    await u.effective_message.reply_text(txt, parse_mode=ParseMode.HTML)

async def donate_info(u: Update, c: ContextTypes.DEFAULT_TYPE):
    txt = ("💰 <b>ỦNG HỘ PHÁT TRIỂN (DONATE)</b>\n\n"
           "Nếu bạn thấy hệ thống hữu ích, hãy mời Admin một ly cà phê nhé!\n"
           "Mọi sự ủng hộ đều giúp hệ thống duy trì ổn định hơn. ❤️")
    kb = [[InlineKeyboardButton("💳 Ngân hàng / MOMO", url=DONATE_URL)],
          [InlineKeyboardButton("🔙 Quay lại", callback_data="back_start")]]
    if u.callback_query:
        await u.callback_query.edit_message_text(txt, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(kb))
    else:
        await u.message.reply_text(txt, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(kb))

async def get_bundle(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not c.args or "|" not in " ".join(c.args): return await u.message.reply_text("⚠️ Cú pháp: `/get user | yyyy-mm-dd`")
    parts = [p.strip() for p in " ".join(c.args).split("|")]
    status = await u.message.reply_text("⏳ Đang xử lý trên Github...")
    try:
        repo = Github(GH_TOKEN).get_repo(REPO_NAME)
        js_p, mod_p = f"{parts[0]}/L.js", f"{parts[0]}/L.sgmodule"
        js_url = f"https://raw.githubusercontent.com/{REPO_NAME}/main/{js_p}"
        js_c = JS_TEMPLATE.format(user=parts[0], date=parts[1])
        mod_c = MODULE_TEMPLATE.format(user=parts[0], js_url=js_url)
        for p, cnt in [(js_p, js_c), (mod_p, mod_c)]:
            try:
                f = repo.get_contents(p); repo.update_file(p, "Update", cnt, f.sha)
            except: repo.create_file(p, "Create", cnt)
        await status.edit_text(f"✅ <b>Link Module:</b>\n<code>https://raw.githubusercontent.com/{REPO_NAME}/main/{mod_p}</code>", parse_mode=ParseMode.HTML)
    except Exception as e: await status.edit_text(f"❌ Lỗi: {e}")

async def get_nextdns(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not c.args: return await u.message.reply_text("🛠 Gõ: <code>/nextdns [ID]</code>", parse_mode=ParseMode.HTML)
    dns_id = c.args[0].strip()
    xml = NEXTDNS_CONFIG.format(dns_id=dns_id, uuid1=str(uuid.uuid4()), uuid2=str(uuid.uuid4()))
    await u.message.reply_text(f"✅ <b>Cấu hình NextDNS:</b>\n<pre>{html.escape(xml)}</pre>", parse_mode=ParseMode.HTML)

async def admin_panel(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id): return
    txt = ("🛠 <b>BẢNG ĐIỀU KHIỂN ADMIN</b>\n\n"
           "• <code>/stats</code> - Xem thống kê\n"
           "• <code>/saoluu</code> - Xuất file Excel backup\n"
           "• <code>/approve ID</code> - Duyệt Premium\n"
           "• <code>/broadcast [nội dung]</code> - Gửi thông báo\n"
           "• <code>/setlink key | title | url</code> - Thêm module\n"
           "• <code>/delmodule key</code> - Xóa module")
    await u.message.reply_text(txt, parse_mode=ParseMode.HTML)

async def stats(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id): return
    with sqlite3.connect(DB_PATH) as conn:
        u_c = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        p_c = conn.execute("SELECT COUNT(*) FROM users WHERE is_premium = 1").fetchone()[0]
        m_c = conn.execute("SELECT COUNT(*) FROM modules").fetchone()[0]
        today = datetime.now(VN_TZ).strftime("%Y-%m-%d")
        active_today = conn.execute("SELECT COUNT(*) FROM users WHERE last_active LIKE ?", (f"{today}%",)).fetchone()[0]
    await u.message.reply_text(f"📊 <b>THỐNG KÊ</b>\n\n👤 Tổng User: {u_c}\n💎 Premium: {p_c}\n📦 Modules: {m_c}\n⚡ Hoạt động hôm nay: {active_today}", parse_mode=ParseMode.HTML)

async def backup_data(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id): return
    status_msg = await u.message.reply_text("⏳ Đang xuất dữ liệu...")
    try:
        with sqlite3.connect(DB_PATH) as conn:
            df_u = pd.read_sql_query("SELECT * FROM users", conn)
            df_m = pd.read_sql_query("SELECT * FROM modules", conn)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_u.to_excel(writer, sheet_name='Thành Viên', index=False)
            df_m.to_excel(writer, sheet_name='Danh Sách Modules', index=False)
        output.seek(0)
        timestamp = datetime.now(VN_TZ).strftime("%d-%m-%Y_%H%M")
        await u.message.reply_document(document=output, filename=f"NDTT_Backup_{timestamp}.xlsx", caption=f"📂 Sao lưu hoàn tất ({len(df_u)} Users, {len(df_m)} Modules)")
        await status_msg.delete()
    except Exception as e: await status_msg.edit_text(f"❌ Lỗi sao lưu: {e}")

async def approve_user(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id) or not c.args: return
    uid = c.args[0]
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE users SET is_premium = 1 WHERE user_id = ?", (uid,))
        conn.commit()
    await u.message.reply_text(f"✅ Đã duyệt Premium cho ID: {uid}")
    try: await c.bot.send_message(uid, "🎉 Tài khoản của bạn đã được nâng cấp lên <b>Premium</b>!", parse_mode=ParseMode.HTML)
    except: pass

async def broadcast(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id): return
    msg = " ".join(c.args)
    if not msg: return
    with sqlite3.connect(DB_PATH) as conn: users = conn.execute("SELECT user_id FROM users").fetchall()
    count = 0
    for user in users:
        try:
            await c.bot.send_message(user[0], f"📢 <b>THÔNG BÁO TỪ HỆ THỐNG:</b>\n\n{msg}", parse_mode=ParseMode.HTML)
            count += 1
            await asyncio.sleep(0.05)
        except: pass
    await u.message.reply_text(f"✅ Đã gửi thông báo tới {count} người dùng.")

async def set_link(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id): return
    try:
        k, t, l = [p.strip() for p in " ".join(c.args).split("|")]
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("INSERT OR REPLACE INTO modules VALUES (?, ?, ?)", (k.lower(), t, l))
            conn.commit()
        await u.message.reply_text(f"✅ Đã lưu module: {t}")
    except: await u.message.reply_text("⚠️ Cú pháp: `/setlink key | tiêu đề | link`")

async def del_mod(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id) or not c.args: return
    key = c.args[0].lower()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM modules WHERE key = ?", (key,))
        conn.commit()
    await u.message.reply_text(f"🗑 Đã xóa module: {key}")

async def send_module_list(u: Update, c: ContextTypes.DEFAULT_TYPE, page: int = 1):
    uid = u.effective_user.id
    is_user_admin = is_admin(uid)
    per_page = 5
    with sqlite3.connect(DB_PATH) as conn:
        mods = conn.execute("SELECT key, title FROM modules").fetchall()
        txt = f"<b>📂 DANH SÁCH MODULES ({len(mods)})</b>\n\n"
        txt += "\n".join([f"🔹 /{m[0]} - {m[1]}" for m in mods]) if mods else "📭 Hiện chưa có module nào."
        kb = [[InlineKeyboardButton("💰 Donate ủng hộ", callback_data="donate_info")]]
        if is_user_admin:
            offset = (page - 1) * per_page
            total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            total_pages = (total_users + per_page - 1) // per_page
            users = conn.execute("SELECT user_id, full_name, is_premium FROM users ORDER BY last_active DESC LIMIT ? OFFSET ?", (per_page, offset)).fetchall()
            txt += f"\n\n👑 <b>ADMIN: QUẢN LÝ ({page}/{total_pages})</b>\n"
            txt += "\n".join([f"👤 {us[1]} (<code>{us[0]}</code>) {'💎' if us[2] else '🆓'}" for us in users])
            nav = []
            if page > 1: nav.append(InlineKeyboardButton("⬅️", callback_data=f"list_page_{page-1}"))
            if page < total_pages: nav.append(InlineKeyboardButton("➡️", callback_data=f"list_page_{page+1}"))
            if nav: kb.append(nav)
    kb.append([InlineKeyboardButton("👤 Hồ sơ", callback_data="profile"), InlineKeyboardButton("🔙 Quay lại", callback_data="back_start")])
    reply_markup = InlineKeyboardMarkup(kb)
    if u.callback_query: await u.callback_query.edit_message_text(txt, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
    else: await u.effective_message.reply_text(txt, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

async def callback_handler(u: Update, c: ContextTypes.DEFAULT_TYPE):
    query = u.callback_query; await query.answer()
    if query.data == "show_list": await send_module_list(u, c)
    elif query.data.startswith("list_page_"): await send_module_list(u, c, page=int(query.data.split("_")[-1]))
    elif query.data == "profile": await profile(u, c)
    elif query.data == "donate_info": await donate_info(u, c)
    elif query.data == "back_start": await start(u, c)
    elif query.data == "hdsd": await u.effective_message.reply_text("📖 <b>HDSD:</b>\n1. <code>/get user | date</code>\n2. Cài Module vào Surge/Shadowrocket.\n3. Bật MITM.", parse_mode=ParseMode.HTML)

async def dynamic_module_handler(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not u.message or not u.message.text.startswith('/'): return
    cmd = u.message.text.split()[0][1:].lower()
    sys_cmds = ['start', 'profile', 'get', 'nextdns', 'admin', 'stats', 'saoluu', 'approve', 'broadcast', 'setlink', 'delmodule', 'list', 'donate', 'hdsd']
    if cmd in sys_cmds: return
    with sqlite3.connect(DB_PATH) as conn:
        res = conn.execute("SELECT title, url FROM modules WHERE key = ?", (cmd,)).fetchone()
    if res: await u.message.reply_text(f"✨ <b>{res[0]}</b>\n🔗 <code>{res[1]}</code>", parse_mode=ParseMode.HTML)

server = Flask(__name__)
@server.route('/')
def home(): return "Bot Online ✅"

async def post_init(application):
    await application.bot.set_my_commands([
        BotCommand("start", "🏠 Bắt đầu"), BotCommand("profile", "👤 Hồ sơ"),
        BotCommand("list", "📂 Danh sách Modules"), BotCommand("get", "✨ Tạo Locket Gold"),
        BotCommand("nextdns", "🌐 Tạo Config NextDNS"), BotCommand("donate", "💰 Donate ủng hộ Admin"),
        BotCommand("admin", "🛠 Menu Admin")
    ])

if __name__ == "__main__":
    threading.Thread(target=lambda: server.run(host="0.0.0.0", port=PORT, use_reloader=False), daemon=True).start()
    app = ApplicationBuilder().token(TOKEN).post_init(post_init).build()
    app.add_handler(TypeHandler(Update, db_auto_reg), group=-1)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("list", send_module_list))
    app.add_handler(CommandHandler("get", get_bundle))
    app.add_handler(CommandHandler("nextdns", get_nextdns))
    app.add_handler(CommandHandler("donate", donate_info))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("saoluu", backup_data))
    app.add_handler(CommandHandler("approve", approve_user))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("setlink", set_link))
    app.add_handler(CommandHandler("delmodule", del_mod))
    app.add_handler(CommandHandler("hdsd", callback_handler))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.COMMAND, dynamic_module_handler))
    app.run_polling(drop_pending_updates=True)
