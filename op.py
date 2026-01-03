import streamlit as st
import openmeteo_requests
import requests_cache
import pandas as pd
from retry_requests import retry
from datetime import datetime, timedelta

# --- CONFIGURATIE ---
st.set_page_config(page_title="Race Control Weather", page_icon="🏎️", layout="wide")

# --- DATA LOGICA (Hetzelfde als voorheen) ---
@st.cache_data(ttl=120) # Cache data voor 2 minuten
def get_weather_data(lat, lon):
    cache_session = requests_cache.CachedSession('.cache', expire_after=120)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)
    
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "minutely_15": ["temperature_2m", "apparent_temperature", "precipitation", 
                        "wind_speed_10m", "wind_direction_10m", 
                        "cloud_cover_low", "cloud_cover_mid", "cloud_cover_high"],
        "forecast_days": 1,
        "models": "best_match"
    }
    
    responses = openmeteo.weather_api(url, params=params)
    response = responses[0]
    minutely = response.Minutely15()
    
    times = pd.date_range(
        start=pd.to_datetime(minutely.Time(), unit="s", utc=True),
        freq=pd.Timedelta(seconds=minutely.Interval()),
        periods=len(minutely.Variables(0).ValuesAsNumpy())
    )
    
    data = {
        "time": times,
        "temp": minutely.Variables(0).ValuesAsNumpy(),
        "apparent_temp": minutely.Variables(1).ValuesAsNumpy(),
        "precip": minutely.Variables(2).ValuesAsNumpy(),
        "wind_spd": minutely.Variables(3).ValuesAsNumpy(),
        "wind_dir": minutely.Variables(4).ValuesAsNumpy(),
        "low": minutely.Variables(5).ValuesAsNumpy(),
        "mid": minutely.Variables(6).ValuesAsNumpy(),
        "high": minutely.Variables(7).ValuesAsNumpy(),
    }
    
    df = pd.DataFrame(data)
    now = pd.Timestamp.now(tz='UTC')
    # Filter: Nu tot +3 uur
    df = df[(df['time'] >= now - timedelta(minutes=15)) & (df['time'] <= now + timedelta(hours=3))]
    return df

def get_strategy(row):
    # Track Temp Estimator
    wind_cooling = row['wind_spd'] * 0.1
    sun_heating = ((100 - (row['low'] + row['mid'])/2) / 10) if row['precip'] == 0 else -2
    track_temp = row['temp'] + max(0, sun_heating) - wind_cooling
    
    # Strategy Logic
    if row['precip'] == 0:
        cond = "DRY"
        tire = "SOFT" if track_temp < 15 else "MED/HARD"
        color = "green"
    elif row['precip'] < 0.2:
        cond = "DAMP"
        tire = "SLICKS/INTER"
        color = "orange"
    else:
        cond = "WET"
        tire = "INTER/WET"
        color = "red"
        
    return pd.Series([row['time'].strftime("%H:%M"), cond, row['precip'], 
                      f"{round(row['temp'],1)} / {round(row['apparent_temp'],1)}", 
                      f"{round(track_temp,1)}", 
                      f"{round(row['wind_spd'],0)} km/h", tire], 
                     index=["Time", "Cond", "Rain (mm)", "Air/Feel", "Track Est.", "Wind", "STRATEGY"])

# --- DE IPHONE INTERFACE ---
st.title("🏎️ Race Control HQ")

# Sidebar voor instellingen (makkelijk aanpassen op mobiel)
with st.sidebar:
    st.header("Location Setup")
    # Default: Zandvoort
    lat = st.number_input("Latitude", value=52.387, format="%.4f")
    lon = st.number_input("Longitude", value=4.540, format="%.4f")
    st.caption("Tip: Gebruik Google Maps om Lat/Lon van je rally stage te vinden.")
    
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()

# Data ophalen
try:
    raw_df = get_weather_data(lat, lon)
    
    # Huidige status kaartjes (KPI's)
    current = raw_df.iloc[0]
    col1, col2, col3 = st.columns(3)
    col1.metric("Rain (Now)", f"{current['precip']} mm", delta_color="inverse")
    col2.metric("Wind", f"{round(current['wind_spd'])} km/h")
    col3.metric("Temp", f"{round(current['temp'], 1)} °C")

    # Tabel bouwen
    st.subheader("Tactical Forecast (Next 3 Hours)")
    
    # Pas de dataframe aan voor weergave
    display_df = raw_df.apply(get_strategy, axis=1)
    
    # Styling van de tabel (Highlight Strategy)
    def highlight_strategy(s):
        is_wet = "WET" in s['STRATEGY'] or "INTER" in s['STRATEGY']
        return ['background-color: #550000' if is_wet else '' for _ in s]

    st.dataframe(display_df.style.apply(highlight_strategy, axis=1), use_container_width=True)
    
    # Grafiekje voor regen (Visueel sneller dan cijfers)
    st.subheader("Rain Intensity Trend")
    st.line_chart(raw_df.set_index("time")["precip"])

except Exception as e:
    st.error(f"Error connecting to satellite: {e}")