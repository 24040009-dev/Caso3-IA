# Planeador de inventario por producto (Caso C)

Aplicación en Python (Streamlit) que predice las unidades vendidas de cada producto con una
**regresión lineal múltiple** (aprendizaje supervisado) y calcula cuántas unidades hay que surtir.
Tiene las mismas funciones que la página web.

## Cómo ejecutarla

Requisito: Python 3.10 a 3.13 e internet la primera vez (para instalar las librerías).

- **Windows:** doble clic en `run.bat`
- **Mac / Linux:** `./run.sh`
- **Manual:**
  ```
  python -m venv .venv
  .venv\Scripts\activate        (Mac/Linux: source .venv/bin/activate)
  pip install -r requirements.txt
  streamlit run app.py
  ```
Se abre en el navegador (normalmente http://localhost:8501).

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
