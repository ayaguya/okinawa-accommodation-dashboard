@echo off
chcp 65001 >nul
echo 環境セットアップ中...
cd /d "%~dp0"
python -m venv venv
call venv\Scripts\activate.bat
pip install -r requirements.txt
python scripts\sample_data_generator.py
echo セットアップ完了!
echo start.batでダッシュボードを起動してください。
pause
