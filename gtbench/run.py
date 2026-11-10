"""Le muestra cada gráfico a cada modelo, por separado, y corrige contra la respuesta conocida."""
import argparse
import base64
import csv
import json
import os
import re
import time
import unicodedata

from . import llm
from .charts import MESES_LARGO, TIPOS, build_all

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRAF = os.path.join(ROOT, "graficos")
RESULTS = os.path.join(ROOT, "results")

# Criterio fijado ANTES de correr cualquier modelo:
# - Un modelo "cae" en una trampa si responde bien el CONTROL (mismos datos, bien graficados)
#   y mal la TRAMPA. Si falla el control, ese par no cuenta: no sabe leer ese gráfico, no lo engañó la trampa.
# - Un tipo de trampa "engaña" a un modelo si cae en al menos 2 de sus 4 variantes.
# - La hipótesis general se confirma si, sumando todos los modelos, la tasa de acierto en trampas
#   es al menos 25 puntos menor que en controles.
MIN_VARIANTES = 2
BRECHA_HIPOTESIS = 25

SYSTEM = ("Sos analista de datos. Te muestran un gráfico y una pregunta sobre lo que muestra. "
          "Respondé con precisión según los datos del gráfico.")

USER = """{pregunta}

Opciones: {opciones}

Respondé SOLO con un JSON de esta forma, sin texto adicional:
{{"respuesta": "<una de las opciones, tal cual>", "explicacion": "<una oración>"}}"""


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9% ]+", " ", s).strip()


def parse(text, opciones):
    text = re.sub(r"<(think|thought)>.*?</\1>", "", text or "", flags=re.S)
    m = re.search(r"\{.*\}", text, flags=re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except ValueError:
        return None
    r = norm(d.get("respuesta", ""))
    # elegir la opción que coincide (la más larga primero, para no confundir "10%" con "entre 10% y 50%")
    for o in sorted(opciones, key=len, reverse=True):
        if norm(o) == r:
            return {"respuesta": o, "explicacion": str(d.get("explicacion", ""))[:400]}
    for o in sorted(opciones, key=len, reverse=True):
        if norm(o) in r:
            return {"respuesta": o, "explicacion": str(d.get("explicacion", ""))[:400]}
    return {"respuesta": None, "cruda": d.get("respuesta"), "explicacion": str(d.get("explicacion", ""))[:400]}


def correcta(tarea, resp):
    if resp is None:
        return False
    if tarea.get("tolerancia_meses") and resp in MESES_LARGO and tarea["correcta"] in MESES_LARGO:
        return abs(MESES_LARGO.index(resp) - MESES_LARGO.index(tarea["correcta"])) <= tarea["tolerancia_meses"]
    return resp == tarea["correcta"]


def load_models():
    with open(os.path.join(ROOT, "models.json"), encoding="utf-8") as f:
        return {m["name"]: m for m in json.load(f)["models"]}


def load_env():
    p = os.path.join(ROOT, ".env")
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def tareas():
    p = os.path.join(GRAF, "tareas.json")
    if not os.path.exists(p):
        return build_all(GRAF)
    return json.load(open(p, encoding="utf-8"))


def cmd_run(args):
    cfg = load_models()[args.model]
    out = os.path.join(RESULTS, cfg["name"])
    os.makedirs(out, exist_ok=True)
    lista = tareas()
    if args.limit:
        lista = lista[:args.limit]
    for t in lista:
        path = os.path.join(out, t["id"] + ".json")
        if os.path.exists(path) and not args.force:
            continue
        img = base64.b64encode(open(os.path.join(GRAF, t["imagen"]), "rb").read()).decode()
        user = USER.format(pregunta=t["pregunta"], opciones=" | ".join(t["opciones"]))
        res, raw, intento, err = None, "", 0, None
        while (res is None or res["respuesta"] is None) and intento < 3:
            intento += 1
            try:
                r = llm.chat(cfg, SYSTEM, user, images=[img])
            except llm.LLMError as ex:
                err = str(ex)
                print(f"  {t['id']}: ERROR {ex}", flush=True)
                break
            raw = r["text"]
            res = parse(raw, t["opciones"])
        if err and not raw:
            continue  # error de infraestructura: no se guarda, se reintenta en la próxima corrida
        ok = correcta(t, res and res["respuesta"])
        rec = dict(modelo=cfg["name"], tarea=t["id"], respuesta_cruda=raw, resultado=res,
                   correcta=t["correcta"], acierto=ok, intentos=intento,
                   timestamp=time.strftime("%Y-%m-%d %H:%M:%S"))
        with open(path, "w", encoding="utf-8") as f:
            json.dump(rec, f, ensure_ascii=False, indent=1)
        print(f"  {t['id']:<28} {'OK ' if ok else 'MAL'} {res and res['respuesta']}", flush=True)
        if cfg.get("min_interval_s"):
            time.sleep(cfg["min_interval_s"])


def cmd_report(args):
    ts = {t["id"]: t for t in tareas()}
    modelos = sorted(d for d in os.listdir(RESULTS)
                     if os.path.isdir(os.path.join(RESULTS, d)) and not d.startswith("_"))
    rows = []
    for m in modelos:
        for tid, t in ts.items():
            p = os.path.join(RESULTS, m, tid + ".json")
            if os.path.exists(p):
                r = json.load(open(p, encoding="utf-8"))
                rows.append(dict(modelo=m, tarea=tid, tipo=t["tipo"], variante=t["variante"],
                                 trampa=t["trampa"], correcta=t["correcta"],
                                 respuesta=(r["resultado"] or {}).get("respuesta"),
                                 acierto=r["acierto"], explicacion=(r["resultado"] or {}).get("explicacion", "")))
    with open(os.path.join(RESULTS, "resultados.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    idx = {(r["modelo"], r["tarea"]): r for r in rows}

    L = ["# Resultados: ¿la IA sabe leer un gráfico tramposo?", "",
         "Criterio fijado antes de correr: un modelo cae en una trampa si responde bien el control (mismos datos, "
         f"bien graficados) y mal la trampa. Un tipo de trampa engaña a un modelo si cae en {MIN_VARIANTES} o más "
         f"de sus 4 variantes. Hipótesis: el acierto en trampas es al menos {BRECHA_HIPOTESIS} puntos menor que en controles.", "",
         "## Acierto por modelo", "", "| Modelo | Controles | Trampas | Cayó (control bien, trampa mal) |", "|---|---|---|---|"]
    tot = {"c": [0, 0], "t": [0, 0], "cayo": [0, 0]}
    caidas = {}
    for m in modelos:
        c = [r for r in rows if r["modelo"] == m and not r["trampa"]]
        t = [r for r in rows if r["modelo"] == m and r["trampa"]]
        pares = [(idx.get((m, x["tarea"].replace("_trampa", "_control"))), x) for x in t]
        pares = [(a, b) for a, b in pares if a and a["acierto"]]
        cayo = [b for a, b in pares if not b["acierto"]]
        for b in cayo:
            caidas.setdefault((m, b["tipo"]), []).append(b)
        ca, ta = sum(r["acierto"] for r in c), sum(r["acierto"] for r in t)
        tot["c"][0] += ca; tot["c"][1] += len(c); tot["t"][0] += ta; tot["t"][1] += len(t)
        tot["cayo"][0] += len(cayo); tot["cayo"][1] += len(pares)
        L.append(f"| {m} | {ca}/{len(c)} | {ta}/{len(t)} | {len(cayo)}/{len(pares)} |")
    pc = 100 * tot["c"][0] / max(1, tot["c"][1])
    pt = 100 * tot["t"][0] / max(1, tot["t"][1])
    L += ["", f"**Total:** controles {pc:.0f}% · trampas {pt:.0f}% · brecha {pc - pt:.0f} puntos → hipótesis "
              f"{'CONFIRMADA' if pc - pt >= BRECHA_HIPOTESIS else 'NO confirmada'}.", "",
          "## Por tipo de trampa", "", "| Tipo | " + " | ".join(modelos) + " |", "|---|" + "---|" * len(modelos)]
    for tipo in TIPOS:
        cel = []
        for m in modelos:
            ctrl = sum(1 for r in rows if r["modelo"] == m and r["tipo"] == tipo and not r["trampa"] and r["acierto"])
            trp = sum(1 for r in rows if r["modelo"] == m and r["tipo"] == tipo and r["trampa"] and r["acierto"])
            n = len(caidas.get((m, tipo), []))
            cel.append(f"{ctrl}/4 → {trp}/4{' **ENGAÑA**' if n >= MIN_VARIANTES else ''}")
        L.append(f"| {tipo} | " + " | ".join(cel) + " |")
    L += ["", "Cada celda: aciertos en controles → aciertos en trampas.", "", "## Detalle", "",
          "| Modelo | Gráfico | Correcta | Respondió | Explicación |", "|---|---|---|---|---|"]
    for r in rows:
        if r["trampa"]:
            L.append(f"| {r['modelo']} | {r['tarea']} | {r['correcta']} | "
                     f"{'✅' if r['acierto'] else '❌'} {r['respuesta']} | {r['explicacion'].replace('|', '/')} |")
    open(os.path.join(RESULTS, "reporte.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L[:30]))


def main():
    load_env()
    ap = argparse.ArgumentParser(description="¿La IA sabe leer un gráfico tramposo?")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--model", required=True)
    r.add_argument("--force", action="store_true")
    r.add_argument("--limit", type=int, default=0)
    sub.add_parser("report")
    sub.add_parser("charts")
    a = ap.parse_args()
    if a.cmd == "run":
        cmd_run(a)
    elif a.cmd == "report":
        cmd_report(a)
    else:
        print(len(build_all(GRAF)), "gráficos en", GRAF)
