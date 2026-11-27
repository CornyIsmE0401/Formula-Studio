@echo off
chcp 65001 >nul
echo === Cai thu vien cho Formula Studio ===
python -m pip install --upgrade pip
python -m pip install PySide6 matplotlib
echo.
echo Xong! Chay ung dung bang run.bat (hoac: python main.py)
pause
