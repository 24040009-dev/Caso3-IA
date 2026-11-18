"""Lógica del planeador de inventario (sin interfaz).

Aprendizaje supervisado de tipo regresión: regresión lineal múltiple que predice
las unidades vendidas de cada producto. Es la misma lógica de la página web:
lectura de columnas por alias, división 80/20 con semilla fija, métricas de
prueba (MAE, RMSE, R²), inventario de seguridad y cálculo de unidades a surtir.
"""
from __future__ import annotations

import io
import math
import re
import unicodedata
from dataclasses import dataclass, field

import numpy as np

ALIASES = {
    "precio": ["precio", "price"],
    "promo": ["en_promocion", "promocion", "promo"],
    "pub": ["publicidad_gastada", "publicidad", "gasto_publicidad"],
    "fin": ["fin_de_semana", "fin_semana", "finde"],
    "temp": ["temporada", "season"],
    "uni": ["unidades_vendidas", "unidades", "ventas"],
    "name": ["producto", "nombre", "nombre_producto", "sku", "codigo", "id"],
    "stock": ["inventario_actual", "inventario", "stock", "existencias"],
}
REQUERIDAS = ["precio", "promo", "pub", "fin", "temp", "uni"]
NOMBRE_COLUMNA = {
    "precio": "precio", "promo": "en_promocion", "pub": "publicidad_gastada",
    "fin": "fin_de_semana", "temp": "temporada", "uni": "unidades_vendidas",
}
MIN_FILAS = 20
FRACCION_PRUEBA = 0.2
SEMILLA = 42
NIVELES = {"90 %": 1.28, "95 %": 1.645, "99 %": 2.33}
PLANTILLA_CSV = (
    "producto,precio,en_promocion,publicidad_gastada,fin_de_semana,temporada,"
    "unidades_vendidas,inventario_actual\n"
)

_NUM_RE = re.compile(r"^[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?")


def js_round(x: float) -> int:
    """Redondeo como Math.round (la mitad hacia arriba)."""
    return int(math.floor(x + 0.5))


def norm(s) -> str:
    s = unicodedata.normalize("NFD", str(s).lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").strip()
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


def es_vacio(v) -> bool:
    if v is None:
        return True
    if isinstance(v, (float, np.floating)) and math.isnan(v):
        return True
    return str(v).strip() == ""


def num(v) -> float:
    """Convierte a número; acepta Sí/No, True/False y comas decimales."""
    if isinstance(v, (bool, np.bool_)):
        return float(v)
    if isinstance(v, (int, float, np.integer, np.floating)):
        return float(v)
    s = norm(v)
    if s in {"si", "yes", "true", "verdadero"}:
        return 1.0
    if s in {"no", "false", "falso"}:
        return 0.0
    t = re.sub(r"[$\s]", "", str(v)).replace(",", ".", 1)
    m = _NUM_RE.match(t)
    return float(m.group()) if m else float("nan")


def _mulberry32(a: int):
    state = [a & 0xFFFFFFFF]

    def imul(x, y):
        return (x * y) & 0xFFFFFFFF

    def nxt() -> float:
        state[0] = (state[0] + 0x6D2B79F5) & 0xFFFFFFFF
        a_ = state[0]
        t = imul(a_ ^ (a_ >> 15), 1 | a_)
        t = ((t + imul(t ^ (t >> 7), 61 | t)) & 0xFFFFFFFF) ^ t
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296

    return nxt


def _matriz(rows, seasons) -> np.ndarray:
    r = np.asarray(rows, dtype=float).reshape(-1, 5)
    cols = [np.ones(len(r)), r[:, 0], r[:, 1], r[:, 2], r[:, 3]]
    cols += [(r[:, 4] == s).astype(float) for s in seasons[1:]]
    return np.column_stack(cols)


def _ajustar(rows, y, seasons) -> np.ndarray:
    X = _matriz(rows, seasons)
    A = X.T @ X
    for i in range(1, A.shape[0]):
        A[i, i] += 1e-6
    return np.linalg.solve(A, X.T @ np.asarray(y, dtype=float))


def _predecir(beta, rows, seasons) -> np.ndarray:
    return np.maximum(0.0, _matriz(rows, seasons) @ beta)


def _metricas(beta, rows, y, seasons) -> dict:
    y = np.asarray(y, dtype=float)
    e = y - _predecir(beta, rows, seasons)
    se = float(np.sum(e ** 2))
    st = float(np.sum((y - y.mean()) ** 2))
    return {"mae": float(np.mean(np.abs(e))), "rmse": math.sqrt(se / len(y)),
            "r2": (1 - se / st) if st else 0.0}


@dataclass
class Modelo:
    nombres: list
    filas_orig: list          # [precio, promo, publicidad, fin_de_semana, temporada]
    y: list                   # unidades vendidas históricas
    stock0: list              # inventario actual de cada producto (del archivo)
    temporadas: list
    beta: np.ndarray          # modelo final, reajustado con todos los productos
    mt: dict                  # métricas en prueba
    mtr: dict                 # métricas en entrenamiento
    n: int = 0
    n_tr: int = 0
    n_te: int = 0
    tiene_stock: bool = True

    @property
    def rmse(self) -> float:
        return self.mt["rmse"]

    def predecir(self, fila) -> float:
        return float(_predecir(self.beta, [fila], self.temporadas)[0])

    def estimar(self, fila, stock: float, z: float) -> dict:
        p = self.predecir(fila)
        seg = z * self.rmse
        return {"p": p, "seg": seg, "st": stock, "need": max(0, math.ceil(p + seg - stock))}

    def texto_metricas(self) -> str:
        mt, mtr = self.mt, self.mtr
        return (
            f"Evaluación con datos que el modelo no vio: se entrenó con {self.n_tr} productos y se probó con "
            f"{self.n_te} productos apartados al azar (80 % / 20 %). En la prueba, el error promedio (MAE) es de "
            f"±{mt['mae']:.1f} unidades, el RMSE es {mt['rmse']:.1f} y el R² es {mt['r2']:.2f} "
            f"(en entrenamiento, R² = {mtr['r2']:.2f}). Para las predicciones, el modelo se reajusta con los "
            f"{self.n} productos."
        )


def entrenar(nombres, filas, y, stock, tiene_stock=True) -> Modelo:
    n = len(y)
    temporadas = sorted({float(r[4]) for r in filas})
    rnd = _mulberry32(SEMILLA)
    idx = list(range(n))
    for i in range(n - 1, 0, -1):
        j = int(math.floor(rnd() * (i + 1)))
        idx[i], idx[j] = idx[j], idx[i]
    nt = max(4, js_round(n * FRACCION_PRUEBA))
    te, tr = idx[:nt], idx[nt:]
    pick = lambda a, s: [a[i] for i in s]
    b1 = _ajustar(pick(filas, tr), pick(y, tr), temporadas)
    mt = _metricas(b1, pick(filas, te), pick(y, te), temporadas)
    mtr = _metricas(b1, pick(filas, tr), pick(y, tr), temporadas)
    beta = _ajustar(filas, y, temporadas)
    return Modelo(list(nombres), [list(map(float, r)) for r in filas], list(map(float, y)),
                  list(map(float, stock)), temporadas, beta, mt, mtr, n, len(tr), nt, tiene_stock)


def procesar(objs: list, etiqueta: str):
    """Valida columnas, limpia filas y entrena. Devuelve (modelo|None, mensaje, tipo)
    con tipo 'ok', 'aviso' o 'error'."""
    if not objs:
        return None, "El archivo está vacío.", "error"
    claves = list(objs[0].keys())
    col = {}
    for campo, alias in ALIASES.items():
        k = next((h for h in claves if norm(h) in alias), None)
        if k is not None:
            col[campo] = k
    faltan = [f for f in REQUERIDAS if f not in col]
    if faltan:
        return None, ("Faltan columnas: " + ", ".join(NOMBRE_COLUMNA[f] for f in faltan)
                      + ". Revisa los nombres de la primera fila."), "error"
    nombres, filas, y, stock, malas = [], [], [], [], 0
    for i, o in enumerate(objs):
        r = [num(o[col["precio"]]), num(o[col["promo"]]), num(o[col["pub"]]),
             num(o[col["fin"]]), num(o[col["temp"]])]
        u = num(o[col["uni"]])
        if "stock" not in col:
            sk = 0.0
        else:
            sk = float("nan") if es_vacio(o[col["stock"]]) else num(o[col["stock"]])
        if any(math.isnan(v) for v in r) or math.isnan(u) or math.isnan(sk):
            malas += 1
            continue
        nm = ""
        if "name" in col and not es_vacio(o[col["name"]]):
            v = o[col["name"]]
            nm = str(int(v)) if isinstance(v, (float, np.floating)) and float(v).is_integer() else str(v).strip()
        nombres.append(nm or f"Producto {i + 1}")
        filas.append(r)
        y.append(u)
        stock.append(sk)
    if len(filas) < MIN_FILAS:
        return None, (f"Solo hay {len(filas)} filas válidas; se necesitan al menos {MIN_FILAS} "
                      "(mejor 30 o más) para entrenar y probar el modelo."), "error"
    try:
        modelo = entrenar(nombres, filas, y, stock, "stock" in col)
    except Exception:
        return None, "No se pudo entrenar el modelo con estos datos.", "error"
    msg = f"{etiqueta}: {len(filas)} productos cargados"
    if malas:
        msg += f" ({malas} filas omitidas por datos incompletos o no numéricos)"
    msg += "."
    if "stock" not in col:
        msg += (" Atención: tu archivo no trae la columna inventario_actual, así que se tomó 0 unidades en "
                "inventario para todos los productos. Agrégala para saber cuánto surtir realmente.")
        return modelo, msg, "aviso"
    return modelo, msg, "ok"


def leer_archivo(nombre: str, contenido: bytes) -> list:
    """Lee un Excel (.xlsx/.xls) o CSV y devuelve una lista de diccionarios (una por fila)."""
    import pandas as pd

    if nombre.lower().endswith((".xlsx", ".xls")):
        df = pd.read_excel(io.BytesIO(contenido), sheet_name=0)
    else:
        try:
            texto = contenido.decode("utf-8-sig")
        except UnicodeDecodeError:
            texto = contenido.decode("latin-1")
        primera = texto.splitlines()[0] if texto.strip() else ""
        sep = ";" if primera.count(";") > primera.count(",") else ","
        df = pd.read_csv(io.StringIO(texto), sep=sep, dtype=str, keep_default_na=False,
                         skipinitialspace=True)
    df.columns = [str(c).strip() for c in df.columns]
    return df.to_dict("records")


def exportar_excel(m: Modelo, filas, stocks, z: float, nombre_base: str = "datos") -> tuple:
    """Excel con las unidades a surtir. Devuelve (nombre_archivo, bytes)."""
    import xlsxwriter

    enc = ["Producto", "Precio", "En promoción", "Publicidad gastada", "Fin de semana", "Temporada",
           "Unidades vendidas", "Unidades previstas", "Inventario de seguridad", "Inventario actual",
           "Unidades a surtir"]
    datos = []
    for i, r in enumerate(filas):
        e = m.estimar(r, stocks[i], z)
        datos.append([m.nombres[i], *r, m.y[i], js_round(e["p"]), js_round(e["seg"]), e["st"], e["need"]])
    total = sum(d[10] for d in datos)
    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, {"in_memory": True})
    ws = wb.add_worksheet("A surtir")
    negrita = wb.add_format({"bold": True})
    ws.write_row(0, 0, enc, negrita)
    for i, d in enumerate(datos, start=1):
        ws.write_row(i, 0, d)
    for c, h in enumerate(enc):
        ws.set_column(c, c, max(12, len(h) + 2))
    rs = wb.add_worksheet("Resumen")
    resumen = [["Resumen"], ["Productos", m.n], ["Total a surtir", total], ["Nivel de servicio (z)", z],
               ["Productos de entrenamiento / prueba", f"{m.n_tr} / {m.n_te}"],
               ["MAE en prueba (unidades)", round(m.mt["mae"], 1)],
               ["RMSE en prueba (unidades)", round(m.mt["rmse"], 1)],
               ["R² en prueba", round(m.mt["r2"], 3)],
               ["Modelo", "Regresión lineal múltiple (aprendizaje supervisado)"]]
    for i, fila in enumerate(resumen):
        rs.write_row(i, 0, fila)
    rs.set_column(0, 0, 36)
    rs.set_column(1, 1, 50)
    wb.close()
    return f"inventario_a_surtir_{nombre_base}.xlsx", buf.getvalue()
