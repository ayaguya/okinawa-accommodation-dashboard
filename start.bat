@echo off
chcp 65001 >nul
echo ダッシュボード起動中...
cd /d "%~dp0"
if not exist "venv" (
    echo 仮想環境がありません。setup.batを先に実行してください。
    pause
    exit /b 1
)
call venv\Scripts\activate.bat
streamlit run app\dashboard.py
pause
