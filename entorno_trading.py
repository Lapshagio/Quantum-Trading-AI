import gymnasium as gym
from gymnasium import spaces
import pandas as pd
import numpy as np


class EntornoTradingSMC(gym.Env):
    def __init__(self, df):
        super(EntornoTradingSMC, self).__init__()
        self.df = df
        self.max_pasos = len(df) - 1
        self.capital_inicial = 10000.0
        # Expandido a 9 variables (Añadido el ATR Normalizado)
        self.observation_space = spaces.Box(low=0, high=1, shape=(9,), dtype=np.float32)
        self.action_space = spaces.Discrete(3)

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.paso_actual = 0
        self.balance = self.capital_inicial
        self.posicion_abierta = False
        self.tipo_posicion = 0
        self.precio_sl = 0.0
        self.precio_tp = 0.0
        self.trades_totales = 0
        self.trades_ganados = 0
        self.trades_perdidos = 0
        return self._obtener_observacion(), {}

    def _obtener_observacion(self):
        fila = self.df.iloc[self.paso_actual]
        # Normalizamos la volatilidad para que la IA la entienda (porcentaje del precio)
        atr_normalizado = (
            (fila["ATR"] / fila["close"]) * 100 if fila["close"] > 0 else 0.0
        )

        obs = np.array(
            [
                float(fila["Rotura_Alcista_15m"]),
                float(fila["Rotura_Bajista_15m"]),
                float(fila["FVG_Alcista"]),
                float(fila["FVG_Bajista"]),
                float(fila["Rotura_Alcista_1h"]),
                float(fila["Rotura_Bajista_1h"]),
                float(fila["Sesion_NY"]),
                float(atr_normalizado),
                float(self.posicion_abierta),
            ],
            dtype=np.float32,
        )
        return obs

    def step(self, action):
        fila = self.df.iloc[self.paso_actual]
        recompensa = 0.0
        atr_actual = fila["ATR"]

        if self.posicion_abierta:
            # Riesgo real calculado en base a la distancia del SL
            distancia_sl = (
                abs(self.precio_sl - self.precio_entrada)
                if hasattr(self, "precio_entrada")
                else atr_actual * 1.5
            )
            riesgo_dolares = self.balance * 0.01  # Arriesgamos un 1% de la cuenta
            beneficio_dolares = riesgo_dolares * 2.0  # Buscamos un 2% (Ratio 1:2)

            if self.tipo_posicion == 1:
                if fila["low"] <= self.precio_sl:
                    self.balance -= riesgo_dolares
                    recompensa = -1.0  # Castigo estricto de 1R
                    self.posicion_abierta = False
                    self.trades_totales += 1
                    self.trades_perdidos += 1
                elif fila["high"] >= self.precio_tp:
                    self.balance += beneficio_dolares
                    recompensa = 2.0  # Premio exacto de 2R
                    self.posicion_abierta = False
                    self.trades_totales += 1
                    self.trades_ganados += 1

            elif self.tipo_posicion == 2:
                if fila["high"] >= self.precio_sl:
                    self.balance -= riesgo_dolares
                    recompensa = -1.0  # Castigo estricto de 1R
                    self.posicion_abierta = False
                    self.trades_totales += 1
                    self.trades_perdidos += 1
                elif fila["low"] <= self.precio_tp:
                    self.balance += beneficio_dolares
                    recompensa = 2.0  # Premio exacto de 2R
                    self.posicion_abierta = False
                    self.trades_totales += 1
                    self.trades_ganados += 1

        else:
            if action == 1 and fila["FVG_Alcista"] and fila["Sesion_NY"]:
                recompensa = (
                    0.0  # CERO recompensa por entrar. El premio está en la salida.
                )
                self.posicion_abierta = True
                self.tipo_posicion = 1
                self.precio_entrada = fila["close"]
                self.precio_sl = self.precio_entrada - (1.5 * atr_actual)
                self.precio_tp = self.precio_entrada + (3.0 * atr_actual)

            elif action == 2 and fila["FVG_Bajista"] and fila["Sesion_NY"]:
                recompensa = (
                    0.0  # CERO recompensa por entrar. El premio está en la salida.
                )
                self.posicion_abierta = True
                self.tipo_posicion = 2
                self.precio_entrada = fila["close"]
                self.precio_sl = self.precio_entrada + (1.5 * atr_actual)
                self.precio_tp = self.precio_entrada - (3.0 * atr_actual)

            elif action in [1, 2]:
                recompensa = (
                    -1.0
                )  # Castigo duro por inventarse operaciones fuera de SMC
            elif (
                action == 0
                and (fila["FVG_Alcista"] or fila["FVG_Bajista"])
                and fila["Sesion_NY"]
            ):
                recompensa = (
                    -0.5
                )  # Castigo leve por cobardía (no entrar cuando hay un setup válido)
            elif action == 0:
                recompensa = 0.0  # Quedarse fuera cuando no hay nada es perfecto. Sin penalización.

        self.paso_actual += 1
        terminado = self.paso_actual >= self.max_pasos
        if self.balance <= 0:
            terminado = True
            recompensa = -100.0  # Castigo masivo por quemar la cuenta de fondeo

        info = {
            "balance": self.balance,
            "totales": self.trades_totales,
            "ganados": self.trades_ganados,
            "perdidos": self.trades_perdidos,
        }
        return self._obtener_observacion(), recompensa, terminado, False, info
