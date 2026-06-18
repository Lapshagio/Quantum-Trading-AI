import ccxt
import pandas as pd
import time
import os
from datetime import datetime, timedelta

print("Iniciando descarga masiva de datos institucionales (15 minutos)...")

# ==========================================
# 📂 ORGANIZACIÓN DE DIRECTORIOS
# ==========================================
CARPETA_DATOS = "datasets"
# Crea la carpeta automáticamente si no existe en tu espacio de trabajo
os.makedirs(CARPETA_DATOS, exist_ok=True)

# Configuración del mercado de Binance
exchange = ccxt.binance({"enableRateLimit": True})
symbol = "BTC/USDT"
timeframe = "15m"

# Retrocedemos exactamente 3 años en el tiempo (1095 días)
start_date = datetime.utcnow() - timedelta(days=1095)
since = exchange.parse8601(start_date.strftime("%Y-%m-%dT00:00:00Z"))

all_ohlcv = []

while True:
    try:
        # Descarga de bloques masivos (1000 velas por petición)
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=1000)

        if not ohlcv:
            break

        # Avanzar el puntero de tiempo
        since = ohlcv[-1][0] + 1
        all_ohlcv.extend(ohlcv)

        fecha_legible = exchange.iso8601(ohlcv[-1][0])
        print(
            f"Descargadas {len(all_ohlcv)} velas... Avanzando por la historia: {fecha_legible[:10]}"
        )

        # Condición de parada si alcanzamos los datos de hoy
        if ohlcv[-1][0] >= exchange.milliseconds() - 100000:
            break

        time.sleep(0.5)  # Respetamos el rate limit de Binance para proteger tu IP

    except Exception as e:
        print(f"Error en la red: {e}. Reintentando en 5 segundos...")
        time.sleep(5)

# Procesamiento y limpieza inicial con Pandas
df = pd.DataFrame(
    all_ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"]
)
df = df.drop_duplicates(subset=["timestamp"])

# Guardado ordenado dentro de la carpeta 'datasets'
archivo_salida = os.path.join(CARPETA_DATOS, "BTC_USDT_15m_masivo.csv")
df.to_csv(archivo_salida, index=False)

print(f"\n¡Operación exitosa! Base de datos maestra guardada en '{archivo_salida}'.")
print(f"Total de velas de 15 minutos listas para procesar: {len(df)}")
