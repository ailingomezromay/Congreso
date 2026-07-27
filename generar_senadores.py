#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generar_senadores.py  —  Banca Vacía / Observatorio del Congreso
------------------------------------------------------------------
Calcula el presentismo de cada senador nacional en las votaciones
de un año y deja los resultados en `senadores.json`, que consume la
solapa "Senadores" de la página.

Fuente de datos: API pública ArgentinaDatos
  - Votaciones : https://api.argentinadatos.com/v1/senado/actas
  - Registro   : https://api.argentinadatos.com/v1/senado/senadores

No necesitás tocar nada para actualizar: se corre solo y baja lo último.
"""

import json
import re
import unicodedata
import collections
import datetime
import urllib.request

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
ANIO = 2025                       # año calendario a analizar
UMBRAL_PARTICIPACION = 0.50       # se rankea solo a quien pudo votar >= 50%
API_ACTAS = "https://api.argentinadatos.com/v1/senado/actas"
API_SENADORES = "https://api.argentinadatos.com/v1/senado/senadores"
SALIDA = "senadores.json"

# Senadores nuevos que todavía no figuran en el registro con período vigente.
# (se completan a mano hasta que la fuente los cargue)
OVERRIDE = {
    "villaverde, maria lorena": {"provincia": "Río Negro",
                                 "bloque": "La Libertad Avanza"},
}


# ---------------------------------------------------------------------------
# Utilidades de nombres (para cruzar votaciones con el registro)
# ---------------------------------------------------------------------------
STOPWORDS = {"de", "del", "la", "los", "las", "y"}


def normalizar(texto):
    """minúsculas, sin tildes, sin apodos entre comillas ni puntos."""
    texto = texto or ""
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    texto = re.sub(r'"[^"]*"', "", texto)   # saca apodos: "Pipi"
    texto = re.sub(r"[.]", "", texto)
    return re.sub(r"\s+", " ", texto).strip().lower()


def partes(nombre):
    """separa 'Apellido, Nombre' en dos listas de tokens (sin stopwords)."""
    n = normalizar(nombre)
    apellido, nombre_pila = (n.split(",", 1) + [""])[:2] if "," in n else (n, "")
    ap = [t for t in apellido.split() if t not in STOPWORDS]
    no = [t for t in nombre_pila.split() if t not in STOPWORDS]
    return ap, no


def claves(nombre):
    """genera varias claves para tolerar variantes de nombre."""
    ap, no = partes(nombre)
    primer_apellido = ap[0] if ap else ""
    ks = [normalizar(nombre)]
    if no:
        ks.append(primer_apellido + "|" + no[0])    # apellido + primer nombre
        ks.append(primer_apellido + "|" + no[-1])   # apellido + último nombre
    return ks


# ---------------------------------------------------------------------------
# Descarga
# ---------------------------------------------------------------------------
def bajar_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "banca-vacia"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


# ---------------------------------------------------------------------------
# Cruce senador -> provincia / bloque
# ---------------------------------------------------------------------------
def construir_indice(registro, anio):
    """arma un índice de nombre->datos con los senadores vigentes en el año."""
    anio = str(anio)

    def vigente(r):
        for k in ("periodoReal", "periodoLegal"):
            p = r.get(k) or {}
            ini = (p.get("inicio") or "0000")[:4]
            fin = (p.get("fin") or "9999")[:4]
            if ini <= anio and fin >= anio:
                return True
        return False

    idx = {}
    for r in registro:
        if not vigente(r):
            continue
        datos = {"provincia": r.get("provincia", "?"),
                 "bloque": r.get("partido", "?")}
        for k in claves(r["nombre"]):
            idx.setdefault(k, datos)
    return idx


def buscar(nombre, indice):
    for k in claves(nombre):
        if k in indice:
            return indice[k]
    return OVERRIDE.get(normalizar(nombre))


# ---------------------------------------------------------------------------
# Programa principal
# ---------------------------------------------------------------------------
def main():
    print(f"Bajando votaciones y registro de senadores ({ANIO})...")
    actas = bajar_json(API_ACTAS)
    registro = bajar_json(API_SENADORES)

    indice = construir_indice(registro, ANIO)

    # Contar presencias por senador en las votaciones del año elegido
    conteo = collections.defaultdict(lambda: {"presente": 0, "total": 0})
    votaciones = 0
    for a in actas:
        if (a.get("fecha", "") or "")[:4] != str(ANIO):
            continue
        votaciones += 1
        for v in a.get("votos", []):
            n = v["nombre"]
            conteo[n]["total"] += 1
            if v.get("voto") != "ausente":     # presente = cualquier cosa != ausente
                conteo[n]["presente"] += 1

    minimo = int(votaciones * UMBRAL_PARTICIPACION)

    filas = []
    for nombre, c in conteo.items():
        if c["total"] < minimo:                # descarta mandatos parciales
            continue
        info = buscar(nombre, indice) or {"provincia": "?", "bloque": "?"}
        pct = round(100 * c["presente"] / c["total"], 1) if c["total"] else 0.0
        filas.append({
            "nombre": nombre,
            "provincia": info["provincia"],
            "bloque": info["bloque"],
            "presente": c["presente"],
            "total": c["total"],
            "presentismo": pct,
        })

    filas.sort(key=lambda f: f["presentismo"])   # de menor a mayor presentismo
    promedio = round(sum(f["presentismo"] for f in filas) / len(filas), 1) if filas else 0

    salida = {
        "actualizado": datetime.date.today().isoformat(),
        "anio": ANIO,
        "total_votaciones": votaciones,
        "presentismo_promedio": promedio,
        "cantidad_senadores": len(filas),
        "senadores": filas,
    }

    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)

    print(f"Listo -> {SALIDA}")
    print(f"  Votaciones {ANIO}: {votaciones}")
    print(f"  Senadores rankeados: {len(filas)}  (umbral: >= {minimo} votaciones)")
    print(f"  Presentismo promedio: {promedio}%")
    if filas:
        peor = filas[0]
        print(f"  Menor presentismo: {peor['nombre']} ({peor['presentismo']}%)")


if __name__ == "__main__":
    main()
