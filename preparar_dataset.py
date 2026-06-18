import os
import shutil
import pandas as pd
from procesar_datos import procesar_datos_smc

print("Iniciando inyección Fractal SMC en las bases de datos masivas...")

# ==========================================
# 📂 RUTAS DE ARCHIVOS (Mapeo exacto de tu PC)
# ==========================================
# El 15m está DENTRO de la carpeta 'datasets'
archivo_15m_crudo = os.path.join("datasets", "BTC_USDT_15m_masivo.csv")
# El 1h está SUELTO en la raíz principal
archivo_1h_crudo = "BTC_USDT_1h_masivo.csv"
# El archivo unificado lo guardamos en 'datasets'
archivo_final = os.path.join("datasets", "BTC_USDT_15m_entrenamiento.csv")

try:
    # 1. Procesar capa de 15 minutos
    print("Procesando histórico de 15 minutos...")
    shutil.copy(archivo_15m_crudo, "temp_15m.csv")
    procesar_datos_smc("temp_15m.csv")
    df_15m = pd.read_csv("temp_15m_smc.csv")

    # 2. Procesar capa de 1 hora
    print("Procesando histórico de 1 hora...")
    shutil.copy(archivo_1h_crudo, "temp_1h.csv")
    procesar_datos_smc("temp_1h.csv")
    df_1h = pd.read_csv("temp_1h_smc.csv")

    # Asegurar orden temporal estricto para la alineación asof
    df_15m["timestamp"] = pd.to_datetime(df_15m["timestamp"])
    df_1h["timestamp"] = pd.to_datetime(df_1h["timestamp"])
    df_15m = df_15m.sort_values("timestamp")
    df_1h = df_1h.sort_values("timestamp")

    # 3. Fusión Cuántica (Alineación Multi-Timeframe)
    print("Alineando dimensiones temporales (pd.merge_asof)...")
    df_1h_recortado = df_1h[["timestamp", "Rotura_Alcista", "Rotura_Bajista"]]

    df_final = pd.merge_asof(
        df_15m,
        df_1h_recortado,
        on="timestamp",
        suffixes=("_15m", "_1h"),
        direction="backward",
    )

    # 4. Guardar y limpiar infraestructura temporal
    df_final.fillna(0).to_csv(archivo_final, index=False)

    for f in [
        "temp_15m.csv",
        "temp_15m_smc.csv",
        "temp_1h.csv",
        "temp_1h_smc.csv",
    ]:
        if os.path.exists(f):
            os.remove(f)

    print(f"\n¡Éxito total! Base de datos Fractal unificada y lista.")
    print(f"Archivo guardado en: {archivo_final}")
    print(f"Total de datos unificados para entrenamiento: {len(df_final)}")

except Exception as e:
    print(f"Ocurrió un error en el procesamiento: {e}")
