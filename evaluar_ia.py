import pandas as pd
from stable_baselines3 import PPO
from entorno_trading import EntornoTradingSMC


def evaluar_modelo_realista():
    print("Cargando el mapa de datos...")
    df = pd.read_csv("BTC_USDT_1h_masivo_smc.csv").fillna(0)

    entorno = EntornoTradingSMC(df)
    print("Despertando a la IA...")
    modelo = PPO.load("modelo_smc_v1")

    obs, _ = entorno.reset()
    terminado = False

    print("\n--- INICIANDO BACKTESTING REALISTA ---")
    print("La IA está operando y aguantando las posiciones. Por favor, espera...")

    while not terminado:
        accion, _ = modelo.predict(obs, deterministic=True)
        obs, recompensa, terminado, truncado, info = entorno.step(accion)

    print("\n" + "=" * 40)
    print("      RESULTADOS DEL BOT SMC REAL")
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
