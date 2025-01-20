import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from statsmodels.tsa.arima.model import ARIMA
import mplcursors
from matplotlib.dates import num2date  # <--- pentru conversie x_val -> datetime

# ----------------------------------------------------------------------------
# 1) Citește fișierul Excel cu date istorice BTC
# ----------------------------------------------------------------------------
script_dir = os.path.dirname(os.path.abspath(__file__))
file_name = os.path.join(script_dir, "bitcoin_daily_price_history.xlsx")

if not os.path.exists(file_name):
    print(f"Fișierul {file_name} nu există. Rulează mai întâi scriptul de extragere a datelor.")
    exit()

df = pd.read_excel(file_name)

# Convertim coloana Date în datetime și o setăm ca index
df['Date'] = pd.to_datetime(df['Date'])
df.set_index('Date', inplace=True)
df.sort_index(inplace=True)

# ----------------------------------------------------------------------------
# 2) Calculăm log-return 
# ----------------------------------------------------------------------------
df['log_price'] = np.log(df['Close'])
df['log_return'] = df['log_price'].diff()
df.dropna(subset=['log_return'], inplace=True)  # eliminăm primul NaN

# ----------------------------------------------------------------------------
# 3) Antrenăm un model ARIMA pe log_return
# ----------------------------------------------------------------------------
p, d, q = 1, 0, 1
model = ARIMA(df['log_return'], order=(p, d, q))
fit = model.fit()

print(f"Rezumat ARIMA({p},{d},{q}):")
print(fit.summary())

# ----------------------------------------------------------------------------
# 4) Forecast randamente + simulare Monte Carlo
# ----------------------------------------------------------------------------
forecast_days = 20            # zile forecast
num_simulations = 150     # !!! foarte mare => atenție la timpul de rulare
volatility_factor = 3.0       # crește factorul de volatilitate (ex. 2.0)

# Forecastul ARIMA (randamente medii prezise)
forecast_obj = fit.get_forecast(steps=forecast_days)
mean_returns_forecast = forecast_obj.predicted_mean

# Reziduurile modelului
residuals = fit.resid.dropna()

# Ultimul preț logaritmic din date
last_log_price = df['log_price'].iloc[-1]

# Simulările (log-price)
simulations_log_prices = []

print(f"\n=== Încep simulările Monte Carlo: {num_simulations} simulări, "
      f"volatility_factor={volatility_factor} ===\n"
      "Pot dura câteva minute (sau zeci de minute), te rog așteaptă...")

for _ in range(num_simulations):
    sim_log_path = [last_log_price]
    
    for day in range(forecast_days):
        mu_t = mean_returns_forecast.iloc[day]
        
        # extragem un șoc normal cu sigma = dev std al reziduurilor
        shock_raw = np.random.normal(0, np.std(residuals))
        
        # amplificăm șocul
        shock = shock_raw * volatility_factor
        
        # randament simulat = medie + șoc
        simulated_return = mu_t + shock
        
        new_log_price = sim_log_path[-1] + simulated_return
        sim_log_path.append(new_log_price)
    
    simulations_log_prices.append(sim_log_path)

print("Simulările s-au terminat.\n")

simulations_log_prices = np.array(simulations_log_prices)  # (num_sim, forecast_days+1)
simulations_prices = np.exp(simulations_log_prices)

# ----------------------------------------------------------------------------
# 5) Calculăm mediană și percentila 25-75 
# ----------------------------------------------------------------------------
median_price = np.median(simulations_prices, axis=0)
p25_price = np.percentile(simulations_prices, 25, axis=0)
p75_price = np.percentile(simulations_prices, 75, axis=0)

# ----------------------------------------------------------------------------
# 6) Construim index de timp
# ----------------------------------------------------------------------------
start_forecast_date = df.index[-1]  
forecast_dates = pd.date_range(start=start_forecast_date, periods=forecast_days+1, freq='D')

# ----------------------------------------------------------------------------
# 7) Plot
# ----------------------------------------------------------------------------
plt.figure(figsize=(10, 6))

# Plot prețuri istorice
line_hist, = plt.plot(df.index, df['Close'], label='Preț Istoric (Close)', color='blue')

# Plot mediana
line_median, = plt.plot(forecast_dates, median_price, label='Predicție (Mediană)', color='orange')

# Banda [25%, 75%]
plt.fill_between(
    forecast_dates,
    p25_price,
    p75_price,
    color='gray',
    alpha=0.3,
    label='Interval [25%, 75%]'
)

plt.title(f"Predicție BTC cu ARIMA + Monte Carlo\n"
          f"(Interval 25%-75%, {num_simulations} simulări, factor volatilitate={volatility_factor})")
plt.xlabel("Data")
plt.ylabel("Preț BTC (USD)")
plt.legend()
plt.grid(True)
plt.tight_layout()

# ----------------------------------------------------------------------------
# 8) Interacțiune cu mouse-ul (mplcursors)
# ----------------------------------------------------------------------------
cursor = mplcursors.cursor([line_hist, line_median], hover=True)

@cursor.connect("add")
def on_add(sel):
    x_val, y_val = sel.target
    # Convertim x_val (float) în datetime prin num2date
    date_dt = num2date(x_val)
    date_str = date_dt.strftime('%Y-%m-%d')
    
    sel.annotation.set_text(f"{date_str}\nPreț: {y_val:.2f}")
    sel.annotation.get_bbox_patch().set(fc="white", alpha=0.9)

# ----------------------------------------------------------------------------
# 9) Afișare plot interactiv
# ----------------------------------------------------------------------------
plt.show()
