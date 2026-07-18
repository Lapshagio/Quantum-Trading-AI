import pandas as pd
import numpy as np
import os
from sb3_contrib import RecurrentPPO
from entorno_trading import EntornoTradingSMC


def evaluar_modelo_realista():
    print("Cargando el mapa de datos (15 minutos)...")
    # Apuntamos a la base de datos correcta dentro de la carpeta datasets
    ruta_datos = os.path.join("datasets", "BTC_USDT_15m_entrenamiento.csv")

    try:
        df = pd.read_csv(ruta_datos).fillna(0)
    except FileNotFoundError:
        print(f"Error: No se encuentra el archivo {ruta_datos}. Verifica el nombre.")
        return

    entorno = EntornoTradingSMC(df)

    print("Despertando a la IA V8 (LSTM)...")
    try:
        # Cargamos el modelo V8 agresivo recién salido del horno
        modelo = RecurrentPPO.load("modelo_smc_v8_lstm_agresivo")
    except Exception as e:
        print(f"Error al cargar el modelo: {e}")
        return

    obs, _ = entorno.reset()
    terminado = False

    # Variables vitales para la memoria LSTM
    estado_lstm = None
    inicio_episodio = np.ones((1,), dtype=bool)

    print("\n--- INICIANDO BACKTESTING REALISTA ---")
    print("La IA está operando y aguantando las posiciones. Por favor, espera...")

    while not terminado:
        # Aquí deterministic=True es CORRECTO, porque queremos evaluar la estrategia
        # pura de la IA sin aleatoriedades (a diferencia del bot en vivo).
        accion, estado_lstm = modelo.predict(
            obs, state=estado_lstm, episode_start=inicio_episodio, deterministic=True
        )
        obs, recompensa, terminado, truncado, info = entorno.step(accion)

        # Una vez dado el primer paso, el episodio ya no está en el inicio
        inicio_episodio = np.zeros((1,), dtype=bool)

    print("\n" + "=" * 40)
    print("      RESULTADOS DEL BOT SMC (V8 LSTM)")
    print("=" * 40)
    print(f"Capital Inicial: ${entorno.capital_inicial:.2f}")
    print(f"Capital Final:   ${info['balance']:.2f}")

    beneficio = info["balance"] - entorno.capital_inicial
    print(
        f"Beneficio Neto:  ${beneficio:.2f} ({(beneficio/entorno.capital_inicial)*100:.2f}%)"
    )

    print("-" * 40)
    print(f"Trades Totales (Cerrados): {info['totales']}")
    if info["totales"] > 0:
        win_rate = (info["ganados"] / info["totales"]) * 100
        print(f"Trades Ganados:  {info['ganados']}")
        print(f"Trades Perdidos: {info['perdidos']}")
        print(f"Win Rate:        {win_rate:.2f}%")
    print("=" * 40)


if __name__ == "__main__":
    evaluar_modelo_realista()
