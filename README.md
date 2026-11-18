# Planeador de inventario por producto (Caso C)

Aplicación en Python (Streamlit) que predice las unidades vendidas de cada producto con una
**regresión lineal múltiple** (aprendizaje supervisado) y calcula cuántas unidades hay que surtir.
Tiene las mismas funciones que la página web.

## Cómo ejecutarla

Descomprime inventario_app.zip y abre una terminal dentro de la carpeta inventario_app.

WINDOWS
Opción rápida

Doble clic en run.bat. Crea el entorno, instala las librerías y abre la app.

Paso a paso (PowerShell)
Revisa Python: python --version (Si no tienes Python, instálalo desde python.org marcando "Add python.exe to PATH".)
Entra a la carpeta: cd $HOME\Downloads\inventario_app
Crea el entorno virtual: python -m venv .venv
Actívalo: .venv\Scripts\Activate.ps1 (Si dice que la ejecución de scripts está deshabilitada, ejecuta una vez: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned) En CMD se activa con: .venv\Scripts\activate.bat
Instala las librerías: python -m pip install --upgrade pip pip install -r requirements.txt
Inicia la app: streamlit run app.py

MAC

Descomprime inventario_app.zip

Paso a paso
Revisa Python: python3 --version
Entra a la carpeta: cd ~/Downloads/inventario_app
Crea el entorno virtual: python3 -m venv .venv
Actívalo: source .venv/bin/activate
Instala las librerías: python -m pip install --upgrade pip pip install -r requirements.txt
Inicia la app: streamlit run app.py
Después de iniciar
La app se abre en el navegador, normalmente en http://localhost:8501.
Si pide un correo la primera vez, deja el campo vacío y presiona Enter.
Para cerrarla, presiona Ctrl + C en la terminal.

## Cómo usarla

1. Sube tu Excel (.xlsx, .xls) o CSV. Una fila por producto, con las columnas
   `precio, en_promocion, publicidad_gastada, fin_de_semana, temporada, unidades_vendidas`.
   Recomendada: `inventario_actual` (si falta, se toma 0 y la app avisa). Opcional: `producto`.
2. Elige un producto en la tabla (clic en la fila) para ver el detalle y probar escenarios.
3. Descarga el Excel con las unidades a surtir de cada producto.

Para probar con el archivo del caso: `datos/caso3_demanda.csv`.

## Archivos

| Archivo | Qué es |
|---|---|
| `app.py` | Interfaz (Streamlit) |
| `modelo.py` | Lógica: lectura de columnas, división 80/20, regresión, métricas, Excel de salida |
| `requirements.txt` | Librerías (streamlit, pandas, numpy, openpyxl, xlrd, xlsxwriter) |
| `tests/test_modelo.py` | Verifica que los resultados coinciden con la página web (`python tests/test_modelo.py`) |
| `datos/caso3_demanda.csv` | Dataset del caso |

## Cómo calcula

- Entrena con 80 % de los productos y mide con el 20 % restante (semilla fija 42): MAE, RMSE y R².
- Surtir = unidades previstas + inventario de seguridad − inventario actual (mínimo 0).
- Inventario de seguridad = nivel de servicio (90 %, 95 % o 99 %) × RMSE de prueba.
