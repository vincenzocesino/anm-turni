@echo off
cd /d "%~dp0"
echo Avvio ANM Turni...
python -m streamlit run app.py --server.port 8501 --browser.gatherUsageStats false
pause
