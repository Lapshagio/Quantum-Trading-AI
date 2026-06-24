import pandas as pd
from sb3_contrib import RecurrentPPO
from entorno_trading import EntornoTradingSMC
import os

print("Iniciando la forja del Cerebro V8 (Memoria Optimizada LSTM)...")

# 1. Apuntamos a la base de datos unificada
ruta_datos = os.path.join("datasets", "BTC_USDT_15m_entrenamiento.csv")
df = pd.read_csv(ruta_datos).fillna(0)

# 2. Cargamos el entorno de 9 dimensiones (Riesgo + Fractalidad)
env = EntornoTradingSMC(df)

# =========================================================================
# ⚙️ HIPERPARÁMETROS DE CONVERGENCIA AVANZADA (ANTI-BORRADO LSTM)
# =========================================================================
# Reducimos la tasa de aprendizaje para estabilizar las celdas de memoria
# Aumentamos los pasos a 1.500.000 para garantizar ~15 épocas completas de estudio
hiperparametros = {
    "learning_rate": 5e-5,
    "n_steps": 2048,
    "batch_size": 256,
    "verbose": 1,
    "seed": 42,
}

print("Forjando conexiones sinápticas temporales estables...")
print("Iterando ciclos evolutivos sobre la base de datos histórica de 3 años.")

# Inicializamos el modelo con la política recurrente y nuestro diccionario optimizado
modelo = RecurrentPPO("MlpLstmPolicy", env, **hiperparametros)

# Lanzamos el entrenamiento intensivo
modelo.learn(total_timesteps=1500000)

# 4. Guardamos el nuevo modelo V8 protegiendo la versión anterior
nombre_modelo_salida = "modelo_smc_v8_lstm_agresivo"
modelo.save(nombre_modelo_salida)

print(f"¡Éxito rotundo! {nombre_modelo_salida} guardado correctamente.")
print("Arquitectura lista para pruebas de estrés en la terminal en vivo.")
