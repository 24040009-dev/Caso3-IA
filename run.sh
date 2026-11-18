#!/usr/bin/env bash
# Crea un entorno virtual, instala las librerías y abre la aplicación.
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
