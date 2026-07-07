import MetaTrader5 as mt5


def conectar_mt5(login, password, server):
    """Inicializa la conexión con la terminal de MetaTrader 5"""
    if not mt5.initialize():
        print("❌ Fallo al inicializar MetaTrader 5.")
        return False

    autorizado = mt5.login(login, password=password, server=server)
    if autorizado:
        print(f"✅ Conectado a MT5 con éxito. Cuenta: {login}")
        return True
    else:
        print(f"❌ Fallo al conectar a MT5: {mt5.last_error()}")
        return False


def abrir_orden(simbolo, tipo, volumen, sl, tp):
    """Envía la orden de compra/venta con SL y TP al broker"""

    # --- TRADUCTOR AUTOMÁTICO DE SÍMBOLO ---
    # Ignoramos el nombre de Binance y forzamos el nombre exacto de este broker
    simbolo_broker = "BTC"

    # 1. Preparamos el símbolo en MT5
    symbol_info = mt5.symbol_info(simbolo_broker)
    if symbol_info is None:
        print(f"❌ Símbolo '{simbolo_broker}' no encontrado en MT5.")
        return None

    if not symbol_info.visible:
        if not mt5.symbol_select(simbolo_broker, True):
            print(f"❌ No se pudo hacer visible el símbolo {simbolo_broker}.")
            return None

    # 2. Definimos si es Compra o Venta
    if tipo == "COMPRA":
        order_type = mt5.ORDER_TYPE_BUY
        precio_ejecucion = mt5.symbol_info_tick(simbolo_broker).ask
    else:
        order_type = mt5.ORDER_TYPE_SELL
        precio_ejecucion = mt5.symbol_info_tick(simbolo_broker).bid

    # 3. Empaquetamos la orden
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": simbolo_broker,
        "volume": float(volumen),
        "type": order_type,
        "price": precio_ejecucion,
        "sl": float(sl),
        "tp": float(tp),
        "deviation": 20,  # Tolerancia de slippage
        "magic": 101010,  # Firma digital del bot V8
        "comment": "Bot Quant V8",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,  # Modo institucional
    }

    # 4. Inyectamos la orden en el mercado
    resultado = mt5.order_send(request)

    if resultado.retcode != mt5.TRADE_RETCODE_DONE:
        print(
            f"❌ Error al abrir orden en MT5: {resultado.retcode} - {resultado.comment}"
        )
        return None

    print(f"✅ Orden {tipo} ejecutada en MT5. Ticket: {resultado.order}")
    return resultado.order
