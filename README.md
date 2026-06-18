# Quantum AI Trading Bot (SMC + LSTM) 🤖📈

Bot de trading cuantitativo automatizado desarrollado en Python, que fusiona los conceptos de liquidez institucional (Smart Money Concepts) con Inteligencia Artificial (Redes Neuronales Recurrentes LSTM) para la toma de decisiones en el mercado de criptomonedas y TradFi.

## 🚀 Características Principales (Arquitectura V7)
* **Visión Fractal:** Análisis simultáneo de temporalidades (15m y 1h) para confirmación de tendencia.
* **Algoritmo SMC:** Detección matemática de Roturas de Estructura (BOS) y Vacíos de Liquidez (FVG).
* **Gestión de Riesgo Cuantitativa:** Cálculo dinámico de Stop Loss y Take Profit basado en volatilidad en tiempo real (ATR).
* **Filtro Hard Gate (Nivel 2):** Escáner del Libro de Órdenes (Order Book) vía API para abortar operaciones si se detectan muros de liquidez institucionales en contra.
* **Memoria Persistente Anti-Fallos:** Sistema de guardado de estado en disco (`.json`) para recuperación de operaciones activas tras microcortes de conexión o reinicios.
* **Integración Asíncrona:** Hilos dedicados (`threading`) para control e informes de rendimiento vía Telegram sin bloquear el motor de trading.

## 🛠️ Stack Tecnológico
* **Lenguaje:** Python 3
* **Machine Learning:** Stable-Baselines3 (RecurrentPPO / LSTM)
* **Data Science:** Pandas, NumPy
* **Conectividad Financiera:** CCXT (Binance API), MetaTrader 5 API
* **Despliegue:** Dotenv para gestión segura de credenciales.

> **Nota para Reclutadores:** Por motivos de seguridad y Propiedad Intelectual, los datasets de entrenamiento, el modelo en formato `.zip`, el historial de transacciones y los archivos de entorno (`.env`) han sido excluidos de este repositorio público.