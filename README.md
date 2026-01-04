# Tool Reg Account VLCM

Tool tự động đăng ký tài khoản cho game VLCM (Võ Lâm Chi Mộng) Zing Me. Tool tự động giải Captcha hình ảnh và Captcha âm thanh (reCAPTCHA) sử dụng AI.

## Tính Năng
- Đăng ký tự động nhiều luồng (Multi-thread).
- Tự động giải Captcha hình ảnh bằng OCR (TrOCR).
- Tự động giải reCAPTCHA Audio bằng OpenAI Whisper.
- Lưu tài khoản thành công vào `accounts.txt`.
- Cấu hình số lượng và luồng chạy qua file `config.json`.

## Yêu Cầu (Prerequisites)
- **Python 3.10** trở lên.
- **Git** (nếu muốn clone source dễ dàng).

## Hướng Dẫn Cài Đặt trên Windows

### Bước 1: Cài đặt Python
1. Tải Python 3.10+ tại [python.org](https://www.python.org/downloads/).
2. Khi cài đặt, **BẮT BUỘC** tích vào ô **"Add Python to PATH"** ở màn hình đầu tiên.

### Bước 2: Tải Source Code
- Tải file zip hoặc dùng git clone về máy.
- Giải nén ra thư mục (ví dụ: `C:\Users\Admin\vlcm-tool`).
- Mở **Command Prompt (CMD)** hoặc **PowerShell** tại thư mục đó (Giữ Shift + Chuột phải -> Open PowerShell window here).

### Bước 3: Cài đặt Tự Động
Chỉ cần chạy file `setup.py`, tool sẽ tự động cài thư viện và tải trình duyệt:

```bash
python setup.py
```

*Lưu ý: Nếu máy báo thiếu FFmpeg (dùng cho giải Captcha âm thanh), hãy tải ffmpeg bin và thêm vào PATH hoặc để file `ffmpeg.exe` cùng thư mục.*

## Cách Sử Dụng

### Cấu Hình
Mở file `config.json` để chỉnh sửa:
```json
{
    "count": 10,       // Số lượng tài khoản muốn tạo
    "concurrency": 3   // Số luồng chạy cùng lúc (tùy cấu hình máy, nên để 2-3)
}
```

### Chạy Tool
Tại cửa sổ CMD/PowerShell thư mục tool, chạy lệnh:

```bash
python -m src.main
```

Hoặc nếu muốn đè cấu hình:

```bash
python -m src.main --count 50 --concurrency 5
```

## Hướng Dẫn Build File EXE (File Chạy)
Nếu bạn muốn đóng gói tool thành file `.exe` để chạy trên máy khác không cần cài Python:

1.  Chạy lệnh build:
    ```bash
    python build.py
    ```
2.  Đợi quá trình chạy xong (có thể mất vài phút).
3.  Kết quả sẽ nằm trong thư mục `dist/`.
4.  Copy file `dist/VLCM_Reg_Tool.exe` (hoặc `VLCM_Reg_Tool` trên Mac) sang máy khác để chạy.

**Lưu ý quan trọng**:
-   File cài đặt sẽ rất nặng (>2GB) do chứa thư viện AI.
-   **Khởi động lần đầu sẽ chậm** do phải giải nén nội dung ra thư mục tạm.
-   Trên máy mới, bạn **vẫn cần cài trình duyệt** bằng cách chạy `patchright install`.
-   **Cần có FFmpeg**: Để Whisper hoạt động, bạn cần cài đặt FFmpeg hoặc tải file `ffmpeg.exe` và đặt cùng thư mục với `VLCM_Reg_Tool.exe`.
-   Nên để file `config.json` cùng thư mục với file exe để dễ dàng cấu hình.

## Kết Quả
- Tài khoản tạo thành công sẽ được lưu vào file `accounts.txt` theo định dạng `username|password`.
- Nếu có lỗi, ảnh chụp màn hình lỗi sẽ lưu trong thư mục `errors/`.

## Xử Lý Lỗi Thường Gặp
1. **Lỗi `ModuleNotFoundError: No module named ...`**: Chạy lại `pip install -r requirements.txt`.
2. **Lỗi `ffmpeg`**: Tải ffmpeg bin về, giải nén và thêm đường dẫn `bin` vào Environment Variables (PATH).
