import requests
import pandas as pd
from datetime import datetime, timedelta
import os
import urllib3

# Dezactivăm avertismentele legate de conexiunile SSL nesigure
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Cheia API de la Alpha Vantage
API_KEY = '8LSORZ4HV7UO8NJ1'

# Generăm un DataFrame pentru datele noastre
data = {
    "Date": [],
    "Open": [],
    "High": [],
    "Low": [],
    "Close": [],
    "Volume": []
}

# Endpoint-ul Alpha Vantage pentru datele zilnice
url = f'https://www.alphavantage.co/query?function=DIGITAL_CURRENCY_DAILY&symbol=BTC&market=USD&apikey={API_KEY}'

# Facem cererea la API, dezactivând verificarea SSL
response = requests.get(url, verify=False)
response_json = response.json()

# Obținem data curentă și data de start (cu 3 ani în urmă)
today = datetime.now().date()
start_date = today - timedelta(days=3*365)  # Aproximativ 3 ani în urmă

# Verificăm dacă există o eroare în răspuns
if "Error Message" in response_json:
    print("Eroare în răspunsul de la API:", response_json["Error Message"])
elif "Time Series (Digital Currency Daily)" in response_json:
    # Parcurgem fiecare zi din datele primite
    for date_str, daily_data in response_json['Time Series (Digital Currency Daily)'].items():
        # Convertim data din string în obiect date
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        # Filtrăm datele care sunt în intervalul dorit
        if start_date <= date <= today:
            # Adăugăm valorile în structura de date, dacă există
            open_value = daily_data.get('1. open', None)
            high_value = daily_data.get('2. high', None)
            low_value = daily_data.get('3. low', None)
            close_value = daily_data.get('4. close', None)
            volume_value = daily_data.get('5. volume', None)
            
            # Verificăm dacă toate valorile necesare sunt disponibile
            if open_value and high_value and low_value and close_value and volume_value:
                data["Date"].append(date)
                data["Open"].append(float(open_value))
                data["High"].append(float(high_value))
                data["Low"].append(float(low_value))
                data["Close"].append(float(close_value))
                data["Volume"].append(float(volume_value))
            else:
                print(f"Date incomplete pentru {date_str}. Available keys: {list(daily_data.keys())}")
else:
    print("Nu s-au găsit date pentru simbolul specificat. Structura răspunsului:", response_json)

# Numele fișierului de export în locația scriptului
script_dir = os.path.dirname(os.path.abspath(__file__))  # Obținem locația scriptului
file_name = os.path.join(script_dir, "bitcoin_daily_price_history.xlsx")

# Ștergem fișierul existent, dacă există
if os.path.exists(file_name):
    os.remove(file_name)
    print(f"Fișierul existent '{file_name}' a fost șters.")

# Creăm un DataFrame și exportăm în Excel dacă avem date
if data["Date"]:
    df = pd.DataFrame(data)
    df = df.sort_values(by='Date')  # Sortăm datele cronologic
    with pd.ExcelWriter(file_name, engine="xlsxwriter", datetime_format='yyyy-mm-dd') as writer:
        df.to_excel(writer, index=False, sheet_name="Bitcoin Price History")
        # Setăm formatul pentru coloana de dată în Excel
        workbook  = writer.book
        worksheet = writer.sheets["Bitcoin Price History"]
        date_format = workbook.add_format({'num_format': 'yyyy-mm-dd'})
        worksheet.set_column("A:A", 15, date_format)  # Setăm lățimea și formatul pentru coloana Date
        worksheet.set_column("B:F", 12)  # Setăm lățimea pentru celelalte coloane
    print(f"Fișierul Excel a fost creat: {file_name}")
else:
    print("Nu există date disponibile pentru export.")
