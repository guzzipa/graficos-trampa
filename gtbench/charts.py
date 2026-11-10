"""Genera los gráficos del experimento. Cada trampa tiene su control: los MISMOS datos, bien graficados.

Todo es determinístico (semilla fija): correr `python gt.py charts` siempre produce los mismos PNG
y el mismo `graficos/tareas.json` con la respuesta correcta de cada uno.
"""
import json
import math
import os
import random

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
MESES_LARGO = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
               "septiembre", "octubre", "noviembre", "diciembre"]
AZUL, NARANJA, GRIS = "#2563A8", "#E07B28", "#888888"


def miles(x, _=None):
    """1234567 -> '1.234.567' (formato argentino)."""
    return f"{x:,.0f}".replace(",", ".")


def _fig(titulo):
    fig, ax = plt.subplots(figsize=(10, 6.25), dpi=100)
    ax.set_title(titulo, fontsize=16, loc="left", pad=14, fontweight="bold")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", color="#DDDDDD", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(labelsize=12)
    return fig, ax


def _save(fig, path):
    fig.tight_layout()
    fig.savefig(path, facecolor="white")
    plt.close(fig)


# ---------------------------------------------------------------- 1. eje truncado
CAT_DIF = ["menos de 10%", "entre 10% y 50%", "entre 50% y 100%", "más del doble"]


def eje_truncado(rng, v, trampa, path):
    ctx = [("Ventas anuales (millones de $)", "2025", "2026"),
           ("Usuarios activos (miles)", "Junio", "Julio"),
           ("Transacciones por día (miles)", "Sucursal Norte", "Sucursal Sur"),
           ("Ticket promedio ($)", "Plan Básico", "Plan Plus")][v]
    g = [0.04, 0.07, 0.22, 0.35][v]
    a = rng.randint(400, 900)
    b = round(a * (1 + g))
    fig, ax = _fig(ctx[0])
    ax.bar([ctx[1], ctx[2]], [a, b], color=[GRIS, AZUL], width=0.55)
    if trampa:
        bottom = a - (b - a) * 0.3
        ax.set_ylim(bottom, b + (b - a) * 0.08)
    else:
        ax.set_ylim(0, b * 1.08)
    ax.yaxis.set_major_formatter(FuncFormatter(miles))
    _save(fig, path)
    real = (b / a - 1) * 100
    return dict(pregunta=(f"Según el gráfico, ¿cuánto mayor es el valor de \"{ctx[2]}\" que el de \"{ctx[1]}\"?"),
                opciones=CAT_DIF, correcta=CAT_DIF[0] if real < 10 else CAT_DIF[1],
                datos={ctx[1]: a, ctx[2]: b, "diferencia_pct": round(real, 1)})


# ---------------------------------------------------------------- 2. doble eje
def doble_eje(rng, v, trampa, path):
    t = list(range(12))
    if v < 2:  # los costos NUNCA superan a los ingresos, pero con doble eje la línea parece cruzar
        i0 = rng.randint(200, 260)
        ing = [round(i0 + 5 * k + rng.uniform(-2, 2)) for k in t]
        c0 = i0 - rng.randint(90, 110)
        cos = [round(c0 + 6.5 * k + rng.uniform(-2, 2)) for k in t]
        lim_i = (min(ing) - 5, max(ing) + 60)
        lim_c = (min(cos) - 60, max(cos) + 5)
    else:  # los costos SÍ superan a los ingresos desde cierto mes, pero con doble eje parecen siempre abajo
        i0 = rng.randint(100, 130)
        ing = [round(i0 + 3 * k) for k in t]
        cruce = [7, 8][v - 2]
        c0 = ing[cruce] - 9 * cruce + 2  # cos[cruce] = ing[cruce] + 2
        cos = [round(c0 + 9 * k) for k in t]
        lim_i = (0, max(ing) * 1.05)
        lim_c = (0, max(cos) * 4)
    primero = next((k for k in t if cos[k] > ing[k]), None)
    fig, ax = _fig("Ingresos y costos mensuales 2026 (millones de $)")
    ax.plot(MESES, ing, color=AZUL, linewidth=3, marker="o", label="Ingresos")
    if trampa:
        ax.set_ylim(*lim_i)
        ax.set_ylabel("Ingresos", color=AZUL, fontsize=13)
        ax2 = ax.twinx()
        ax2.plot(MESES, cos, color=NARANJA, linewidth=3, marker="o", label="Costos")
        ax2.set_ylim(*lim_c)
        ax2.set_ylabel("Costos", color=NARANJA, fontsize=13)
        ax2.tick_params(labelsize=12)
        ax2.spines["top"].set_visible(False)
        h = [ax.lines[0], ax2.lines[0]]
    else:
        ax.plot(MESES, cos, color=NARANJA, linewidth=3, marker="o", label="Costos")
        ax.set_ylim(0, max(max(ing), max(cos)) * 1.1)
        h = ax.lines
    ax.legend(h, ["Ingresos", "Costos"], loc="upper left", fontsize=12, frameon=False)
    _save(fig, path)
    return dict(pregunta=("Según el gráfico, ¿en qué mes los costos superan por primera vez a los ingresos? "
                          "Si en ningún mes los superan, respondé \"ninguno\"."),
                opciones=MESES_LARGO + ["ninguno"],
                correcta="ninguno" if primero is None else MESES_LARGO[primero],
                tolerancia_meses=1, datos={"ingresos": ing, "costos": cos})


# ---------------------------------------------------------------- 3. eje invertido
DIR = ["subieron", "bajaron", "se mantuvieron"]


def eje_invertido(rng, v, trampa, path):
    titulo, evento = [("Reclamos de clientes por mes", "Lanzamiento app nueva"),
                      ("Fraudes detectados por mes", "Cambio de proveedor"),
                      ("Reclamos de clientes por mes", "Nuevo chatbot"),
                      ("Fraudes detectados por mes", "Nuevo modelo antifraude")][v]
    sube = v in (0, 1)
    base = rng.randint(250, 350)
    vals = []
    for k in range(12):
        if k < 6:
            vals.append(base + rng.randint(-12, 12))
        else:
            d = (k - 5) * base * 0.09
            vals.append(round(base + (d if sube else -d) + rng.randint(-8, 8)))
    fig, ax = _fig(titulo)
    ax.plot(MESES, vals, color=AZUL, linewidth=3, marker="o")
    lo, hi = 0, max(vals) * 1.15
    ax.set_ylim(lo, hi)
    if trampa:
        ax.invert_yaxis()
        ax.fill_between(MESES, vals, lo, color=AZUL, alpha=0.18)  # relleno hacia arriba, como el gráfico de Reuters
    else:
        ax.fill_between(MESES, vals, lo, color=AZUL, alpha=0.18)
    ax.axvline(5.5, color=GRIS, linestyle="--", linewidth=1.5)
    ax.text(5.6, (hi * 0.06 if not trampa else hi * 0.94), evento, fontsize=12, color="#444444")
    _save(fig, path)
    return dict(pregunta=(f"Según el gráfico, después de \"{evento}\", ¿los {titulo.split()[0].lower()} "
                          "subieron, bajaron o se mantuvieron?"),
                opciones=DIR, correcta=DIR[0] if sube else DIR[1], datos={"valores": vals})


# ---------------------------------------------------------------- 4. acumulado
def acumulado(rng, v, trampa, path):
    trim = ["T1 25", "T2 25", "T3 25", "T4 25", "T1 26", "T2 26", "T3 26", "T4 26"]
    base = rng.randint(30, 50)
    inc = [round(base * f) for f in [[1, 1.1, 1.2, 1.3, 1.4, 1.5, 1.45, 0.9],
                                     [1, 1.08, 1.15, 1.25, 1.35, 1.4, 1.3, 0.75],
                                     [1, 1.15, 1.3, 1.4, 1.5, 1.6, 1.55, 1.1],
                                     [1, 1.05, 1.1, 1.2, 1.25, 1.35, 1.3, 0.95]][v]]
    nombre = ["Ventas", "Préstamos otorgados", "Ventas", "Préstamos otorgados"][v]
    if trampa:
        acu = [sum(inc[:k + 1]) for k in range(len(inc))]
        fig, ax = _fig(f"{nombre} acumuladas desde 2025 (millones de $)")
        ax.plot(trim, acu, color=AZUL, linewidth=3, marker="o")
        ax.fill_between(trim, acu, 0, color=AZUL, alpha=0.15)
        ax.set_ylim(0, max(acu) * 1.1)
    else:
        fig, ax = _fig(f"{nombre} por trimestre (millones de $)")
        ax.bar(trim, inc, color=AZUL, width=0.6)
        ax.set_ylim(0, max(inc) * 1.15)
    _save(fig, path)
    return dict(pregunta=(f"Según el gráfico, comparando el último trimestre (T4 26) con el anterior (T3 26), "
                          f"¿{'las ventas' if nombre == 'Ventas' else 'los préstamos otorgados'} de ese trimestre "
                          "subieron, bajaron o se mantuvieron?"),
                opciones=DIR, correcta=DIR[1], datos={"por_trimestre": inc})


# ---------------------------------------------------------------- 5. escala logarítmica
ANIOS = ["2025", "2026", "parecido"]


def escala_log(rng, v, trampa, path):
    m = [f"{MESES[k % 12]} {25 + k // 12}" for k in range(25)]
    u0 = [1000, 3000, 5000, 2000][v]
    if v in (0, 1):  # mismo % de crecimiento los dos años: en log es una recta
        r1 = r2 = 10 ** (1 / 12)
    else:            # el % de crecimiento se frena: en log la curva se aplana
        r1, r2 = 20 ** (1 / 12), 3 ** (1 / 12)
    vals = [u0]
    for k in range(24):
        vals.append(vals[-1] * (r1 if k < 12 else r2))
    vals = [round(x) for x in vals]
    nuevos_25, nuevos_26 = vals[12] - vals[0], vals[24] - vals[12]
    nombre = ["Usuarios registrados", "Clientes con tarjeta", "Usuarios registrados", "Clientes con tarjeta"][v]
    fig, ax = _fig(f"{nombre}, fin de cada mes")
    ax.plot(range(25), vals, color=AZUL, linewidth=3)
    ax.set_xticks(range(0, 25, 3))
    ax.set_xticklabels([m[k] for k in range(0, 25, 3)])
    if trampa:
        ax.set_yscale("log")
    else:
        ax.set_ylim(0, max(vals) * 1.08)
    ax.yaxis.set_major_formatter(FuncFormatter(miles))
    ax.grid(axis="y", which="both", color="#E5E5E5", linewidth=0.6)
    _save(fig, path)
    return dict(pregunta=(f"Según el gráfico, ¿en qué año se sumaron más {nombre.split()[0].lower()} nuevos en "
                          "términos absolutos (cantidad de personas): en 2025 (de Ene 25 a Ene 26), en 2026 (de Ene 26 a Ene 27), "
                          "o fue parecido?"),
                opciones=ANIOS, correcta="2026" if nuevos_26 > nuevos_25 * 1.2 else "parecido",
                datos={"nuevos_2025": nuevos_25, "nuevos_2026": nuevos_26})


# ---------------------------------------------------------------- 6. eje X irregular
def eje_x_irregular(rng, v, trampa, path):
    anios = [2016, 2018, 2020, 2022, 2023, 2024, 2025]
    p1 = rng.randint(18, 22)        # crecimiento por año 2016-2022 (cada punto = 2 años)
    p2 = round(p1 * rng.uniform(1.4, 1.6))  # crecimiento por año 2022-2025 (cada punto = 1 año): MÁS rápido
    vals = [100]
    for k in range(1, len(anios)):
        vals.append(vals[-1] + p1 * (anios[k] - anios[k - 1]) if anios[k] <= 2022 else vals[-1] + p2)
    nombre = ["Facturación anual (millones de $)", "Clientes (miles)",
              "Facturación anual (millones de $)", "Clientes (miles)"][v]
    fig, ax = _fig(nombre)
    if trampa:
        x = list(range(len(anios)))  # años como categorías equiespaciadas
    else:
        x = anios
    ax.plot(x, vals, color=AZUL, linewidth=3, marker="o")
    ax.set_xticks(x)
    ax.set_xticklabels([str(a) for a in anios])
    ax.set_ylim(0, max(vals) * 1.1)
    _save(fig, path)
    op = ["2016-2022", "2022-2025", "parecido"]
    return dict(pregunta=("Según el gráfico, ¿en qué período creció más rápido por año: entre 2016 y 2022, "
                          "entre 2022 y 2025, o fue parecido?"),
                opciones=op, correcta=op[1], datos={"anios": anios, "valores": vals,
                                                     "por_anio_2016_2022": p1, "por_anio_2022_2025": p2})


TIPOS = {
    "eje_truncado": eje_truncado,
    "doble_eje": doble_eje,
    "eje_invertido": eje_invertido,
    "acumulado": acumulado,
    "escala_log": escala_log,
    "eje_x_irregular": eje_x_irregular,
}
VARIANTES = 4


def build_all(outdir):
    os.makedirs(outdir, exist_ok=True)
    tareas = []
    for ti, (tipo, fn) in enumerate(TIPOS.items()):
        for v in range(VARIANTES):
            for trampa in (False, True):
                rng = random.Random(1000 * ti + v)  # misma semilla: trampa y control usan los mismos datos
                tid = f"{tipo}_{v + 1}_{'trampa' if trampa else 'control'}"
                info = fn(rng, v, trampa, os.path.join(outdir, tid + ".png"))
                tareas.append(dict(id=tid, tipo=tipo, variante=v + 1, trampa=trampa,
                                   imagen=tid + ".png", **info))
    with open(os.path.join(outdir, "tareas.json"), "w", encoding="utf-8") as f:
        json.dump(tareas, f, ensure_ascii=False, indent=1)
    return tareas


if __name__ == "__main__":
    t = build_all("graficos")
    print(len(t), "gráficos")
