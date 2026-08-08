@echo off
cd /d "E:\New folder\workpay\main.py"

call venv\Scripts\activate

python -m streamlit run main.py

pause
