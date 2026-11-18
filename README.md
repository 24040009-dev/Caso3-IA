# Planeador de inventario por producto (Caso C)

Aplicación en Python (Streamlit) que predice las unidades vendidas de cada producto con una
**regresión lineal múltiple** (aprendizaje supervisado) y calcula cuántas unidades hay que surtir.
Tiene las mismas funciones que la página web.

## Cómo ejecutarla

Descomprime `inventario_app.zip` y abre una terminal dentro de la carpeta `inventario_app`.

---

### Windows

#### Opción rápida
Haz doble clic en `run.bat`. Este script crea el entorno virtual, instala las librerías y abre la aplicación automáticamente.

#### Paso a paso (PowerShell)

1. **Revisa tu versión de Python:**
   ```powershell
   python --version
   ```
   > **Nota:** Si no tienes Python, instálalo desde [python.org](https://www.python.org/) asegurándote de marcar la casilla **"Add python.exe to PATH"**.

2. **Entra a la carpeta del proyecto:**
   ```powershell
   cd $HOME\Downloads\inventario_app
   ```

3. **Crea el entorno virtual:**
   ```powershell
   python -m venv .venv
   ```

4. **Activa el entorno virtual:**
   ```powershell
   .venv\Scripts\Activate.ps1
   ```
   > **¿Error de permisos?** Si dice que la ejecución de scripts está deshabilitada, ejecuta este comando una sola vez y vuelve a intentar:
   > ```powershell
   > Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
   > ```
   > *Si utilizas **CMD** en lugar de PowerShell, actívalo con:* `.venv\Scripts\activate.bat`

5. **Instala las librerías:**
   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

6. **Inicia la aplicación:**
   ```powershell
   streamlit run app.py
   ```

---

### Mac

1. **Descomprime** `inventario_app.zip` y abre la Terminal.

2. **Revisa tu versión de Python:**
   ```bash
   python3 --version
   ```

3. **Entra a la carpeta del proyecto:**
   ```bash
   cd ~/Downloads/inventario_app
   ```

4. **Crea el entorno virtual:**
   ```bash
   python3 -m venv .venv
   ```

5. **Activa el entorno virtual:**
   ```bash
   source .venv/bin/activate
   ```

6. **Instala las librerías:**
   ```bash
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

7. **Inicia la aplicación:**
   ```bash
   streamlit run app.py
   ```

---

### 🌐 Después de iniciar

* La aplicación se abrirá en tu navegador, normalmente en `http://localhost:8501`.
* **Primera vez:** Si la terminal te pide un correo electrónico, deja el campo vacío y presiona `Enter`.
* **Para cerrarla:** Presiona `Ctrl + C` en la terminal.

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
