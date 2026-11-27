@echo off
chcp 65001 >nul
echo === Tao moi truong Python 3.12 rieng de dung quet anh OFFLINE (rapid-latex-ocr) ===
echo Can cai Python 3.12 truoc (https://www.python.org/downloads/release/python-3120/ , nho tick "py launcher").
py -3.12 -m venv venv312
if errorlevel 1 (
  echo Khong tim thay Python 3.12. Hay cai Python 3.12 roi chay lai.
  pause
  exit /b 1
)
call venv312\Scripts\activate
python -m pip install --upgrade pip
python -m pip install PySide6 matplotlib rapid-latex-ocr
echo.
echo Xong! Tu nay chay ung dung bang: run_py312.bat
pause
