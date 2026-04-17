# 🤖 Telegram Locket & DNS Bot: Web-to-Bot Automation — Edition 2026

### 🛠 Phát triển bởi: [NgDanhThanhTrung](https://github.com/NgDanhThanhTrung)

![Tác giả](https://img.shields.io/badge/Author-NgDanhThanhTrung-blue?style=for-the-badge&logo=telegram)
![Ngôn ngữ](https://img.shields.io/badge/Language-Python-yellow?style=for-the-badge&logo=python)
![Trạng thái](https://img.shields.io/badge/Status-Active-brightgreen?style=for-the-badge)
![Giao diện](https://img.shields.io/badge/UI-Modern_Dashboard-indigo?style=for-the-badge)
![Deploy](https://img.shields.io/badge/Deploy-Koyeb-blueviolet?style=for-the-badge&logo=koyeb)

Dự án này là một giải pháp tự động hóa đa nhiệm được nghiên cứu và phát triển độc quyền bởi **NgDanhThanhTrung**. Hệ thống vận hành trên nền tảng Koyeb, kết hợp Telegram Bot và GitHub API để quản lý DNS và Module Locket Gold cá nhân hóa.

---

## 💡 Bản Quyền & Chất Xám Tác Giả
Đây là sản phẩm trí tuệ dựa trên kinh nghiệm tối ưu hóa quy trình tương tác API và tự động hóa của **NgDanhThanhTrung**. 

> **⚡ Thông điệp từ tác giả:**
> "Mã nguồn này được chia sẻ với mục đích học tập và hỗ trợ cộng đồng. Tôi hy vọng bạn sẽ tôn trọng chất xám của tôi bằng cách giữ nguyên ghi chú bản quyền và không sử dụng cho các mục đích thương mại trái phép."

---

## 🛠 Nguyên lý hoạt động (Cloud Architecture)

Hệ thống hoạt động dựa trên cơ chế song song (**Multi-threading**) để tối ưu hóa hiệu suất:

1.  **Telegram Bot**: Xử lý các lệnh từ người dùng theo thời gian thực (Long Polling).
2.  **Web Service (Flask)**: Duy trì trạng thái trực tuyến trên Koyeb qua cổng `8000` và cung cấp Dashboard.
3.  **GitHub API**: Tự động thực hiện commit/update các file cấu hình trực tiếp vào repository cá nhân.
4.  **Database Management**: Sử dụng SQLite với chế độ `WAL` giúp ghi dữ liệu đồng thời mà không gây lỗi khóa (Lock).

---

## ⚙️ Hướng dẫn Chỉnh sửa & Tùy biến (Trong code)

Để thay đổi thông tin cá nhân, bạn chỉ cần tìm đến phần `# --- CONFIGURATION ---` trong file `bot.py` và chỉnh sửa các dòng sau:

# --- CÁC BIẾN CÓ THỂ THAY ĐỔI ---

* ROOT_ADMIN_ID = 7346983056              # Thay bằng ID Telegram của bạn
* REPO_NAME = "NgDanhThanhTrung/locket_"  # Thay bằng "Tên_GitHub/Tên_Repo" của bạn
* CONTACT_URL = "https://t.me/NgDanhThanhTrung" 
* DONATE_URL = "https://ngdanhthanhtrung.github.io/Bank/" 
* KOYEB_URL = "https://your-app.koyeb.app/" # URL sau khi deploy lên Koyeb

### Cách thực hiện:
* **Thay đổi Admin**: Sửa số `7346983056` thành ID của bạn (Lấy ID tại @userinfobot).
* **Kết nối GitHub**: Sửa `REPO_NAME` để bot đẩy file script vào đúng kho lưu trữ của bạn (VD: `Username/my-repo`).
* **Cập nhật URL**: Sau khi deploy thành công lên Koyeb, hãy copy URL ứng dụng của bạn dán vào `KOYEB_URL` để các tính năng điều hướng hoạt động chính xác.

---

## 🌟 Tính Năng Nổi Bật (Cập nhật 2026)

* **Modern Dashboard UI**: Giao diện web tối giản, chuyên nghiệp hiển thị trạng thái hệ thống.
* **Locket Gold Factory**: Tự động tạo Module bypass cá nhân hóa cho từng User qua lệnh `/get`.
* **NextDNS Configurator**: Tạo file cấu hình `.mobileconfig` chuẩn Apple cho iOS/macOS.
* **Admin Panel**: Cấp quyền Premium, thống kê User và gửi thông báo toàn hệ thống trực tiếp từ Bot.
* **Cloud Backup**: Xuất toàn bộ cơ sở dữ liệu ra file Excel thông qua lệnh `/saoluu`.

---

## 🚀 Hướng dẫn Triển khai (Koyeb & GitHub)

1.  **GitHub**: Tạo Repository và lấy **GitHub Personal Access Token** (quyền `repo`).
2.  **Koyeb**: Tạo Web Service, kết nối Repo GitHub và thiết lập các **Biến môi trường**:
    * `BOT_TOKEN`: Token lấy từ @BotFather.
    * `GH_TOKEN`: Token GitHub đã tạo ở bước 1.
    * `PORT`: `8000`.
3.  **Vận hành**: Sau khi Deploy, hệ thống sẽ tự động khởi tạo Database và bắt đầu lắng nghe lệnh.

---

## 🎁 Ủng Hộ & Liên Hệ
* **Ủng hộ tác giả**: [Tại đây](https://ngdanhthanhtrung.github.io/Bank/)
* **Telegram Hỗ Trợ**: [@NgDanhThanhTrung](https://t.me/NgDanhThanhTrung)

---

## 📜 Điều Khoản Sử Dụng
© 2026 **NgDanhThanhTrung**. Bảo lưu mọi quyền.
1. Tuyệt đối không xóa hoặc chỉnh sửa thông tin bản quyền của tác giả.
2. Không sử dụng mã nguồn cho các hành vi vi phạm chính sách của Telegram.
3. Tác giả không chịu trách nhiệm về bất kỳ rủi ro nào phát sinh trong quá trình sử dụng.
