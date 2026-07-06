🚀 Quantum Trading AI (Cerebro V8)

Un sistema de trading algorítmico de grado institucional que fusiona Smart Money Concepts (SMC) con Deep Reinforcement Learning (LSTM). Diseñado para operar de forma autónoma, el sistema filtra el "ruido" del mercado aplicando confluencias técnicas, análisis de liquidez en Nivel 2 (Order Book) y ejecución automatizada en MetaTrader 5.

🧠 Arquitectura del Sistema

El "Cerebro V8" no es un simple bot basado en indicadores tradicionales; es un ecosistema cuantitativo compuesto por varias capas de análisis y seguridad:

Ingesta de Datos (CCXT): Extracción de datos OHLCV en vivo desde Binance en múltiples temporalidades (15m y 1H).

Procesamiento de Estructura (SMC): Detección matemática de roturas de estructura (BOS/CHOCH), Fair Value Gaps (FVG) y medición de volatilidad dinámica (ATR).

Red Neuronal Recurrente (LSTM): Un modelo de Reinforcement Learning (Proximal Policy Optimization con memoria LSTM) entrenado con miles de velas históricas para predecir la direccionalidad del precio.

Filtros de Ejecución (Hard Gates):

Escudo Macro (EMA 200): Prohíbe operaciones en contra de la tendencia principal de 1 Hora.

Escudo de Liquidez (Order Book Imbalance): Analiza la profundidad del mercado en vivo. Aborta operaciones si detecta "muros" institucionales de órdenes límite en contra (Umbral > 0.25).

Inyector de Órdenes (MT5 Bridge): Comunicación bidireccional con terminales MetaTrader para la ejecución de órdenes en cuentas de fondeo (Prop Firms) con Stop Loss y Take Profit fijos.

⚙️ Tecnologías Utilizadas

Python 3: Lenguaje principal del ecosistema.

Stable Baselines3 (sb3_contrib): Implementación de la red neuronal RecurrentPPO.

MetaTrader 5 API: Para la ejecución de órdenes y gestión de posiciones en vivo.

CCXT: Para el análisis profundo del Order Book en criptomonedas (Binance).

Pandas & NumPy: Manipulación de datos financieros y cálculo vectorial.

HTML/JS (Chart.js & Tailwind): Dashboard analítico local para evaluar la Curva de Equidad (Equity Curve) durante el Forward Testing.

Telegram Bot API: Sistema de alertas y reportes de estado en tiempo real.

📊 Dashboard Cuantitativo Incluido

El proyecto incluye un tracker_smc.html, un panel de control serverless que permite ingestar los archivos .csv generados por el bot para auditar:

Net PNL (Rendimiento Acumulado).

Win Rate.

Maximum Drawdown (Riesgo).

Curva de Equidad gráfica.

🚀 Instalación y Uso (Entorno Demo)

Clonar el repositorio.

Instalar las dependencias necesarias:

pip install ccxt pandas numpy sb3_contrib MetaTrader5 python-dotenv requests


Configurar el archivo .env en la raíz del proyecto:

TOKEN_TELEGRAM=tu_token_telegram
CHAT_ID=tu_chat_id
MT5_LOGIN=tu_usuario_demo
MT5_PASSWORD=tu_contraseña_demo
MT5_SERVER=Nombre-Del-Broker-Demo


Ejecutar el sistema en vivo:

python bot_en_vivo.py


⚠️ Descargo de Responsabilidad (Disclaimer)

Este proyecto tiene fines estrictamente educativos y de investigación en Ingeniería de Software y Data Science. El código proporcionado NO es un consejo financiero. Operar en los mercados financieros (Forex, Criptomonedas, Futuros) conlleva un alto nivel de riesgo. El creador de este repositorio no se hace responsable de las pérdidas financieras que puedan derivarse del uso de este software en cuentas con dinero real. Se recomienda encarecidamente utilizarlo únicamente en entornos de simulación (Demo) o Forward Testing.