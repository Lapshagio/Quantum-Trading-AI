import ccxt
import pandas as pd
import time


def descargar_datos_historicos(simbolo, temporalidad, fecha_inicio_str):
    print(f"Conectando a Binance para descargar historial masivo de {simbolo}...")
    exchange = ccxt.binance({"enableRateLimit": True})

    # Convertir la fecha de texto a milisegundos para la API
    desde_timestamp = exchange.parse8601(fecha_inicio_str)
    todos_los_datos = []

    print("Iniciando descarga por bloques (Esto tomará unos segundos)...")
    while True:
        # Descargamos paquetes de 1000 en 1000
        velas = exchange.fetch_ohlcv(
            simbolo, temporalidad, since=desde_timestamp, limit=1000
        )

        if len(velas) == 0:
            break  # Si ya no hay velas nuevas, salimos del bucle

        todos_los_datos.extend(velas)
        print(f"Descargadas {len(todos_los_datos)} velas acumuladas...")

        # Actualizamos el timestamp para que el siguiente bloque empiece donde terminó este
        desde_timestamp = velas[-1][0] + 1

        # Pausa de seguridad de medio segundo para que Binance no nos banee la IP
        time.sleep(0.5)

        if len(velas) < 1000:
            break  # Llegamos al día de hoy

    # Convertimos a formato Pandas
    df = pd.DataFrame(
        todos_los_datos, columns=["timestamp", "open", "high", "low", "close", "volume"]
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")

    # Lo guardamos con un nombre nuevo para no pisar el viejo
    nombre_archivo = "BTC_USDT_1h_masivo.csv"
    df.to_csv(nombre_archivo, index=False)

    print(f"\n¡Éxito rotundo! Descargadas {len(df)} velas históricas.")
    print(f"Archivo guardado como: {nombre_archivo}")


if __name__ == "__main__":
    # Arrancamos desde enero de 2023
    descargar_datos_historicos("BTC/USDT", "1h", "2023-01-01T00:00:00Z")
