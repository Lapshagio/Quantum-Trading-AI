import pandas as pd
from sb3_contrib import RecurrentPPO
from entorno_trading import EntornoTradingSMC
import os

print("Iniciando la forja del Cerebro V6 (Memoria Fotográfica LSTM)...")

# 1. Apuntamos a la base de datos unificada
ruta_datos = os.path.join("datasets", "BTC_USDT_15m_entrenamiento.csv")
df = pd.read_csv(ruta_datos).fillna(0)

# 2. Cargamos el entorno de 9 dimensiones (Riesgo + Fractalidad)
env = EntornoTradingSMC(df)

# 3. Entrenamos la red neuronal recurrente (LSTM)
print(
    "Forjando conexiones sinápticas temporales... Esto requerirá más potencia computacional."
)
# Usamos MlpLstmPolicy para activar las celdas de memoria
modelo = RecurrentPPO("MlpLstmPolicy", env, verbose=1, batch_size=256)
modelo.learn(total_timesteps=100000)

# 4. Guardamos el nuevo modelo V6
modelo.save("modelo_smc_v6_lstm")
print("¡Modelo V6 (LSTM) guardado con éxito! Arquitectura de memoria completada.")
