import pandas as pd
import numpy as np


def procesar_datos_smc(nombre_archivo):
    print(f"Leyendo el archivo {nombre_archivo}...")
    df = pd.read_csv(nombre_archivo)

    print("Calculando Estructura de Mercado (Swings y Roturas)...")
    df["Swing_High"] = (
        (df["high"] > df["high"].shift(1))
        & (df["high"] > df["high"].shift(2))
        & (df["high"] > df["high"].shift(-1))
        & (df["high"] > df["high"].shift(-2))
    )
    df["Swing_Low"] = (
        (df["low"] < df["low"].shift(1))
        & (df["low"] < df["low"].shift(2))
        & (df["low"] < df["low"].shift(-1))
        & (df["low"] < df["low"].shift(-2))
    )

    df["Precio_Swing_High"] = np.where(df["Swing_High"], df["high"], np.nan)
    df["Precio_Swing_Low"] = np.where(df["Swing_Low"], df["low"], np.nan)
    df["Ultimo_High_Confirmado"] = df["Precio_Swing_High"].ffill()
    df["Ultimo_Low_Confirmado"] = df["Precio_Swing_Low"].ffill()

    rotura_alcista_cruda = (df["close"] > df["Ultimo_High_Confirmado"]) & (
        df["close"].shift(1) <= df["Ultimo_High_Confirmado"]
    )
    rotura_bajista_cruda = (df["close"] < df["Ultimo_Low_Confirmado"]) & (
        df["close"].shift(1) >= df["Ultimo_Low_Confirmado"]
    )

    # --- VÁLVULA DE RIESGO ABIERTA (PERFIL AGRESIVO) ---
    df["Rotura_Alcista"] = (
        rotura_alcista_cruda.rolling(window=15, min_periods=1).max().astype(float)
    )
    df["Rotura_Bajista"] = (
        rotura_bajista_cruda.rolling(window=15, min_periods=1).max().astype(float)
    )

    print("Detectando Fair Value Gaps (FVG)...")
    fvg_alcista_crudo = df["low"] > df["high"].shift(2)
    fvg_bajista_crudo = df["high"] < df["low"].shift(2)

    df["FVG_Alcista"] = (
        fvg_alcista_crudo.rolling(window=8, min_periods=1).max().astype(float)
    )
    df["FVG_Bajista"] = (
        fvg_bajista_crudo.rolling(window=8, min_periods=1).max().astype(float)
    )
    # ----------------------------------------------------

    df["Precio_Techo_FVG"] = np.where(
        fvg_alcista_crudo,
        df["low"],
        np.where(fvg_bajista_crudo, df["low"].shift(2), np.nan),
    )
    df["Precio_Suelo_FVG"] = np.where(
        fvg_alcista_crudo,
        df["high"].shift(2),
        np.where(fvg_bajista_crudo, df["high"], np.nan),
    )

    print("Añadiendo el filtro de volumen institucional (NY Session)...")
    if pd.api.types.is_numeric_dtype(df["timestamp"]):
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    else:
        df["timestamp"] = pd.to_datetime(df["timestamp"])

    df["Sesion_NY"] = df["timestamp"].dt.hour.isin([13, 14, 15, 16, 17])

    # ==========================================
    # 7. GESTIÓN DE RIESGO DINÁMICA (ATR)
    # ==========================================
    print("Calculando Volatilidad Dinámica (ATR)...")
    df["H-L"] = df["high"] - df["low"]
    df["H-PC"] = abs(df["high"] - df["close"].shift(1))
    df["L-PC"] = abs(df["low"] - df["close"].shift(1))
    df["TR"] = df[["H-L", "H-PC", "L-PC"]].max(axis=1)
    df["ATR"] = df["TR"].rolling(window=14, min_periods=1).mean().fillna(0)
    df.drop(["H-L", "H-PC", "L-PC", "TR"], axis=1, inplace=True)

    nombre_archivo_procesado = nombre_archivo.replace(".csv", "_smc.csv")
    df.to_csv(nombre_archivo_procesado, index=False)
    print(f"¡Éxito! Datos guardados en: {nombre_archivo_procesado}")


if __name__ == "__main__":
    procesar_datos_smc("BTC_USDT_1h_masivo.csv")
