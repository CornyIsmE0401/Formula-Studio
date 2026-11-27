@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
echo ============================================================
echo   DONG GOI Formula Studio THANH FILE .EXE
echo   (chay:  build_exe.bat           -> mot file .exe duy nhat, khong co _internal)
echo   (chay:  build_exe.bat folder    -> dang thu muc, mo nhanh hon)
echo ============================================================

rem PyInstaller thuong chua ho tro Python moi nhat (vd 3.15) -> uu tien 3.12 / 3.13 / 3.11 de dong goi
set PYCMD=
for %%V in (3.12 3.13 3.11) do (
  if not defined PYCMD (
    py -%%V -c "import sys" >nul 2>&1 && set PYCMD=py -%%V
  )
)
if not defined PYCMD set PYCMD=python
echo Dang dung: %PYCMD%
%PYCMD% --version

%PYCMD% -m venv build_venv
if errorlevel 1 goto :fail
call build_venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install PySide6 matplotlib pyinstaller pywin32
if errorlevel 1 goto :fail

set MODE=--onefile
if /i "%1"=="folder" set MODE=--onedir

pyinstaller --noconfirm --clean --windowed %MODE% --name FormulaStudio --icon app.ico --add-data "app.ico;." --add-data "assets;assets" ^
  --exclude-module rdkit --exclude-module tkinter --exclude-module scipy ^
  --hidden-import win32com.client --hidden-import pythoncom main.py
if errorlevel 1 goto :fail

echo.
echo === Tu kiem tra ban dong goi ===
if /i "%1"=="folder" (
  dist\FormulaStudio\FormulaStudio.exe --selftest
) else (
  dist\FormulaStudio.exe --selftest
)
if exist selftest_result.txt type selftest_result.txt

echo.
if /i "%1"=="folder" (
  echo XONG!  Thu muc: dist\FormulaStudio\   ^(chay FormulaStudio.exe trong do; nen zip de gui nguoi khac^)
) else (
  echo XONG!  File duy nhat: dist\FormulaStudio.exe   ^(gui file nay cho khach^)
)
pause
exit /b 0

:fail
echo.
echo *** LOI. Neu bao khong ho tro Python hien tai: hay cai Python 3.12 (python.org) roi chay lai build_exe.bat ***
pause
exit /b 1
