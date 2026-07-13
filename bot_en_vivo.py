import ccxt
import pandas as pd
import numpy as np
import time
import requests
import os
import json
from datetime import datetime, timezone
from sb3_contrib import RecurrentPPO
from procesar_datos import procesar_datos_smc
import threading
from dotenv import load_dotenv

# Importamos nuestro inyector de MetaTrader 5
import puente_mt5

# ==========================================
# ⚙️ CONFIGURACIÓN Y VARIABLES DE CONTROL
# ==========================================

load_dotenv()

TOKEN_TELEGRAM = os.getenv("TOKEN_TELEGRAM")
CHAT_ID = os.getenv("CHAT_ID")
MT5_LOGIN = os.getenv("MT5_LOGIN")
MT5_PASSWORD = os.getenv("MT5_PASSWORD")
MT5_SERVER = os.getenv("MT5_SERVER")

SIMBOLO_BINANCE = "BTC/USDT"  # Para descargar datos
SIMBOLO_MT5 = "BTCUSD"  # Para enviar órdenes al broker
VOLUMEN_LOTES = 0.01  # Lotes para la prueba Demo

ARCHIVO_HISTORIAL = "historial_trades.csv"
ARCHIVO_ESTADO = "estado_posicion.json"

posicion_abierta = 0
precio_entrada = 0.0
take_profit = 0.0
stop_loss = 0.0
offset_telegram = None

# Memoria LSTM
estado_lstm = None
inicio_episodio = np.ones((1,), dtype=bool)


# ==========================================
# 💾 SISTEMA DE PERSISTENCIA DE ESTADO
# ==========================================
def cargar_estado_seguro():
    """Recupera el estado del trade si el script o el PC se reinician"""
    global posicion_abierta, precio_entrada, take_profit, stop_loss
    if os.path.exists(ARCHIVO_ESTADO):
        try:
            with open(ARCHIVO_ESTADO, "r", encoding="utf-8") as f:
                estado = json.load(f)
                posicion_abierta = estado.get("posicion_abierta", 0)
                precio_entrada = estado.get("precio_entrada", 0.0)
                take_profit = estado.get("take_profit", 0.0)
                stop_loss = estado.get("stop_loss", 0.0)
            if posicion_abierta != 0:
                print(
                    f"💾 [Persistencia] Detectada posición activa previa en reinicio. Recuperando SL/TP..."
                )
        except Exception as e:
            print(f"⚠️ Error al cargar el archivo de estado persistente: {e}")


def guardar_estado_seguro():
    """Registra en disco de forma atómica el estado actual del mercado"""
    try:
        estado = {
            "posicion_abierta": posicion_abierta,
            "precio_entrada": precio_entrada,
            "take_profit": take_profit,
            "stop_loss": stop_loss,
        }
        with open(ARCHIVO_ESTADO, "w", encoding="utf-8") as f:
            json.dump(estado, f, indent=4)
    except Exception as e:
        print(f"⚠️ Error crítico al escribir el archivo de estado: {e}")


# ==========================================
# 📡 COMUNICACIONES Y ESTADÍSTICAS
# ==========================================
def enviar_mensaje_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TOKEN_TELEGRAM}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": mensaje})
    except Exception as e:
        print(f"Error en Telegram: {e}")


def guardar_trade_en_csv(tipo, entrada, salida, porcentaje):
    nuevo_trade = pd.DataFrame(
        [
            {
                "Fecha": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                "Tipo": tipo,
                "Precio_Entrada": entrada,
                "Precio_Salida": salida,
                "Porcentaje_Neto": porcentaje,
            }
        ]
    )
    header_exist = not os.path.exists(ARCHIVO_HISTORIAL)
    nuevo_trade.to_csv(ARCHIVO_HISTORIAL, mode="a", header=header_exist, index=False)


def enviar_estadisticas():
    try:
        if not os.path.exists(ARCHIVO_HISTORIAL):
            enviar_mensaje_telegram(
                "📊 Historial vacío. Todavía no se ha cerrado ninguna operación."
            )
            return
        df = pd.read_csv(ARCHIVO_HISTORIAL)
        total_trades = len(df)
        if total_trades == 0:
            enviar_mensaje_telegram(
                "📊 Historial vacío. Todavía no se ha cerrado ninguna operación."
            )
            return

        ganados = len(df[df["Porcentaje_Neto"] > 0])
        perdidos = len(df[df["Porcentaje_Neto"] < 0])
        win_rate = (ganados / total_trades) * 100
        rendimiento_total = df["Porcentaje_Neto"].sum()

        reporte = (
            f"📈 --- REPORTE DE RENDIMIENTO V8 (LSTM + MT5) --- 📈\n\n"
            f"🔄 Operaciones Totales: {total_trades}\n"
            f"✅ Operaciones Ganadas: {ganados}\n"
            f"❌ Operaciones Perdidas: {perdidos}\n"
            f"🎯 Win Rate Actual: {win_rate:.1f}%\n"
            f"💰 Rendimiento Acumulado: {rendimiento_total:+.2f}%"
        )
        enviar_mensaje_telegram(reporte)
    except Exception as e:
        print(f"Error al calcular estadísticas: {e}")


def analizar_order_book(exchange, simbolo):
    try:
        order_book = exchange.fetch_order_book(simbolo, limit=50)
        volumen_bids = sum(
            [precio * cantidad for precio, cantidad in order_book["bids"]]
        )
        volumen_asks = sum(
            [precio * cantidad for precio, cantidad in order_book["asks"]]
        )
        volumen_total = volumen_bids + volumen_asks
        if volumen_total == 0:
            return 0.0
        return (volumen_bids - volumen_asks) / volumen_total
    except Exception as e:
        print(f"Error escaneando el Order Book: {e}")
        return 0.0


def revisar_comandos_telegram():
    global offset_telegram
    url = f"https://api.telegram.org/bot{TOKEN_TELEGRAM}/getUpdates"
    params = {"timeout": 1}
    if offset_telegram:
        params["offset"] = offset_telegram
    try:
        respuesta = requests.get(url, params=params).json()
        if respuesta.get("ok") and respuesta.get("result"):
            for update in respuesta["result"]:
                offset_telegram = update["update_id"] + 1
                if "message" in update and "text" in update["message"]:
                    texto = update["message"]["text"].lower().strip()
                    user_chat_id = str(update["message"]["chat"]["id"])
                    if user_chat_id == CHAT_ID:
                        if texto in ["/stats", "/datos", "stats"]:
                            enviar_estadisticas()
                        elif texto in ["/estado", "estado"]:
                            if posicion_abierta == 0:
                                enviar_mensaje_telegram(
                                    "💤 Estado: Evaluando Memoria LSTM y Escudos..."
                                )
                            else:
                                tipo_txt = (
                                    "COMPRA (Long)"
                                    if posicion_abierta == 1
                                    else "VENTA (Short)"
                                )
                                enviar_mensaje_telegram(
                                    f"📊 POSICIÓN ACTIVA:\n• Tipo: {tipo_txt}\n• Entrada: ${precio_entrada:.2f}\n• TP: ${take_profit:.2f}\n• SL: ${stop_loss:.2f}"
                                )
    except Exception:
        pass


def bucle_escucha_telegram():
    while True:
        revisar_comandos_telegram()
        time.sleep(2)


def es_horario_institucional():
    ahora = datetime.now(timezone.utc)
    if ahora.weekday() >= 5:
        return False
    if 7 <= ahora.hour < 17:
        return True  # Sesión híbrida Londres/NY
    return False


# ==========================================
# 🚀 NÚCLEO DEL BOT QUANT DE PRODUCCIÓN
# ==========================================
def ejecutar_bot_en_vivo():
    global posicion_abierta, precio_entrada, take_profit, stop_loss
    global estado_lstm, inicio_episodio

    print(f"--- BOT QUANT V8.2 (Puro LSTM Direccional + MT5) ---")
    cargar_estado_seguro()

    # CONEXIÓN A METATRADER 5
    if not MT5_LOGIN or not MT5_PASSWORD or not MT5_SERVER:
        print("❌ CRÍTICO: Faltan credenciales de MT5 en el archivo .env")
        return

    if not puente_mt5.conectar_mt5(int(MT5_LOGIN), MT5_PASSWORD, MT5_SERVER):
        enviar_mensaje_telegram("❌ CRÍTICO: El bot no pudo conectar con MetaTrader 5.")
        return

    enviar_mensaje_telegram(
        "🛡️ Sistema V8.2 Operativo (Sin filtro Macro). Conectado a MT5 ✅"
    )

    try:
        modelo = RecurrentPPO.load("modelo_smc_v8_lstm_agresivo")
        print("Cerebro Recurrente LSTM cargado con éxito.")
    except:
        print("Error: No se encontró 'modelo_smc_v8_lstm_agresivo.zip'.")
        return

    exchange = ccxt.binance()
    ultima_vela_procesada_id = None

    while True:
        try:
            velas_15m = exchange.fetch_ohlcv(SIMBOLO_BINANCE, "15m", limit=100)
            velas_1h = exchange.fetch_ohlcv(SIMBOLO_BINANCE, "1h", limit=250)

            df_15m = pd.DataFrame(
                velas_15m,
                columns=["timestamp", "open", "high", "low", "close", "volume"],
            )
            df_1h = pd.DataFrame(
                velas_1h,
                columns=["timestamp", "open", "high", "low", "close", "volume"],
            )

            vela_actual_id = df_15m.iloc[-1]["timestamp"]
            precio_actual = float(df_15m.iloc[-1]["close"])

            # ---- GESTIÓN OPERATIVA EN MEMORIA RAM ----
            if posicion_abierta != 0:
                if posicion_abierta == 1:  # LONG
                    if precio_actual >= take_profit:
                        enviar_mensaje_telegram(
                            f"💰 ¡TAKE PROFIT! (COMPRA)\nSalida: ${precio_actual}\nResultado: +2.0% ✅"
                        )
                        guardar_trade_en_csv(
                            "COMPRA", precio_entrada, precio_actual, 2.0
                        )
                        posicion_abierta = 0
                        guardar_estado_seguro()
                    elif precio_actual <= stop_loss:
                        enviar_mensaje_telegram(
                            f"❌ ¡STOP LOSS! (COMPRA)\nSalida: ${precio_actual}\nResultado: -1.0% 🩸"
                        )
                        guardar_trade_en_csv(
                            "COMPRA", precio_entrada, precio_actual, -1.0
                        )
                        posicion_abierta = 0
                        guardar_estado_seguro()

                elif posicion_abierta == 2:  # SHORT
                    if precio_actual <= take_profit:
                        enviar_mensaje_telegram(
                            f"💰 ¡TAKE PROFIT! (VENTA)\nSalida: ${precio_actual}\nResultado: +2.0% ✅"
                        )
                        guardar_trade_en_csv(
                            "VENTA", precio_entrada, precio_actual, 2.0
                        )
                        posicion_abierta = 0
                        guardar_estado_seguro()
                    elif precio_actual >= stop_loss:
                        enviar_mensaje_telegram(
                            f"❌ ¡STOP LOSS! (VENTA)\nSalida: ${precio_actual}\nResultado: -1.0% 🩸"
                        )
                        guardar_trade_en_csv(
                            "VENTA", precio_entrada, precio_actual, -1.0
                        )
                        posicion_abierta = 0
                        guardar_estado_seguro()
            else:
                if (
                    vela_actual_id != ultima_vela_procesada_id
                    and es_horario_institucional()
                ):
                    df_15m.to_csv("datos_vivo_15m.csv", index=False)
                    procesar_datos_smc("datos_vivo_15m.csv")
                    df_15m_smc = pd.read_csv("datos_vivo_15m_smc.csv").fillna(0)
                    ultima_vela_15m = df_15m_smc.iloc[-1]

                    df_1h.to_csv("datos_vivo_1h.csv", index=False)
                    procesar_datos_smc("datos_vivo_1h.csv")
                    df_1h_smc = pd.read_csv("datos_vivo_1h_smc.csv").fillna(0)
                    ultima_vela_1h = df_1h_smc.iloc[-1]

                    atr_actual = float(ultima_vela_15m["ATR"])
                    atr_normalizado = (
                        (atr_actual / precio_actual) * 100 if precio_actual > 0 else 0.0
                    )

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
                            float(posicion_abierta),
                        ],
                        dtype=np.float32,
                    )

                    accion, estado_lstm = modelo.predict(
                        observacion,
                        state=estado_lstm,
                        episode_start=inicio_episodio,
                        deterministic=False,
                    )
                    inicio_episodio = np.zeros((1,), dtype=bool)

                    if accion in [1, 2]:
                        imbalance = analizar_order_book(exchange, SIMBOLO_BINANCE)

                        if accion == 1:
                            if imbalance < -0.25:
                                print(
                                    f"⚠️ [Hard Gate] Muro de ventas detectado ({imbalance:.2f}). Compra Abortada."
                                )
                                enviar_mensaje_telegram(
                                    f"⚠️ [Hard Gate] Nivel 2 detectó ballenas vendiendo (OBI: {imbalance:.2f}). Operación cancelada."
                                )
                                accion = 0
                            else:
                                posicion_abierta = 1
                                precio_entrada = precio_actual

                                # CALIBRACIÓN V9.2: RR estricto 1:2 sin Filtro Macro (Puro LSTM)
                                take_profit = precio_entrada + (3.0 * atr_actual)
                                stop_loss = precio_entrada - (1.5 * atr_actual)

                                # INYECCIÓN A METATRADER 5
                                ticket = puente_mt5.abrir_orden(
                                    SIMBOLO_MT5,
                                    "COMPRA",
                                    VOLUMEN_LOTES,
                                    stop_loss,
                                    take_profit,
                                )

                                guardar_estado_seguro()
                                enviar_mensaje_telegram(
                                    f"🟢 [COMPRA MT5]\nTicket: {ticket}\nEntrada: ${precio_entrada}\n🎯 TP: ${take_profit:.2f}\n🛡️ SL: ${stop_loss:.2f}"
                                )

                        elif accion == 2:
                            if imbalance > 0.25:
                                print(
                                    f"⚠️ [Hard Gate] Muro de compras detectado ({imbalance:.2f}). Venta Abortada."
                                )
                                enviar_mensaje_telegram(
                                    f"⚠️ [Hard Gate] Nivel 2 detectó acumulación de compras (OBI: {imbalance:.2f}). Operación cancelada."
                                )
                                accion = 0
                            else:
                                posicion_abierta = 2
                                precio_entrada = precio_actual

                                # CALIBRACIÓN V9.2: RR estricto 1:2 sin Filtro Macro (Puro LSTM)
                                take_profit = precio_entrada - (3.0 * atr_actual)
                                stop_loss = precio_entrada + (1.5 * atr_actual)

                                # INYECCIÓN A METATRADER 5
                                ticket = puente_mt5.abrir_orden(
                                    SIMBOLO_MT5,
                                    "VENTA",
                                    VOLUMEN_LOTES,
                                    stop_loss,
                                    take_profit,
                                )

                                guardar_estado_seguro()
                                enviar_mensaje_telegram(
                                    f"🔴 [VENTA MT5]\nTicket: {ticket}\nEntrada: ${precio_entrada}\n🎯 TP: ${take_profit:.2f}\n🛡️ SL: ${stop_loss:.2f}"
                                )

                    if accion == 0:
                        hora_actual = datetime.now().strftime("%H:%M:%S")
                        print(
                            f"[{hora_actual}] 👁️ Capas analizadas. Volatilidad (ATR): ${atr_actual:.2f} | IA: FUERA (0)"
                        )

                    ultima_vela_procesada_id = vela_actual_id

            time.sleep(15)

        except Exception as e:
            print(f"Error crítico: {e}")
            time.sleep(10)


if __name__ == "__main__":
    hilo_telegram = threading.Thread(target=bucle_escucha_telegram)
    hilo_telegram.daemon = True
    hilo_telegram.start()
    ejecutar_bot_en_vivo()
