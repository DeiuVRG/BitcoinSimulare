import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import mplcursors  # Importăm mplcursors pentru interacțiune
from statsmodels.tsa.statespace.sarimax import SARIMAX
from arch import arch_model
import warnings

# Dezactivăm avertismentele pentru a preveni interferențele
warnings.filterwarnings("ignore")

# Citire date din fișierul Excel
file_path = r"C:\Users\uig21225\OneDrive - Continental AG\AUTOMATIZARE\bitcoin_daily_price_history.xlsx"
data = pd.read_excel(file_path)
data['Date'] = pd.to_datetime(data['Date'])
data.set_index('Date', inplace=True)
data = data.sort_index()

# Folosim coloana 'Close' pentru analiză
price_data = data['Close'] / 1e6  # Scalează datele pentru stabilitate

# Definim perioada de forecast
forecast_days = 30

# Modelul SARIMA cu parametri ajustați
sarima_model = SARIMAX(price_data, order=(1, 1, 1), seasonal_order=(1, 0, 1, 7))
sarima_fit = sarima_model.fit(disp=False)

# Extragem reziduurile și aplicăm modelul GARCH pentru volatilitate
sarima_residuals = sarima_fit.resid
garch_model = arch_model(sarima_residuals, vol='Garch', p=1, q=1, rescale=False)
garch_fit = garch_model.fit(disp='off')

# Ultima valoare reală din datele istorice
last_historical_value = price_data.iloc[-1] * 1e6

# Funcția de simulare Monte Carlo pentru predicție
def monte_carlo_simulation(base_forecast, garch_fit, num_simulations=1000, forecast_days=30, variance=0.005):
    simulations = []
    garch_volatility = garch_fit.forecast(horizon=forecast_days).variance.values[-1, :]
    
    # Trend aleatoriu redus pentru a diminua zgomotul
    random_trend = np.linspace(-0.05, 0.05, forecast_days) + np.random.normal(0, 0.01, forecast_days)
    
    for _ in range(num_simulations):
        shocks = np.random.normal(0, np.sqrt(garch_volatility) * variance, forecast_days)
        simulated_forecast = base_forecast * (1 + random_trend + shocks)
        simulations.append(simulated_forecast)
    return simulations

# Predicțiile pentru următoarele 30 de zile și ajustare
sarima_forecast = sarima_fit.get_forecast(steps=forecast_days).predicted_mean
sarima_forecast_adjusted = sarima_forecast * (last_historical_value / sarima_forecast.iloc[0])  # Ajustăm să pornească exact de la ultima valoare

# Simulările Monte Carlo bazate pe predicția ajustată
sarima_simulations = monte_carlo_simulation(sarima_forecast_adjusted.values, garch_fit, forecast_days=forecast_days)

# Calculăm mediana și intervalele de confidență (2.5% și 97.5%) pentru simulările ajustate
forecast_median = np.median(sarima_simulations, axis=0)
forecast_lower = np.percentile(sarima_simulations, 2.5, axis=0)
forecast_upper = np.percentile(sarima_simulations, 97.5, axis=0)

# Aplicăm un factor de lărgire pentru a mări vizibilitatea intervalului de confidență
widening_factor = 1.02  # 2% lărgire
forecast_lower *= widening_factor
forecast_upper /= widening_factor

# Adăugăm ultima valoare din datele istorice la forecast pentru continuitate
forecast_median = np.insert(forecast_median, 0, last_historical_value)
forecast_lower = np.insert(forecast_lower, 0, last_historical_value)
forecast_upper = np.insert(forecast_upper, 0, last_historical_value)

# Creăm indexul de date pentru forecast, astfel încât să includă ultima dată din datele istorice
forecast_index = pd.date_range(price_data.index[-1], periods=forecast_days + 1)

# Grafic al datelor istorice și al predicțiilor cu interval de confidență
plt.figure(figsize=(12, 6))
line_actual, = plt.plot(price_data * 1e6, label='Istoric Preț', color='blue')  # Rescalează înapoi pentru afișare
line_forecast, = plt.plot(forecast_index, forecast_median, label='Predicție Mediană', color='orange')
plt.fill_between(forecast_index, forecast_lower, forecast_upper, color='gray', alpha=0.5, label='Interval de Confidență 95%')

plt.xlabel('Date')
plt.ylabel('Close Price')
plt.legend()
plt.title('Predictie Pret Bitcoin pentru urmatoarele 20 de zile (SARIMA + GARCH + Simulari Monte Carlo)')

# Adăugăm interactivitate pentru a afișa valorile la cursor
mplcursors.cursor([line_actual, line_forecast], hover=True).connect(
    "add", lambda sel: sel.annotation.set_text(f"{sel.target[1]:,.2f}"))

plt.show()
