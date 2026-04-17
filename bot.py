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
from flask import Flask, request, jsonify, render_template
# --- CONFIGURATION ---
ROOT_ADMIN_ID = 7346983056 
TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TOKEN")
GH_TOKEN = os.getenv("GH_TOKEN")
REPO_NAME = "NgDanhThanhTrung/locket_"
PORT = int(os.getenv("PORT", "8000"))
CONTACT_URL = "https://t.me/NgDanhThanhTrung"
DONATE_URL = "https://ngdanhthanhtrung.github.io/Bank/"
KOYEB_URL = "https://colourful-carilyn-ngdanhthanhtrung-1cfbab15.koyeb.app/"
VN_TZ = timezone(timedelta(hours=7))
logging.basicConfig(level=logging.INFO)
DB_PATH = "data_system.db"
# --- DATABASE SETUP ---
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
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
# --- HELPERS ---
def is_admin(user_id: int) -> bool:
    if int(user_id) == int(ROOT_ADMIN_ID): return True
    with sqlite3.connect(DB_PATH) as conn:
        res = conn.execute("SELECT 1 FROM admins WHERE user_id = ?", (str(user_id),)).fetchone()
        return res is not None
async def is_premium(user_id: int) -> bool:
    """Kiểm tra xem người dùng có phải Premium không"""
    with sqlite3.connect(DB_PATH) as conn:
        res = conn.execute("SELECT is_premium FROM users WHERE user_id = ?", (str(user_id),)).fetchone()
        return res is not None and res[0] == 1
async def check_premium_permission(u: Update):
    """Kiểm tra và thông báo nếu người dùng không có quyền Premium"""
    if await is_premium(u.effective_user.id) or is_admin(u.effective_user.id):
        return True
    txt = (
        "⚠️ <b>TÍNH NĂNG GIỚI HẠN</b>\n\n"
        "Tính năng tạo Module cá nhân hóa yêu cầu tài khoản <b>Premium</b>.\n"
        "Vui lòng liên hệ Admin hoặc nhấn nút Donate để nâng cấp."
    )
    kb = [[InlineKeyboardButton("💰 Donate nâng cấp", callback_data="donate_info")],
          [InlineKeyboardButton("💬 Liên hệ Admin", url=CONTACT_URL)]]
    await send_ui(u, txt, kb)
    return False
async def add_admin_db(user_id: str):
    """Thêm admin mới vào database"""
    now = datetime.now(VN_TZ).strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("INSERT OR REPLACE INTO admins (user_id, added_at) VALUES (?, ?)", (user_id, now))
        conn.commit()
async def db_auto_reg(u: Update, c: ContextTypes.DEFAULT_TYPE = None):
    user = u.effective_user
    if not user or user.is_bot: return
    uid, uname, fname = str(user.id), (f"@{user.username}" if user.username else "N/A"), user.full_name
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
async def send_ui(u: Update, text: str, kb: list):
    """Sửa tin nhắn cũ để tạo hiệu ứng chuyển trang, bật xem trước link Web"""
    reply_markup = InlineKeyboardMarkup(kb)
    if u.callback_query:
        try:
            await u.callback_query.edit_message_text(
                text, 
                parse_mode=ParseMode.HTML, 
                reply_markup=reply_markup, 
                disable_web_page_preview=False
            )
        except:
            await u.effective_message.reply_text(
                text, 
                parse_mode=ParseMode.HTML, 
                reply_markup=reply_markup, 
                disable_web_page_preview=False
            )
    else:
        await u.effective_message.reply_text(
            text, 
            parse_mode=ParseMode.HTML, 
            reply_markup=reply_markup, 
            disable_web_page_preview=False
        )
# --- TEMPLATES ---
JS_TEMPLATE = """const mapping = {{ '%E8%BD%A6%E7%A5%A8%E7%A5%A8': ['vip', 'watch_vip'], 'Locket': ['Gold', 'com.{user}.premium.yearly'] }};
const ua = $request.headers["User-Agent"] || $request.headers["user-agent"];
let obj = JSON.parse($response.body);
obj.subscriber = obj.subscriber || {{}};
obj.subscriber.entitlements = obj.subscriber.entitlements || {{}};
obj.subscriber.subscriptions = obj.subscriber.subscriptions || {{}};
const pInfo = {{ is_sandbox: false, ownership_type: "PURCHASED", expires_date: "2999-12-18T01:04:17Z", purchase_date: "{date}T01:04:17Z", store: "app_store" }};
const eInfo = {{ purchase_date: "{date}T01:04:17Z", product_identifier: "com.{user}.premium.yearly", expires_date: "2999-12-18T01:04:17Z" }};
const match = Object.keys(mapping).find(e => ua.includes(e));
if (match) {{
  let [entKey, subKey] = mapping[match];
  let finalSubKey = subKey || "com.{user}.premium.yearly";
  eInfo.product_identifier = finalSubKey;
  obj.subscriber.subscriptions[finalSubKey] = pInfo;
  obj.subscriber.entitlements[entKey] = eInfo;
}} else {{
  obj.subscriber.subscriptions["com.{user}.premium.yearly"] = pInfo;
  obj.subscriber.entitlements["Gold"] = eInfo;
}}
$done({{ body: JSON.stringify(obj) }});"""
MODULE_TEMPLATE = """#!name=Locket-Gold ({user})
#!desc=Crack By NgDanhThanhTrung
[Script]
revenuecat = type=http-response, pattern=^https:\\/\\/api\\.revenuecat\\.com\\/.+\\/(receipts$|subscribers\\/[^/]+$), script-path={js_url}, requires-body=true, max-size=-1, timeout=60
deleteHeader = type=http-request, pattern=^https:\\/\\/api\\.revenuecat\\.com\\/.+\\/(receipts|subscribers), script-path=https://raw.githubusercontent.com/NgDanhThanhTrung/locket_/main/Locket_NDTT/deleteHeader.js, timeout=60
[MITM]
hostname = %APPEND% api.revenuecat.com"""
NEXTDNS_CONFIG = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict><key>PayloadContent</key><array><dict><key>DNSSettings</key><dict><key>DNSProtocol</key><string>HTTPS</string><key>ServerURL</key><string>https://apple.nextdns.io/{dns_id}</string></dict><key>PayloadIdentifier</key><string>com.nextdns.dns.{dns_id}</string><key>PayloadType</key><string>com.apple.dnsSettings.managed</string><key>PayloadUUID</key><string>{uuid1}</string><key>PayloadVersion</key><integer>1</integer></dict></array><key>PayloadDisplayName</key><string>NextDNS ({dns_id})</string><key>PayloadIdentifier</key><string>com.nextdns.config.{dns_id}</string><key>PayloadType</key><string>Configuration</string><key>PayloadUUID</key><string>{uuid2}</string><key>PayloadVersion</key><integer>1</integer></dict></plist>"""
# --- HANDLERS ---
async def start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    txt = (
        f"👋 Chào mừng <b>{u.effective_user.first_name}</b> đến với <b>@NgDanhThanhTrung_BOT</b>!\n\n"
        f"🚀 <b>Tính năng chính:</b>\n"
        f"🔹 Hỗ trợ tạo Module Shadowrocket cá nhân hóa.\n"
        f"🔹 Tự động kích hoạt script Locket Gold vĩnh viễn.\n"
        f"🔹 Dashboard Web mượt mà, dễ sử dụng.\n\n"
        f"🌐 <b>Web Dashboard:</b>\n"
        f"<code>{KOYEB_URL}</code>\n\n"
        f"📝 <b>Hướng dẫn:</b>\n"
        f"• Nhấn nút <b>Danh sách Module</b> bên dưới để xem script.\n"
        f"• Gõ <code>/get Tên | Ngày</code> để tạo script riêng.\n"
        f"• Gõ /hdsd để xem cách cài đặt <b>HTTPS Decryption</b>.\n\n"
        f"👨‍💻 <b>Admin:</b> @NgDanhThanhTrung"
    )
    kb = [[InlineKeyboardButton("📂 Danh sách Module", callback_data="show_list")],
          [InlineKeyboardButton("👤 Hồ sơ", callback_data="profile"), InlineKeyboardButton("💰 Donate", callback_data="donate_info")],
          [InlineKeyboardButton("📖 HDSD", callback_data="hdsd"), InlineKeyboardButton("💬 Liên hệ Admin", url=CONTACT_URL)]]
    await send_ui(u, txt, kb)
async def send_mail_to_admin(u: Update, c: ContextTypes.DEFAULT_TYPE):
    user = u.effective_user
    if not c.args:
        return await u.message.reply_text("⚠️ <b>Cú pháp:</b> <code>/sendmail [Nội dung yêu cầu]</code>", parse_mode=ParseMode.HTML)
    user_msg = " ".join(c.args)
    kb_admin = [[InlineKeyboardButton("✅ THÀNH CÔNG", callback_data=f"done_req_{user.id}")]]
    report_to_admin = (
        "📨 <b>YÊU CẦU HỖ TRỢ DNS</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>Người gửi:</b> {user.full_name}\n"
        f"🆔 <b>ID:</b> <code>{user.id}</code>\n"
        f"📝 <b>Nội dung:</b> {user_msg}"
    )
    try:
        await c.bot.send_message(ROOT_ADMIN_ID, report_to_admin, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(kb_admin))
        text_user = (
            "✅ <b>Đã gửi thông tin tới Admin!</b>\n\n"
            "Vui lòng chờ một thời gian để Admin chỉnh sửa DNS hộ bạn. "
            "Tới khi có thông báo trả về, bạn hãy dùng lệnh <code>/nextdns</code> kèm với ID DNS sẽ được Admin gửi về."
        )
        await u.message.reply_text(text_user, parse_mode=ParseMode.HTML)
    except Exception as e:
        await u.message.reply_text(f"❌ Lỗi gửi tin nhắn: {str(e)}")
async def done_dns_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id): return
    if not c.args or "|" not in " ".join(c.args):
        return await u.message.reply_text("⚠️ <b>Cú pháp:</b> <code>/donedns [ID User] | [ID DNS]</code>", parse_mode=ParseMode.HTML)
    try:
        parts = [p.strip() for p in " ".join(c.args).split("|")]
        target_id = parts[0]
        dns_id = parts[1]
        msg_to_user = (
            "🎉 <b>THÔNG BÁO: DNS ĐÃ SẴN SÀNG!</b>\n\n"
            "Admin đã hoàn tất việc chỉnh sửa DNS cho bạn.\n"
            f"🆔 ID DNS của bạn là: <code>{dns_id}</code>\n\n"
            f"👉 Bây giờ bạn có thể dùng lệnh: <code>/nextdns {dns_id}</code> để cấu hình."
        )
        await c.bot.send_message(target_id, msg_to_user, parse_mode=ParseMode.HTML)
        await u.message.reply_text(f"✅ Đã gửi ID DNS <code>{dns_id}</code> tới người dùng <code>{target_id}</code> thành công!")
    except Exception as e:
        await u.message.reply_text(f"❌ Không thể gửi tin nhắn cho người dùng: {str(e)}")
async def callback_handler(u: Update, c: ContextTypes.DEFAULT_TYPE):
    query = u.callback_query
    await query.answer()
    data = query.data
    if data == "show_list":
        await send_module_list(u, c)
    elif data.startswith("list_page_"):
        page_num = int(data.split("_")[-1])
        await send_module_list(u, c, page=page_num)
    elif data == "profile":
        await profile(u, c)
    elif data == "donate_info":
        await donate_info(u, c)
    elif data == "back_start":
        await start(u, c)
    elif data == "hdsd":
        await hdsd_ui(u, c)
    elif data.startswith("done_req_"):
        target_uid = data.split("_")[-1]
        await c.bot.send_message(
            chat_id=ROOT_ADMIN_ID,
            text=(
                f"📩 <b>TIẾN HÀNH TRẢ KẾT QUẢ</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"👤 Người dùng: <code>{target_uid}</code>\n\n"
                f"Hãy dùng lệnh dưới đây để gửi mã DNS cho họ:\n"
                f"<code>/donedns {target_uid} | [MÃ_DNS_TẠI_ĐÂY]</code>"
            ),
            parse_mode=ParseMode.HTML
        )
async def send_feedback(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not c.args:
        return await u.message.reply_text("⚠️ Cú pháp: `/send [nội dung góp ý/báo lỗi]`")
    user = u.effective_user
    text = " ".join(c.args)
    report = (f"🆘 <b>YÊU CẦU HỖ TRỢ</b>\n"
              f"Người gửi: {user.full_name} (<code>{user.id}</code>)\n"
              f"Nội dung: {text}")
    await c.bot.send_message(ROOT_ADMIN_ID, report, parse_mode=ParseMode.HTML)
    await u.message.reply_text("✅ Đã gửi báo cáo đến Admin. Chúng tôi sẽ phản hồi sớm nhất!")
async def profile(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = str(u.effective_user.id)
    with sqlite3.connect(DB_PATH) as conn:
        user = conn.execute("SELECT join_date, interact_count, is_premium, last_active FROM users WHERE user_id = ?", (uid,)).fetchone()
    if not user: return await u.effective_message.reply_text("❌ Không tìm thấy dữ liệu.")
    status = "💎 Premium" if user[2] == 1 else "🆓 Thành viên"
    txt = (f"👤 <b>HỒ SƠ CỦA BẠN</b>\n\n🆔 ID: <code>{uid}</code>\n📅 Tham gia: {user[0]}\n"
           f"⚡ Tương tác: {user[1]} lần\n🕒 Cuối: {user[3]}\n🌟 Trạng thái: <b>{status}</b>")
    kb = [[InlineKeyboardButton("🔙 Quay lại", callback_data="back_start")]]
    await send_ui(u, txt, kb)
async def donate_info(u: Update, c: ContextTypes.DEFAULT_TYPE):
    txt = ("💰 <b>ỦNG HỘ PHÁT TRIỂN (DONATE)</b>\n\n"
           "Nếu bạn thấy hệ thống hữu ích, hãy mời Admin một ly cà phê nhé!\n"
           "Mọi sự ủng hộ đều giúp hệ thống duy trì ổn định hơn. ❤️")
    kb = [[InlineKeyboardButton("💳 Ngân hàng ", url=DONATE_URL)],
          [InlineKeyboardButton("🔙 Quay lại", callback_data="back_start")]]
    await send_ui(u, txt, kb)
async def get_bundle(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not c.args or "|" not in " ".join(c.args): 
        return await u.message.reply_text(
            "⚠️ <b>Cú pháp:</b> <code>/get username locket | yyyy-mm-dd</code>\n"
            "Ví dụ: <code>/get ngdanhthanhtrung | 2026-01-01</code>", 
            parse_mode=ParseMode.HTML
        )
    full_text = " ".join(c.args)
    parts = [p.strip() for p in full_text.split("|")]
    raw_username = parts[0]
    safe_user = "".join(x for x in raw_username if x.isalnum())
    if not safe_user:
        return await u.message.reply_text("❌ Username không hợp lệ (vui lòng chỉ dùng chữ và số).")
    try:
        raw_date = parts[1].replace("/", "-").replace(".", "-")
        date_obj = datetime.strptime(raw_date, "%Y-%m-%d")
        date_str = date_obj.strftime("%Y-%m-%d")
    except (ValueError, IndexError):
        return await u.message.reply_text(
            "❌ Ngày không hợp lệ!\nĐịnh dạng đúng: <code>Năm-Tháng-Ngày</code> (VD: 2026-04-17)", 
            parse_mode=ParseMode.HTML
        )
    status = await u.message.reply_text("⏳ <b>Đang khởi tạo Module cá nhân...</b>", parse_mode=ParseMode.HTML)
    try:
        repo = Github(GH_TOKEN).get_repo(REPO_NAME)
        js_p, mod_p = f"{safe_user}/LocketGold.js", f"{safe_user}/LocketGold.sgmodule"
        js_url = f"https://raw.githubusercontent.com/{REPO_NAME}/main/{js_p}"
        js_c = JS_TEMPLATE.format(user=safe_user, date=date_str)
        mod_c = MODULE_TEMPLATE.format(user=raw_username, js_url=js_url)
        for p, cnt in [(js_p, js_c), (mod_p, mod_c)]:
            try:
                f = repo.get_contents(p)
                repo.update_file(p, f"Update module: {safe_user}", cnt, f.sha)
            except:
                repo.create_file(p, f"Create module: {safe_user}", cnt)
        await status.edit_text(
            f"✅ <b>TẠO MODULE THÀNH CÔNG!</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>Username:</b> <code>{raw_username}</code>\n"
            f"📅 <b>Ngày tham gia:</b> <code>{date_str}</code>\n\n"
            f"🔗 <b>Link Module của bạn:</b>\n"
            f"<code>https://raw.githubusercontent.com/{REPO_NAME}/main/{mod_p}</code>\n\n"
            f"💖 Nếu thấy hữu ích, hãy ủng hộ Admin tại /donate nhé!", 
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logging.error(f"GitHub Error: {str(e)}")
        await status.edit_text(f"❌ Lỗi kết nối GitHub: <code>{str(e)}</code>", parse_mode=ParseMode.HTML)
async def get_nextdns(u: Update, c: ContextTypes.DEFAULT_TYPE):
    try:
        await db_auto_reg(u, c)
        if not c.args:
            guide = (
                "🌐 <b>HƯỚNG DẪN CẤU HÌNH NEXTDNS</b>\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                "1️⃣ Truy cập <a href='https://my.nextdns.io'>my.nextdns.io</a> để tạo tài khoản.\n"
                "2️⃣ Đặt mật khẩu là <code>12345678</code> nếu cần Admin hỗ trợ.\n"
                "3️⃣ Gõ <code>/sendmail [Email]</code> để báo Admin chỉnh cấu hình.\n"
                "4️⃣ Lấy <b>ID</b> (6 ký tự) tại tab Setup.\n\n"
                "👉 <b>Cú pháp lấy mã:</b> <code>/nextdns [ID_CỦA_BẠN]</code>"
            )
            return await u.message.reply_text(
                guide, 
                parse_mode=ParseMode.HTML, 
                disable_web_page_preview=True
            )
        dns_id = c.args[0].strip()
        status = await u.message.reply_text("⏳ <b>Đang khởi tạo cấu hình...</b>", parse_mode=ParseMode.HTML)
        xml_content = NEXTDNS_CONFIG.format(
            dns_id=dns_id,
            uuid1=str(uuid.uuid4()),
            uuid2=str(uuid.uuid4())
        )
        shortcut_url = "https://www.icloud.com/shortcuts/ef6f685318484784940648ad520b5c4f"
        kb = [
            [InlineKeyboardButton("⚡ Cài qua Shortcuts (iOS)", url=shortcut_url)],
            [InlineKeyboardButton("🔙 Quay lại", callback_data="back_start"), 
             InlineKeyboardButton("💬 Hỗ trợ", url=CONTACT_URL)]
        ]
        safe_xml = html.escape(xml_content)
        msg_text = (
            f"✅ <b>NEXTDNS CỦA BẠN ĐÃ SẴN SÀNG!</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🆔 ID DNS: <code>{dns_id}</code>\n\n"
            f"🛠 <b>CÁCH CÀI ĐẶT NHANH:</b>\n"
            f"1. Nhấn nút <b>⚡ Cài qua Shortcuts</b> để tải phím tắt.\n"
            f"2. Chạm vào mã bên dưới để <b>Copy</b>.\n"
            f"3. Dán mã vào <b>Ghi chú (Notes)</b>.\n"
            f"4. Nhấn <b>Chia sẻ</b> ➔ Chọn phím tắt <b>NextDNS</b>.\n\n"
            f"📋 <b>MÃ XML (CHẠM ĐỂ SAO CHÉP):</b>\n"
            f"<pre>{safe_xml}</pre>"
        )
        await u.message.reply_text(
            msg_text, 
            parse_mode=ParseMode.HTML, 
            reply_markup=InlineKeyboardMarkup(kb)
        )
        await status.delete()
    except Exception as e:
        logging.error(f"Lỗi NextDNS: {e}")
        error_txt = f"❌ <b>Lỗi hệ thống:</b> <code>{str(e)}</code>"
        if 'status' in locals():
            await status.edit_text(error_txt, parse_mode=ParseMode.HTML)
        else:
            await u.message.reply_text(error_txt, parse_mode=ParseMode.HTML)
# --- ADMIN FUNCTIONS ---
async def admin_panel(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id): 
        return
    txt = (
        "🛠 <b>BẢNG ĐIỀU KHIỂN QUẢN TRỊ VIÊN</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "📊 <b>Thống kê & Hệ thống:</b>\n"
        "• <code>/stats</code>: Xem tổng User, Premium và Modules.\n"
        "• <code>/saoluu</code>: Xuất file Excel backup toàn bộ dữ liệu.\n"
        "• <code>/broadcast [nội dung]</code>: Gửi thông báo tới toàn bộ người dùng.\n\n"
        "👤 <b>Quản lý Người dùng:</b>\n"
        "• <code>/approve [ID]</code>: Cấp quyền <b>Premium</b> cho người dùng.\n"
        "• <code>/revoke [ID]</code>: Thu hồi quyền Premium.\n"
        "• <code>/addadmin [ID]</code>: Cấp quyền <b>Admin</b> (Chỉ Root Admin).\n\n"
        "📦 <b>Quản lý Modules:</b>\n"
        "• <code>/setlink key | title | url</code>: Thêm/Sửa module.\n"
        "• <code>/delmodule [key]</code>: Xóa module khỏi hệ thống.\n\n"   
        "💡 <i>Mẹo: Nhấn vào ID người dùng trong danh sách Module để copy nhanh.</i>"
    )
    kb = [
        [InlineKeyboardButton("📂 Danh sách & Quản lý User", callback_data="show_list")],
        [InlineKeyboardButton("🔙 Quay lại trang chủ", callback_data="back_start")]
    ]
    await send_ui(u, txt, kb)
async def revoke_user(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id) or not c.args: return
    uid = c.args[0]
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE users SET is_premium = 0 WHERE user_id = ?", (uid,))
        conn.commit()
    await u.message.reply_text(f"🚫 Đã thu hồi quyền Premium của ID: {uid}")    
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
    await u.message.reply_text(f"✅ Đã cấp quyền Premium cho ID: <code>{uid}</code>", parse_mode=ParseMode.HTML)
    try: 
        await c.bot.send_message(uid, "🎉 Chúc mừng! Tài khoản của bạn đã được nâng cấp lên <b>Premium</b>!", parse_mode=ParseMode.HTML)
    except: 
        await u.message.reply_text("⚠️ Đã duyệt DB nhưng không thể gửi tin nhắn cho User (có thể họ đã block bot).")
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
async def set_admin_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    """Lệnh cấp quyền Admin (Chỉ Root Admin ID mới dùng được)"""
    if u.effective_user.id != ROOT_ADMIN_ID:
        return
    if not c.args:
        return await u.message.reply_text("⚠️ Cú pháp: `/addadmin ID`")
    target_id = c.args[0]
    await add_admin_db(target_id)
    await u.message.reply_text(f"✅ Đã cấp quyền Admin cho ID: <code>{target_id}</code>", parse_mode=ParseMode.HTML)
# --- LIST & CALLBACKS ---
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
            users = conn.execute("""
                SELECT user_id, full_name, join_date, interact_count, is_premium 
                FROM users ORDER BY last_active DESC LIMIT ? OFFSET ?
            """, (per_page, offset)).fetchall()
            txt += f"\n\n👑 <b>QUẢN LÝ THÀNH VIÊN ({page}/{total_pages})</b>"
            for us in users:
                status = "💎" if us[4] else "🆓"
                txt += (f"\n\n👤 <b>{us[1]}</b> (<code>{us[0]}</code>)\n"
                        f"📅 Join: {us[2]} | ⚡ Lần: {us[3]} | {status}")
            nav = []
            if page > 1: nav.append(InlineKeyboardButton("⬅️ Trước", callback_data=f"list_page_{page-1}"))
            if page < total_pages: nav.append(InlineKeyboardButton("Sau ➡️", callback_data=f"list_page_{page+1}"))
            if nav: kb.append(nav)
    kb.append([InlineKeyboardButton("👤 Hồ sơ của tôi", callback_data="profile")])
    kb.append([InlineKeyboardButton("🔙 Quay lại trang chủ", callback_data="back_start")])
    await send_ui(u, txt, kb)
async def hdsd_ui(u: Update, c: ContextTypes.DEFAULT_TYPE):
    txt = (
        "📖 <b>HƯỚNG DẪN SỬ DỤNG:</b>\n\n"
        "🔹 <b>MODULE CÓ SẴN:</b>\n"
        "Nhấn nút 'Danh sách Module' hoặc gõ /list.\n"
        "Sau đó gõ <code>/[tên_module]</code> để lấy link.\n\n"
        "🔹 <b>TẠO MODULE LOCKET RIÊNG:</b>\n"
        "Cú pháp: <code>/get tên_user | yyyy-mm-dd</code>\n"
        "<i>Ví dụ: /get ndtt | 2025-01-16</i>"
    )
    kb = [[InlineKeyboardButton("🔙 Quay lại", callback_data="back_start")]]
    await send_ui(u, txt, kb)
async def callback_handler(u: Update, c: ContextTypes.DEFAULT_TYPE):
    query = u.callback_query; await query.answer()
    if query.data == "show_list": await send_module_list(u, c)
    elif query.data.startswith("list_page_"): await send_module_list(u, c, page=int(query.data.split("_")[-1]))
    elif query.data == "profile": await profile(u, c)
    elif query.data == "donate_info": await donate_info(u, c)
    elif query.data == "back_start": await start(u, c)
    elif query.data == "hdsd": await hdsd_ui(u, c)
async def dynamic_module_handler(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not u.message or not u.message.text or not u.message.text.startswith('/'):
        return
    cmd = u.message.text.split()[0][1:].split('@')[0].lower()
    sys_cmds = ['start', 'profile', 'list', 'get', 'nextdns', 'donate', 'admin', 'stats', 'sendmail', 'donedns', 'saoluu', 'approve', 'send', 'revoke', 'broadcast', 'setlink', 'delmodule', 'addadmin', 'hdsd']
    if cmd in sys_cmds:
        return
    try:
        with sqlite3.connect(DB_PATH) as conn:
            res = conn.execute("SELECT title, url FROM modules WHERE key = ?", (cmd,)).fetchone()
        if res:
            title, url = res
            txt = (
                f"📦 <b>MODULE: {title.upper()}</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n\n"
                f"🔗 <b>ĐƯỜNG DẪN CÀI ĐẶT:</b>\n"
                f"<code>{url}</code>\n\n"
                f"🛠 <b>HƯỚNG DẪN CHI TIẾT:</b>\n"
                f"1️⃣ <b>Sao chép:</b> Chạm vào dòng link phía trên để tự động copy.\n"
                f"2️⃣ <b>Thêm Module:</b> Mở Shadowrocket/Surge/QuantumultX ➔ Tìm mục <b>Module</b> ➔ Chọn <b>Add Module</b>.\n"
                f"3️⃣ <b>Dán & Lưu:</b> Dán link đã copy vào và nhấn lưu lại.\n"
                f"4️⃣ <b>HTTPS Decryption:</b> Phải đảm bảo mục <b>MITM</b> đã được cài đặt chứng chỉ và đang ở trạng thái <b>Bật (ON)</b> thì script mới có hiệu lực.\n\n"
                f"💡 <i>Lưu ý: Nếu bạn chưa cài chứng chỉ CA, hãy gõ /hdsd để xem cách làm.</i>"
            )
            kb = [[InlineKeyboardButton(f"📥 Cài đặt {title}", url=url)], [InlineKeyboardButton("🔙 Quay lại danh sách", callback_data="show_list")]]
            await u.message.reply_text(text=txt, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(kb), disable_web_page_preview=True)
        elif u.effective_chat.type == "private":
            not_found_txt = f"🔍 <b>Không tìm thấy Module:</b> <code>/{cmd}</code>\n\nVui lòng kiểm tra lại hoặc nhấn nút dưới đây để xem danh sách Module hiện có."
            kb = [[InlineKeyboardButton("📂 Xem danh sách Module", callback_data="show_list")]]
            await u.message.reply_text(text=not_found_txt, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(kb))
    except Exception as e:
        logging.error(f"Error in dynamic_handler: {e}")
        
# --- WEB SERVER ---
server = Flask(__name__)
@server.route('/')
def index():
    return render_template('index.html')
async def post_init(application):
    await application.bot.set_my_commands([
        BotCommand("start", "🏠 Bắt đầu"), 
        BotCommand("profile", "👤 Hồ sơ"),
        BotCommand("list", "📂 Danh sách Modules"), 
        BotCommand("get", "✨ Tạo Locket Gold"),
        BotCommand("nextdns", "🌐 Tạo Config NextDNS"), 
        BotCommand("send", "🆘 Báo lỗi/Góp ý"),
        BotCommand("sendmail", "📧 Gửi yêu cầu chỉnh DNS"),
        BotCommand("donate", "💰 Donate ủng hộ Admin"),
        BotCommand("admin", "🛠 Menu Admin")
    ])    
# --- MAIN ---
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
    app.add_handler(CommandHandler("sendmail", send_mail_to_admin))
    app.add_handler(CommandHandler("donedns", done_dns_cmd))
    app.add_handler(CommandHandler("saoluu", backup_data))
    app.add_handler(CommandHandler("approve", approve_user))
    app.add_handler(CommandHandler("send", send_feedback))
    app.add_handler(CommandHandler("revoke", revoke_user))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("setlink", set_link))
    app.add_handler(CommandHandler("delmodule", del_mod))
    app.add_handler(CommandHandler("addadmin", set_admin_cmd))
    app.add_handler(CommandHandler("hdsd", hdsd_ui))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.COMMAND, dynamic_module_handler))
    app.run_polling(drop_pending_updates=True)
