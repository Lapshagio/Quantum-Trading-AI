import ccxt
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import time
import os
from datetime import datetime, timezone
from sb3_contrib import RecurrentPPO
from procesar_datos import procesar_datos_smc

# ==========================================
# ⚙️ CONFIGURACIÓN DE PLATAFORMAS
# ==========================================
SIMBOLO_BINANCE = "BTC/USDT"
SIMBOLO_MT5 = "BTCUSD"  # Depende del broker de fondeo (puede ser BTCUSD.pro, BTCUSD..)


def inicializar_sistemas():
    print("🤖 Conectando Radar de Binance...")
    binance = ccxt.binance()

    print("📈 Conectando Brazo Ejecutor MetaTrader 5...")
    if not mt5.initialize():
        print(f"❌ Error crítico inicializando MT5: {mt5.last_error()}")
        return None, None

    print("✅ Conexión bidireccional establecida con éxito.")
    return binance, mt5


def obtener_precio_y_spread_mt5(simbolo):
    """Lee las cotizaciones en tiempo real del broker de fondeo"""
    ticker = mt5.symbol_info_tick(simbolo)
    if ticker is None:
        print(f"❌ No se pudo obtener información del símbolo {simbolo} en MT5")
        return None, None, None

    precio_bid = ticker.bid
    precio_ask = ticker.ask
    spread_local = precio_ask - precio_bid
    return precio_bid, precio_ask, spread_local


def enviar_orden_mt5(tipo_operacion, precio_entrada, distancia_sl, distancia_tp):
    """
    Inyecta la orden directamente en el servidor de la empresa de fondeo
    mapeando las distancias porcentuales calculadas por el oráculo
    """
    bid, ask, _ = obtener_precio_y_spread_mt5(SIMBOLO_MT5)
    if bid is None:
        return

    # Determinar precios de ejecución locales del broker
    if tipo_operacion == "COMPRA":
        precio_ejecucion = ask
        sl_local = precio_ejecucion - distancia_sl
        tp_local = precio_ejecucion + distancia_tp
        tipo_orden = mt5.ORDER_TYPE_BUY
    else:
        precio_ejecucion = bid
        sl_local = precio_ejecucion + distancia_sl
        tp_local = precio_ejecucion - distancia_tp
        tipo_orden = mt5.ORDER_TYPE_SELL

    solicitud = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SIMBOLO_MT5,
        "volume": 0.1,  # Loteaje inicial de prueba
        "type": tipo_orden,
        "price": precio_ejecucion,
        "sl": round(sl_local, 2),
        "tp": round(tp_local, 2),
        "deviation": 20,
        "magic": 777,  # Identificador de tu IA V7
        "comment": "IA SMC V7 Quantum Oracle",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    resultado = mt5.order_send(solicitud)
    if resultado.retcode != mt5.TRADE_RETCODE_DONE:
        print(
            f"❌ Orden rechazada por el broker de MT5: {resultado.comment} (Código: {resultado.retcode})"
        )
    else:
        print(f"🚀 ¡ORDEN EJECUTADA EN CUENTA DE FONDEO!")
        print(f"   • Tipo: {tipo_operacion} | Entrada MT5: ${precio_ejecucion}")
        print(f"   • SL Ajustado: ${sl_local:.2f} | TP Ajustado: ${tp_local:.2f}")


def ejecutar_puente_cuant():
    binance, _ = inicializar_sistemas()
    if binance is None:
        return

    try:
        modelo = RecurrentPPO.load("modelo_smc_v6_lstm")
        print("🧠 Cerebro Recurrente LSTM acoplado al puente.")
    except:
        print("❌ Error: Asegúrate de tener 'modelo_smc_v6_lstm.zip' en la raíz.")
        return

    estado_lstm = None
    inicio_episodio = np.ones((1,), dtype=bool)
    ultima_vela_id = None

    while True:
        try:
            # 1. El radar lee la actividad pura en Binance
            velas_15m = binance.fetch_ohlcv(SIMBOLO_BINANCE, "15m", limit=100)
            velas_1h = binance.fetch_ohlcv(SIMBOLO_BINANCE, "1h", limit=50)

            df_15m = pd.DataFrame(
                velas_15m,
                columns=["timestamp", "open", "high", "low", "close", "volume"],
            )
            df_1h = pd.DataFrame(
                velas_1h,
                columns=["timestamp", "open", "high", "low", "close", "volume"],
            )

            vela_actual_id = df_15m.iloc[-1]["timestamp"]
            precio_binance = float(df_15m.iloc[-1]["close"])

            if vela_actual_id != ultima_vela_id:
                # 2. Procesamiento de indicadores SMC y ATR
                df_15m.to_csv("datos_vivo_15m.csv", index=False)
                procesar_datos_smc("datos_vivo_15m.csv")
                df_15m_smc = pd.read_csv("datos_vivo_15m_smc.csv").fillna(0)
                ultima_vela_15m = df_15m_smc.iloc[-1]

                df_1h.to_csv("datos_vivo_1h.csv", index=False)
                procesar_datos_smc("datos_vivo_1h.csv")
                df_1h_smc = pd.read_csv("datos_vivo_1h_smc.csv").fillna(0)
                ultima_vela_1h = df_1h_smc.iloc[-1]

                atr_binance = float(ultima_vela_15m["ATR"])
                atr_normalizado = (atr_binance / precio_binance) * 100

                observacion = np.array(
                    [
                        float(ultima_vela_15m["Rotura_Alcista"]),
                        float(ultima_vela_15m["Rotura_Bajista"]),
                        float(ultima_vela_15m["FVG_Alcista"]),
                        float(ultima_vela_15m["FVG_Bajista"]),
                        float(ultima_vela_1h["Rotura_Alcista"]),
                        float(ultima_vela_1h["Rotura_Bajista"]),
                        float(ultima_vela_15m["Sesion_NY"]),
                        float(atr_normalizado),
                        0.0,  # Posición abierta gestionada localmente por el script
                    ],
                    dtype=np.float32,
                )

                # 3. Inferencia de la IA
                accion, estado_lstm = modelo.predict(
                    observacion,
                    state=estado_lstm,
                    episode_start=inicio_episodio,
                    deterministic=True,
                )
                inicio_episodio = np.zeros((1,), dtype=bool)

                # 4. Traducción y Emparejamiento de Riesgo para MT5
                if accion in [1, 2]:
                    # Traducimos la volatilidad del oráculo en distancias brutas en dólares
                    distancia_sl_dolares = 1.5 * atr_binance
                    distancia_tp_dolares = 3.0 * atr_binance

                    tipo_op = "COMPRA" if accion == 1 else "VENTA"
                    print(f"🎯 Señal detectada por el Oráculo para: {tipo_op}")

                    # Ejecutamos la orden mapeando los valores en MetaTrader 5
                    enviar_orden_mt5(
                        tipo_op,
                        precio_binance,
                        distancia_sl_dolares,
                        distancia_tp_dolares,
                    )

                ultima_vela_id = vela_actual_id

            time.sleep(10)
        except Exception as e:
            print(f"⚠️ Alerta en el bucle del puente: {e}")
            time.sleep(5)


if __name__ == "__main__":
    ejecutar_puente_cuant()
