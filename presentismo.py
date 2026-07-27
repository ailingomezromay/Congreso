"""
Observatorio de Presentismo - Cámara de Diputados de la Nación (Argentina)
==========================================================================

Calcula, para un año dado, cuántas veces cada diputado/a estuvo PRESENTE
en las votaciones nominales, y arma un ranking.

Fuente de datos: API pública ArgentinaDatos
    https://api.argentinadatos.com/v1/diputados/actas/<AÑO>

Metodología (documentada a propósito, para que sea auditable):
- Cada "acta" es una votación nominal. Trae la lista de los 257 diputados
  y cómo votó cada uno: afirmativo / negativo / abstencion / presidente / ausente.
- Consideramos PRESENTE a quien tiene cualquier tipoVoto distinto de "ausente"
  (incluye al que preside la sesión, que está en el recinto pero no vota).
- Presentismo del diputado = presentes / (votaciones en las que figura).
- Para que el ranking sea JUSTO, solo incluimos a quienes figuran en al menos
  un porcentaje mínimo de las votaciones del año (UMBRAL). Así no mezclamos a
  quienes asumieron o cesaron a mitad de período con quienes estuvieron todo el año.

Uso:
    python presentismo.py 2025
"""

import sys
import json
from datetime import date
from collections import defaultdict

import requests
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # backend sin ventana, para poder guardar el PNG en un servidor
import matplotlib.pyplot as plt

API_BASE = "https://api.argentinadatos.com/v1"
UMBRAL_MINIMO = 0.5  # el diputado debe figurar en >=50% de las votaciones para entrar al ranking


def descargar_actas(anio: int) -> list:
    """Descarga todas las votaciones (actas) de un año desde la API."""
    url = f"{API_BASE}/diputados/actas/{anio}"
    print(f"Descargando {url} ...")
    respuesta = requests.get(url, timeout=60)
    respuesta.raise_for_status()  # si el servidor responde con error, cortamos acá
    actas = respuesta.json()
    print(f"  -> {len(actas)} votaciones encontradas para {anio}")
    return actas


def calcular_presentismo(actas: list, umbral: float = UMBRAL_MINIMO) -> pd.DataFrame:
    """Recibe la lista de actas y devuelve un DataFrame ordenado por presentismo."""
    total_votaciones = len(actas)

    # Acumulamos, por diputado, cuántas veces estuvo presente y en cuántas figura.
    conteo = defaultdict(lambda: {"presente": 0, "total": 0})
    for acta in actas:
        for voto in acta["votos"]:
            nombre = voto["diputado"].strip()
            if not nombre or nombre == ",":
                continue  # descartamos nombres vacíos (basura de parseo del origen)
            conteo[nombre]["total"] += 1
            if voto["tipoVoto"] != "ausente":
                conteo[nombre]["presente"] += 1

    filas = []
    for nombre, c in conteo.items():
        # Filtro de justicia: solo entra quien figura en suficientes votaciones.
        if c["total"] < umbral * total_votaciones:
            continue
        filas.append({
            "diputado": nombre,
            "presentes": c["presente"],
            "ausentes": c["total"] - c["presente"],
            "votaciones": c["total"],
            "presentismo_%": round(c["presente"] / c["total"] * 100, 1),
        })

    df = pd.DataFrame(filas).sort_values("presentismo_%", ascending=True)
    return df.reset_index(drop=True)


def graficar(df: pd.DataFrame, anio: int, n: int = 15) -> str:
    """Grafica los N diputados con MENOR presentismo y guarda un PNG."""
    peores = df.head(n).iloc[::-1]  # invertimos para que el peor quede arriba

    fig, ax = plt.subplots(figsize=(10, 8))
    barras = ax.barh(peores["diputado"], peores["presentismo_%"], color="#c0392b")
    ax.bar_label(barras, fmt="%.1f%%", padding=4, fontsize=9)

    ax.set_xlim(0, 100)
    ax.set_xlabel("Presentismo (%)")
    ax.set_title(
        f"Diputados con menor presentismo en votaciones — {anio}\n"
        f"(sobre {df['votaciones'].max()} votaciones nominales)",
        fontsize=13, fontweight="bold",
    )
    ax.grid(axis="x", linestyle=":", alpha=0.5)
    fig.text(0.01, 0.01, "Fuente: API ArgentinaDatos (datos oficiales HCDN)",
             fontsize=8, color="gray")
    fig.tight_layout()

    salida = f"presentismo_diputados_{anio}.png"
    fig.savefig(salida, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return salida


def main():
    anio = int(sys.argv[1]) if len(sys.argv) > 1 else 2025

    actas = descargar_actas(anio)
    df = calcular_presentismo(actas)

    csv = f"presentismo_diputados_{anio}.csv"
    df.to_csv(csv, index=False, encoding="utf-8-sig")  # utf-8-sig para que Excel lea bien los acentos
    png = graficar(df, anio)

    # Archivo liviano que consume la web (index.html). Ya viene ordenado y calculado.
    datos = {
        "anio": anio,
        "actualizado": date.today().isoformat(),
        "total_votaciones": int(df["votaciones"].max()),
        "ranking": df.to_dict(orient="records"),
    }
    with open("datos.json", "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False)

    print(f"\nListo. Generé:\n  - {csv}  ({len(df)} diputados)\n  - {png}\n  - datos.json (para la web)")
    print("\nTop 5 con menor presentismo:")
    print(df.head(5).to_string(index=False))


if __name__ == "__main__":
    main()
