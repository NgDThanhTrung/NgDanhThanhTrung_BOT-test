# 🤖 Telegram Locket & DNS Bot: Web-to-Bot Automation — Edition 2026

### 🛠 Phát triển bởi: [NgDanhThanhTrung](https://github.com/NgDanhThanhTrung)

![Tác giả](https://img.shields.io/badge/Author-NgDanhThanhTrung-blue?style=for-the-badge&logo=telegram)
![Ngôn ngữ](https://img.shields.io/badge/Language-Python-yellow?style=for-the-badge&logo=python)
![Trạng thái](https://img.shields.io/badge/Status-Active-brightgreen?style=for-the-badge)
![Giao diện](https://img.shields.io/badge/UI-Modern_Dashboard-indigo?style=for-the-badge)
![Deploy](https://img.shields.io/badge/Deploy-Koyeb-blueviolet?style=for-the-badge&logo=koyeb)

Dự án này là một hệ thống đa nhiệm được nghiên cứu và phát triển bởi **NgDanhThanhTrung**. Hệ thống vận hành dưới dạng một **Web Service** trên nền tảng Koyeb, kết hợp sức mạnh của Telegram Bot và GitHub API để cung cấp giải pháp quản lý DNS và Module Locket Gold cá nhân hóa.

---

## 💡 Bản Quyền & Chất Xám Tác Giả
Đây là sản phẩm trí tuệ dựa trên kinh nghiệm tối ưu hóa quy trình tương tác API và tự động hóa của **NgDanhThanhTrung**. 

> **⚡ Thông điệp từ tác giả:**
> "Mã nguồn này được chia sẻ với mục đích học tập và hỗ trợ cộng đồng. Tôi hy vọng bạn sẽ tôn trọng chất xám của tôi bằng cách giữ nguyên ghi chú bản quyền và không sử dụng cho các mục đích thương mại trái phép."

---

## 🛠 Nguyên lý hoạt động (Cloud Native)

Hệ thống không chạy theo dạng script đơn lẻ mà vận hành như một thực thể Web chuyên nghiệp:

* **Multi-threading**: Bot xử lý song song các yêu cầu từ Telegram và các yêu cầu từ Web Dashboard, đảm bảo không có độ trễ.
* **Koyeb Web Service**: Flask Server lắng nghe trên cổng `8000` để duy trì trạng thái trực tuyến (Health Check) và phục vụ trang Dashboard.
* **GitHub Integration**: Tự động hóa việc tạo, commit và phân phối file cấu hình (.js, .sgmodule) thông qua GitHub API.
* **Persistent Database**: Sử dụng SQLite với chế độ `WAL` để lưu trữ dữ liệu người dùng và phân quyền Premium ngay trên Cloud.

---

## 🌟 Tính Năng Nổi Bật (Cập nhật 2026)

* **Modern Dashboard UI**: Giao diện web quản trị chuyên nghiệp, cho phép người dùng tương tác và lấy cấu hình trực quan.
* **Locket Gold Personalization**: Tự động tạo Module bypass cho Locket dựa trên Username và thời gian thực của người dùng.
* **NextDNS Unified**: Hỗ trợ tạo file cấu hình `.mobileconfig` chuẩn Apple từ ID NextDNS cá nhân.
* **Premium Management**: Hệ thống quản lý thành viên thông minh, cấp quyền/thu hồi quyền qua ID Telegram.
* **Automated Backup**: Tính năng `/saoluu` giúp Admin xuất toàn bộ dữ liệu ra Excel để lưu trữ an toàn.

---

## 📖 Cách Sử Dụng & Lệnh Bot

### 1. Dành cho Người dùng
* **Lấy Module Locket**: `/get [tên_user] | [yyyy-mm-dd]`
* **Tạo NextDNS**: `/nextdns [ID_DNS]`
* **Thông tin cá nhân**: `/profile` để xem trạng thái Premium và các module đã tạo.
* **Ủng hộ**: `/donate` để xem thông tin hỗ trợ tác giả.

### 2. Dành cho Quản trị viên (Admin)
* **Duyệt Premium**: `/approve [User_ID]`
* **Thu hồi quyền**: `/revoke [User_ID]`
* **Gửi thông báo toàn bộ**: `/broadcast [Nội dung]`
* **Sao lưu hệ thống**: `/saoluu` để nhận file Excel dữ liệu.

---

## 🛠 Hướng Dẫn Triển Khai (Koyeb.com)

1.  **GitHub**: Upload toàn bộ mã nguồn lên Repository (nên để chế độ **Private**).
2.  **Koyeb**: 
    * Tạo **Web Service** mới, kết nối với Repo GitHub.
    * Thiết lập **Environment Variables**:
        - `BOT_TOKEN`: Token lấy từ @BotFather.
        - `GH_TOKEN`: GitHub Personal Access Token (quyền ghi repo).
        - `REPO_NAME`: Repo lưu script (VD: `Username/locket_`).
        - `PORT`: 8000.
3.  **Địa chỉ Web**: Sau khi Deploy, hệ thống sẽ cấp một URL định danh (VD: `https://your-app.koyeb.app`) dùng để truy cập Dashboard.

---

## 🎁 Ủng Hộ & Liên Hệ
* **Ủng hộ tác giả**: [https://ngdanhthanhtrung.github.io/Bank/](https://ngdanhthanhtrung.github.io/Bank/)
* **Telegram Hỗ Trợ**: [@NgDanhThanhTrung](https://t.me/NgDanhThanhTrung)

---

## 📜 Điều Khoản Sử Dụng
© 2026 **NgDanhThanhTrung**. Bảo lưu mọi quyền.
1. Tuyệt đối không xóa hoặc chỉnh sửa thông tin bản quyền của tác giả.
2. Không sử dụng mã nguồn cho hành vi vi phạm chính sách của Telegram.
3. Tác giả không chịu trách nhiệm về bất kỳ rủi ro nào phát sinh trong quá trình sử dụng.
