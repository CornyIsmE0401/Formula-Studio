@echo off
chcp 65001 >nul
call venv312\Scripts\activate
python main.py
if errorlevel 1 pause
