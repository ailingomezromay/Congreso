"""
Observatorio de Presentismo - Camara de Diputados de la Nacion (Argentina)
==========================================================================

Calcula, para un anio dado, cuantas veces cada diputado estuvo PRESENTE en las
votaciones nominales, con su BLOQUE, y arma un ranking.

Fuente: API publica ArgentinaDatos
    https://api.argentinadatos.com/v1/diputados/actas/<ANIO>   (votaciones)
    https://api.argentinadatos.com/v1/diputados/diputados      (bloques, provincia)

Uso:
    python presentismo.py 2025
"""

import sys
import json
import re
import unicodedata
from datetime import date
from collections import defaultdict

import requests
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

API_BASE = "https://api.argentinadatos.com/v1"
UMBRAL_MINIMO = 0.5


# ---------------------------------------------------------------- descargas
def descargar(url: str):
    print(f"Descargando {url} ...")
    r = requests.get(url, timeout=90)
    r.raise_for_status()
    return r.json()


# ---------------------------------------------------------- cruce con bloque
def _norm(s: str) -> str:
    """Normaliza un nombre: sin acentos, sin apodos entre comillas, minusculas."""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r'"[^"]*"', "", s)          # saca apodos: Ali, Ernesto "Pipi"
    return re.sub(r"\s+", " ", s.lower().strip())


def construir_lookup(diputados: list, anio: int):
    """Devuelve una funcion que, dado 'Apellido, Nombre', encuentra su registro."""
    por_full, por_apellido = {}, defaultdict(list)
    for d in diputados:
        if d["periodoMandato"]["fin"][:10] < f"{anio}-01-01":
            continue  # solo mandatos activos en el anio analizado
        por_full[_norm(f"{d['apellido']}, {d['nombre']}")] = d
        por_apellido[_norm(d["apellido"])].append(d)

    def buscar(nombre_voto: str):
        n = _norm(nombre_voto)
        if n in por_full:
            return por_full[n]
        apellido = n.split(",")[0].strip()
        primer = n.split(",")[1].strip().split(" ")[0] if "," in n else ""
        candidatos = por_apellido.get(apellido, [])
        for c in candidatos:                       # respaldo: apellido + 1er nombre
            if _norm(c["nombre"]).startswith(primer):
                return c
        if len(candidatos) == 1:                   # respaldo: apellido unico
            return candidatos[0]
        return None

    return buscar


# ----------------------------------------------------------- calculo central
def calcular_presentismo(actas: list, buscar_bloque=None, umbral=UMBRAL_MINIMO) -> pd.DataFrame:
    total = len(actas)
    conteo = defaultdict(lambda: {"presente": 0, "total": 0})
    for acta in actas:
        for voto in acta["votos"]:
            nombre = voto["diputado"].strip()
            if not nombre or nombre == ",":
                continue
            conteo[nombre]["total"] += 1
            if voto["tipoVoto"] != "ausente":
                conteo[nombre]["presente"] += 1

    filas = []
    for nombre, c in conteo.items():
        if c["total"] < umbral * total:
            continue
        reg = buscar_bloque(nombre) if buscar_bloque else None
        filas.append({
            "diputado": nombre,
            "bloque": reg["bloque"] if reg else "Sin dato",
            "provincia": reg["provincia"] if reg else "",
            "presentes": c["presente"],
            "ausentes": c["total"] - c["presente"],
            "votaciones": c["total"],
            "presentismo_%": round(c["presente"] / c["total"] * 100, 1),
        })
    return pd.DataFrame(filas).sort_values("presentismo_%").reset_index(drop=True)


# ---------------------------------------------------------------- grafico PNG
def graficar(df: pd.DataFrame, anio: int, n: int = 15) -> str:
    peores = df.head(n).iloc[::-1]
    fig, ax = plt.subplots(figsize=(10, 8))
    barras = ax.barh(peores["diputado"], peores["presentismo_%"], color="#D81E5B")
    ax.bar_label(barras, fmt="%.1f%%", padding=4, fontsize=9)
    ax.set_xlim(0, 100)
    ax.set_xlabel("Presentismo (%)")
    ax.set_title(f"Diputados con menor presentismo — {anio}\n"
                 f"(sobre {df['votaciones'].max()} votaciones nominales)",
                 fontsize=13, fontweight="bold")
    ax.grid(axis="x", linestyle=":", alpha=0.5)
    fig.text(0.01, 0.01, "Fuente: API ArgentinaDatos (datos oficiales HCDN)",
             fontsize=8, color="gray")
    fig.tight_layout()
    salida = f"presentismo_diputados_{anio}.png"
    fig.savefig(salida, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return salida


# ------------------------------------------------------------------ programa
def main():
    anio = int(sys.argv[1]) if len(sys.argv) > 1 else 2025

    actas = descargar(f"{API_BASE}/diputados/actas/{anio}")
    diputados = descargar(f"{API_BASE}/diputados/diputados")
    buscar = construir_lookup(diputados, anio)

    df = calcular_presentismo(actas, buscar)

    csv = f"presentismo_diputados_{anio}.csv"
    df.to_csv(csv, index=False, encoding="utf-8-sig")
    png = graficar(df, anio)

    datos = {
        "anio": anio,
        "actualizado": date.today().isoformat(),
        "total_votaciones": int(df["votaciones"].max()),
        "ranking": df.to_dict(orient="records"),
    }
    with open("datos.json", "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False)

    print(f"\nListo:\n  - {csv} ({len(df)} diputados)\n  - {png}\n  - datos.json")
    sin = (df["bloque"] == "Sin dato").sum()
    print(f"Diputados sin bloque identificado: {sin}")


if __name__ == "__main__":
    main()
