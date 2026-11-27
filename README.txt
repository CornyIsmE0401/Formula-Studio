FORMULA STUDIO v1.0  -  ItzMe_Corniizt

Bộ công cụ soạn công thức, vẽ cấu trúc phân tử, dựng hình học và máy tính khoa học. Chạy ngoại tuyến.

CÀI ĐẶT VÀ CHẠY
1. Cài Python 3.10 trở lên (tick "Add Python to PATH").
2. Bấm đúp install.bat để cài thư viện (lần đầu).
3. Bấm đúp run.bat để mở ứng dụng, hoặc chạy:  python main.py

ĐÓNG GÓI THÀNH .EXE (Windows)
- Bấm đúp build_exe.bat (cần Internet lần đầu). Kết quả: một file duy nhất dist\FormulaStudio.exe (không có thư mục _internal).
- Muốn dạng thư mục (mở nhanh hơn): chạy "build_exe.bat folder" -> dist\FormulaStudio\FormulaStudio.exe
- Chạy "FormulaStudio.exe --selftest" để kiểm tra nhanh (kết quả ghi trong selftest_result.txt).

CÁC MODULE
- Toán học: soạn công thức LaTeX (323 mẫu, có phần thay số vào biến), hình học động, đồ thị.
- Hóa học: cân bằng phương trình, trình vẽ cấu trúc, SMILES, bảng tuần hoàn, tra cứu chất.
- Máy tính khoa học: hiển thị biểu thức dạng công thức, kèm công cụ giải toán từng bước.
- Cài đặt: giao diện, hành vi nút đóng (thu nhỏ xuống khay hoặc thoát hẳn), OCR, hướng dẫn.

THƯ VIỆN
Bắt buộc: PySide6, matplotlib. Tùy chọn: rdkit, rapid-latex-ocr, pywin32.
