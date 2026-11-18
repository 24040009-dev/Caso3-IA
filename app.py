"""Planeador de inventario por producto (interfaz Streamlit).

Ejecutar:  streamlit run app.py
La lógica del modelo está en modelo.py (regresión lineal múltiple, aprendizaje
supervisado). Aquí solo está la interfaz, con las mismas funciones de la página web.
"""
import hashlib
from pathlib import Path

import pandas as pd
import streamlit as st

from modelo import (NIVELES, PLANTILLA_CSV, exportar_excel, js_round, leer_archivo, procesar)

st.set_page_config(page_title="Planeador de inventario por producto", page_icon="📦", layout="wide")
ss = st.session_state
f0 = lambda v: f"{js_round(v):,}"
PREFIJOS = ("p0_", "p1_", "p2_", "p3_", "p4_", "stk_")

st.title("Planeador de inventario por producto")
st.caption("Carga tu propio archivo con los productos de este momento. La página aprende de tus datos, "
           "calcula cuánto surtir de cada producto y te deja descargar un Excel con el resultado.")


def explicacion():
    st.subheader("3. ¿Qué tipo de aprendizaje se usa y por qué?")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Aprendizaje supervisado: regresión**")
        st.markdown("**Supervisado** porque tu archivo ya trae la respuesta correcta (unidades_vendidas) para cada "
                    "ejemplo. El modelo aprende la relación entre las variables y esa respuesta, y luego la aplica "
                    "a casos nuevos.")
        st.markdown("**Regresión** porque lo que se quiere predecir es un número continuo (cuántas unidades), "
                    "no una categoría.")
    with c2:
        st.markdown("**Por qué no los otros**")
        st.markdown("**No es clustering (no supervisado):** no buscamos agrupar productos, tenemos una variable "
                    "objetivo conocida.")
        st.markdown("**No es clasificación:** no queremos un sí o no, queremos una cantidad exacta para decidir "
                    "cuánto inventario preparar.")
        st.markdown("**Modelo usado:** regresión lineal múltiple, ajustada con todos los productos de tu archivo. "
                    "Se vuelve a entrenar cada vez que cargas datos nuevos. Para medirlo de forma honesta, se aparta "
                    "20 % de los productos al azar como datos de prueba que el modelo no ve al aprender.")
    if "modelo" in ss:
        st.caption(ss["modelo"].texto_metricas())
    st.caption("**Límite importante:** si cada producto aparece una sola vez, no se puede entrenar un modelo separado "
               "por producto (tendría un solo dato). Se entrena un modelo común y la predicción se calcula con los "
               "datos propios de cada producto.")
    st.caption("Surtir = predicción + inventario de seguridad − inventario actual. La seguridad es el nivel de "
               "servicio × el error (RMSE) medido en los datos de prueba.")


# ---------------------------------------------------------------- 1. Carga
st.subheader("1. Carga tus datos")
archivo = st.file_uploader("Archivo Excel (.xlsx, .xls) o CSV", type=["xlsx", "xls", "csv", "txt"])
st.download_button("Descargar plantilla", PLANTILLA_CSV, file_name="plantilla_inventario.csv", mime="text/csv")

if archivo is None:
    for k in [k for k in ss.keys() if k.startswith(PREFIJOS)]:
        del ss[k]
    for k in ("clave", "estado", "modelo", "nombre_base", "sel"):
        ss.pop(k, None)
else:
    contenido = archivo.getvalue()
    clave = (archivo.name, hashlib.md5(contenido).hexdigest())
    if ss.get("clave") != clave:
        ss["clave"] = clave
        try:
            modelo, msg, tipo = procesar(leer_archivo(archivo.name, contenido), archivo.name)
        except Exception:
            modelo, msg, tipo = None, "No se pudo leer el archivo. Verifica que sea un Excel o CSV válido.", "error"
        ss["estado"] = (msg, tipo)
        if modelo is not None:
            for k in [k for k in ss.keys() if k.startswith(PREFIJOS)]:
                del ss[k]
            ss["modelo"], ss["nombre_base"], ss["sel"], ss["busqueda"] = modelo, Path(archivo.name).stem, 0, ""

estado = ss.get("estado")
if estado is None:
    st.info("Aún no has cargado ningún archivo.")
elif estado[1] == "ok":
    st.success(estado[0])
elif estado[1] == "aviso":
    st.warning(estado[0])
else:
    st.error(estado[0])
st.caption("Columnas necesarias (en la primera fila): **precio, en_promocion, publicidad_gastada, fin_de_semana, "
           "temporada, unidades_vendidas**. En promoción y fin de semana van como 1/0 (o Sí/No). Recomendada: la "
           "columna **inventario_actual** con las unidades que tienes hoy de cada producto (si falta, se toma 0 y la "
           "página te avisa). Opcional: **producto** (nombre o código). Cada fila es un producto; se recomiendan al "
           "menos 30 filas para que el modelo sea confiable.")

if "modelo" not in ss:
    explicacion()
    st.stop()

m = ss["modelo"]


def fila(i):
    o, g = m.filas_orig[i], ss.get
    promo = (1.0 if g(f"p1_{i}") == "Sí" else 0.0) if f"p1_{i}" in ss else o[1]
    fin = (1.0 if g(f"p3_{i}") == "Sí" else 0.0) if f"p3_{i}" in ss else o[3]
    return [g(f"p0_{i}", o[0]), promo, g(f"p2_{i}", o[2]), fin, g(f"p4_{i}", o[4])]


def inventario(i):
    return ss.get(f"stk_{i}", m.stock0[i])


# ------------------------------------------------------- 2. Elige un producto
st.subheader("2. Elige un producto")
c1, c2, c3 = st.columns(3)
q = c1.text_input("Buscar por número o nombre", key="busqueda", placeholder="Ej. 15")
orden = c2.selectbox("Ordenar tabla por", ["Orden del archivo", "Más unidades por surtir"])
nivel = c3.selectbox("Nivel de servicio", list(NIVELES), index=1)
z = NIVELES[nivel]

E = [m.estimar(fila(i), inventario(i), z) for i in range(m.n)]
ql = q.strip().lower()
idx = [i for i in range(m.n) if not ql or ql in m.nombres[i].lower() or ql in str(i + 1)]
if orden.startswith("Más"):
    idx.sort(key=lambda i: (-E[i]["need"], i))
filas_tab = [fila(i) for i in idx]
df = pd.DataFrame({
    "Producto": [m.nombres[i] for i in idx],
    "Precio": [r[0] for r in filas_tab],
    "Promo": ["Sí" if r[1] else "No" for r in filas_tab],
    "Publ.": [js_round(r[2]) for r in filas_tab],
    "Fin sem.": ["Sí" if r[3] else "No" for r in filas_tab],
    "Temp.": [f"{r[4]:g}" for r in filas_tab],
    "Vendidas (hist.)": [js_round(m.y[i]) for i in idx],
    "Predicho": [js_round(E[i]["p"]) for i in idx],
    "Surtir": [E[i]["need"] for i in idx],
})
ev = st.dataframe(df, hide_index=True, use_container_width=True, height=420,
                  on_select="rerun", selection_mode="single-row", key="tabla")
if ev.selection.rows:
    ss["sel"] = idx[ev.selection.rows[0]]
st.caption(f"Suma de unidades a surtir de todos los productos: {f0(sum(e['need'] for e in E))}. "
           "Haz clic en una fila para ver el detalle.")

nombre_xlsx, datos_xlsx = exportar_excel(m, [fila(i) for i in range(m.n)], [inventario(i) for i in range(m.n)],
                                         z, ss.get("nombre_base", "datos"))
st.download_button("Descargar Excel con lo que hay que surtir", datos_xlsx, file_name=nombre_xlsx,
                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary")

# ------------------------------------------------------------------ Detalle
sel = ss.get("sel", 0)
if sel >= m.n:
    sel = ss["sel"] = 0
o = m.filas_orig[sel]
for k, v in ((f"p0_{sel}", o[0]), (f"p1_{sel}", "Sí" if o[1] else "No"), (f"p2_{sel}", o[2]),
             (f"p3_{sel}", "Sí" if o[3] else "No"), (f"p4_{sel}", o[4]), (f"stk_{sel}", m.stock0[sel])):
    ss.setdefault(k, v)

st.divider()
st.subheader(m.nombres[sel])
a = st.columns(6)
a[0].number_input("Precio", min_value=0.0, step=1.0, key=f"p0_{sel}")
a[1].number_input("Publicidad ($)", min_value=0.0, step=100.0, key=f"p2_{sel}")
a[2].selectbox("En promoción", ["No", "Sí"], key=f"p1_{sel}")
a[3].selectbox("Fin de semana", ["No", "Sí"], key=f"p3_{sel}")
a[4].selectbox("Temporada", m.temporadas, format_func=lambda s: f"{s:g}", key=f"p4_{sel}")
a[5].number_input("Inventario actual", min_value=0.0, step=1.0, key=f"stk_{sel}")

e = m.estimar(fila(sel), inventario(sel), z)
k = st.columns(4)
k[0].metric("Unidades previstas", f0(e["p"]))
k[1].metric("Inventario de seguridad", f0(e["seg"]))
k[2].metric("Inventario actual", f0(e["st"]))
k[3].metric("Unidades a surtir", f0(e["need"]))
if e["need"] > 0:
    st.info(f"Para {m.nombres[sel]} conviene surtir {f0(e['need'])} unidades. "
            f"Ventas históricas registradas: {f0(m.y[sel])}.")
else:
    st.success(f"{m.nombres[sel]} está cubierto: su inventario alcanza para la demanda prevista "
               "más el margen de seguridad.")


def reiniciar(i):
    r = m.filas_orig[i]
    ss[f"p0_{i}"], ss[f"p1_{i}"], ss[f"p2_{i}"] = r[0], "Sí" if r[1] else "No", r[2]
    ss[f"p3_{i}"], ss[f"p4_{i}"], ss[f"stk_{i}"] = "Sí" if r[3] else "No", r[4], m.stock0[i]


st.button("Volver a los datos originales de este producto", on_click=reiniciar, args=(sel,))
st.divider()
explicacion()
