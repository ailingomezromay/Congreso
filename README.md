# Observatorio de Presentismo — Cámara de Diputados 🇦🇷

Ranking del presentismo de cada diputado/a de la Nación en las **votaciones nominales**, calculado a partir de datos públicos y **actualizado automáticamente** una vez por semana.

![Ranking de presentismo](presentismo_diputados_2025.png)

## Qué mide

Cuántas veces cada diputado/a estuvo **presente** en las votaciones nominales del año, sobre el total de votaciones en las que le tocaba estar.

- Los datos completos, diputado por diputado, están en el CSV: [`presentismo_diputados_2025.csv`](presentismo_diputados_2025.csv).
- El gráfico muestra solo a los 15 con menor presentismo (el resto está en el CSV).

## Fuente de datos

API pública [ArgentinaDatos](https://argentinadatos.com/), que a su vez toma las votaciones del portal oficial de la [Honorable Cámara de Diputados de la Nación](https://votaciones.hcdn.gob.ar/). Endpoint usado:

```
https://api.argentinadatos.com/v1/diputados/actas/<AÑO>
```

## Metodología (importante)

Este proyecto está pensado para ser **auditable**: cualquiera puede revisar el código y reproducir los números. Las decisiones que se tomaron:

1. **Qué cuenta como "presente".** Cada votación registra, para los 257 diputados, un `tipoVoto`: `afirmativo`, `negativo`, `abstencion`, `presidente` o `ausente`. Se considera **presente** a todo `tipoVoto` distinto de `ausente` (incluye a quien preside la sesión, que está en el recinto aunque no vote).

2. **Cómo se calcula el porcentaje.** Para cada diputado/a:

   ```
   presentismo (%) = presentes / votaciones en las que figura × 100
   ```

3. **Umbral de inclusión (para que sea justo).** Solo entran al ranking quienes figuran en **al menos el 50%** de las votaciones del año. Esto evita comparar a quien asumió o cesó a mitad de período (y por eso aparece en pocas votaciones) con quien estuvo el año entero. El umbral se puede cambiar en la variable `UMBRAL_MINIMO` de `presentismo.py`.

4. **Limpieza.** Se descartan registros con nombre vacío que a veces aparecen en el origen.

### Qué NO mide

- **No** mide el trabajo en comisiones ni la presencia en sesiones sin votación nominal, solo las votaciones nominales.
- Estar "presente" no dice nada sobre el **sentido** del voto.
- Un presentismo bajo puede tener causas justificadas (licencias, salud, etc.). El dato es un punto de partida, no una conclusión.

## Cómo correrlo localmente

```bash
pip install -r requirements.txt
python presentismo.py 2025     # o el año que quieras
```

Genera dos archivos: el CSV con todos los diputados y el PNG con el gráfico.

## Actualización automática

El workflow de GitHub Actions (`.github/workflows/actualizar.yml`) corre todos los lunes, recalcula el presentismo del año en curso y commitea los archivos actualizados. También se puede disparar a mano desde la pestaña **Actions** del repositorio.

## Licencia

Datos de dominio público. Código bajo licencia MIT.
