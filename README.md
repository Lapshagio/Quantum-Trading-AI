# IA Trading Bot — BTCUSD sobre MetaTrader 5

Bot de trading algorítmico para BTCUSD, con ejecución en MetaTrader 5. El motor de decisión es una **regla determinística de confluencia multi-timeframe** basada en Smart Money Concepts (SMC), validada estadísticamente contra tres años de histórico antes de conectarse a una cuenta real.

Este README documenta la arquitectura actual (V10) y, por transparencia técnica, el camino de investigación con Reinforcement Learning que se intentó antes y por qué se abandonó.

## Arquitectura V10

### 1. Ingesta y pipeline de datos

Los datos en vivo se obtienen en dos temporalidades (15 minutos y 1 hora) directamente contra el broker vía MetaTrader 5. Cada ciclo, el pipeline excluye explícitamente la vela en formación antes de calcular cualquier indicador — solo se opera sobre velas ya cerradas, para que el comportamiento en vivo sea consistente con la metodología usada en el backtesting histórico.

### 2. Procesamiento SMC (Smart Money Concepts)

Sobre cada temporalidad se calculan:

- **Fair Value Gaps (FVG):** desequilibrios de precio entre velas no consecutivas, alcistas y bajistas.
- **Estructura de mercado (BOS — Break of Structure):** rotura de swings de precio confirmados, detectando cambios de dirección institucional.
- **ATR (Average True Range):** medición de volatilidad dinámica, usada como base para el dimensionamiento de Stop Loss / Take Profit.
- **Sesión horaria:** filtro de ventana operativa alineado con el período de mayor liquidez institucional.

### 3. Regla de decisión determinística (confluencia multi-timeframe)

A diferencia de un modelo de machine learning que "aprende" una política, la decisión de entrada es una regla fija y auditable: se requiere un FVG en la temporalidad de ejecución **y** una rotura de estructura alineada en la temporalidad superior, dentro de la ventana de sesión activa. Sin esa doble confirmación, no hay operación — no existe ambigüedad ni comportamiento no determinista en la señal.

Esta regla fue validada con un backtest estadístico separado (simulación secuencial de una sola posición a la vez, con position sizing de riesgo fijo) antes de conectarse a la cuenta real. Los resultados exactos de esa validación no se publican en este README — son específicos de la cuenta y del período evaluado, y no deben interpretarse como garantía de rendimiento futuro (ver disclaimer).

### 4. Gestión de riesgo dinámica

El tamaño de posición no se asume ni se fija en lotes constantes: se calcula en cada operación a partir del **valor real por punto** del instrumento, consultado directamente vía `symbol_info` del broker (contract size, tick value, tick size), no con una aproximación genérica. El riesgo por operación es un porcentaje fijo del balance de cuenta actual, con relación riesgo/beneficio fija.

### 5. Motor de ejecución con verificación server-side

Ninguna posición se marca como "abierta" en el estado interno del bot hasta que el broker confirma explícitamente la ejecución de la orden. El cierre de posiciones tampoco se infiere comparando precios locales contra el Take Profit/Stop Loss teóricos: se consulta directamente el estado real de la posición contra el broker, y el resultado (ganancia o pérdida) se reconstruye desde el historial de operaciones del broker, no desde una suposición.

## El camino con Reinforcement Learning (`legacy_rl/`)

Antes de llegar a la regla determinística, este proyecto pasó por varias iteraciones de un enfoque distinto: un modelo de **Reinforcement Learning recurrente (PPO con memoria LSTM)** que aprendería la política de entrada/salida directamente de datos históricos. El código de esa etapa se conserva en `legacy_rl/` como referencia histórica, no como algo en uso.

### Qué se intentó

El modelo se entrenaba sobre el histórico de 3 años procesado con los mismos indicadores SMC, con observaciones normalizadas (estructura, FVG, ATR, spread, sesión) y una función de recompensa basada en el resultado real de cada operación simulada (ratio riesgo/beneficio fijo).

### Por qué se abandonó: colapso de entropía persistente

El problema documentado, de forma consistente en **los cuatro entrenamientos conservados en `legacy_rl/` (v10 a v13)** — hubo al menos una corrida anterior (la que generó `modelo_smc_v9_lstm_mt5`) que no dejó log persistido, por lo que "cuatro documentados" no equivale a "cuatro intentos totales" —, fue un colapso de entropía de la política: la entropía de las acciones del modelo (una medida de cuánto explora vs. cuánto ya "decidió" una respuesta fija) arrancaba en un nivel saludable de exploración en cada corrida y colapsaba progresivamente hacia casi cero — es decir, el modelo dejaba de explorar y convergía a una política casi determinista mucho antes de haber aprendido una señal robusta, quedando efectivamente atascado.

Se probaron intervenciones sucesivas entre una corrida y la siguiente, cada una apuntando a una hipótesis distinta sobre la causa:

1. **Episodios cortos con inicio aleatorio** (en vez de un único episodio de ~100k pasos): la hipótesis era que un horizonte de episodio demasiado largo diluía la señal de recompensa.
2. **Aumento del coeficiente de entropía (`ent_coef`)**: para penalizar directamente la pérdida de exploración.
3. **Reducción de `n_epochs` por lote y adición de `target_kl`**: para evitar que cada actualización de política se sobreajustara de forma agresiva sobre el lote de datos recién visto.

Ninguna de las tres intervenciones, aplicadas de forma acumulativa a lo largo de los cuatro entrenamientos, evitó el colapso — solo cambió la velocidad y severidad con la que ocurría. Ese patrón repetido, entrenamiento tras entrenamiento, fue la evidencia que llevó a abandonar el enfoque de RL en favor de una regla determinística: una señal validada estadísticamente de forma directa, sin depender de que un proceso de optimización estocástico convergiera de forma estable, resultó más confiable para una cuenta con dinero real.

## Ingeniería y prácticas

- **Logging estructurado**: los errores del bot en vivo se registran con traceback completo (no solo el mensaje), a consola y a archivo con rotación, categorizados entre errores de red/API externa y errores de lógica interna — para poder diagnosticar un fallo sin depender de que la ventana de consola siga abierta. Los reintentos usan backoff progresivo en vez de un intervalo fijo, para no agravar un problema de límite de tasa del lado del broker o del proveedor de datos.
- **Verificación de ejecución antes de confirmar estado**: ninguna apertura de posición se da por exitosa sin confirmar explícitamente la respuesta del broker; ningún cierre se infiere por comparación de precio local cuando existe una fuente de verdad consultable directamente en el broker.
- **Protocolo de cambios para archivos que operan la cuenta real**: cualquier modificación a los archivos que ejecutan órdenes reales sigue un protocolo fijo — mostrar el diff completo antes de aplicar, verificar que el código compila (sin tratar eso como validación de la lógica de negocio), y confirmar con una búsqueda directa sobre el archivo en disco qué quedó realmente aplicado, en vez de asumirlo por el resumen del cambio.

## ⚠️ Disclaimer

Este proyecto tiene fines **educativos y de investigación en ingeniería de software y ciencia de datos**. No es asesoría financiera. Operar en mercados financieros (Forex, criptomonedas, futuros, CFDs) conlleva un alto nivel de riesgo, incluida la posibilidad de pérdida total del capital. Los resultados de cualquier backtesting o validación estadística corresponden a datos históricos y **no garantizan rendimiento futuro** — condiciones de mercado, liquidez, spread y ejecución real pueden diferir significativamente de lo simulado. El autor no se hace responsable de pérdidas derivadas del uso de este software. Se recomienda usarlo exclusivamente en cuentas demo o de simulación antes de considerar cualquier otro uso.

## Instalación y uso

1. Clonar el repositorio.

2. Instalar las dependencias del sistema en vivo:

```bash
pip install ccxt pandas numpy MetaTrader5 python-dotenv requests
```

   (Opcional, solo para explorar `legacy_rl/`: `pip install sb3_contrib stable-baselines3 gymnasium`.)

3. Configurar el archivo `.env` en la raíz del proyecto con tus propias credenciales:

```env
TOKEN_TELEGRAM=<tu_token_de_bot_de_telegram>
CHAT_ID=<tu_chat_id_de_telegram>
MT5_LOGIN=<tu_usuario_mt5>
MT5_PASSWORD=<tu_contraseña_mt5>
MT5_SERVER=<nombre_del_servidor_de_tu_broker>
```

   `.env` está en `.gitignore` — nunca subas tus credenciales reales al repositorio.

4. Ejecutar el sistema:

```bash
python bot_en_vivo.py
```

Se recomienda encarecidamente comenzar en una cuenta demo y revisar el protocolo de cambios antes de modificar cualquier archivo que opere la cuenta.
