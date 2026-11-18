@echo off
rem Crea un entorno virtual, instala las librerias y abre la aplicacion.
cd /d "%~dp0"
if not exist .venv ( python -m venv .venv )
call .venv\Scripts\activate.bat
pip install -r requirements.txt
streamlit run app.py
pause
