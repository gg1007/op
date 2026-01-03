import streamlit as st
import openmeteo_requests
import requests_cache
import pandas as pd
import gpxpy
import gpxpy.gpx
from retry_requests import retry
from datetime import datetime, timedelta
from geopy.distance import geodesic

# --- CONFIGURATIE ---
st.set_page_config(page_title="Race Control HQ", page_icon="🏎️", layout="wide")

# --- DATA FUNCTIES ---
@st.cache_data(ttl=120)
def get_weather_data(lat, lon, mode="circuit"):
    # Setup API
    cache_session = requests_cache.CachedSession('.cache', expire_after=120)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)
    
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "minutely_15": ["temperature_2m", "precipitation", "wind_speed_10m", 
                        "cloud_cover_low", "cloud_cover_mid", "wind_direction_10m"],
        "forecast_days": 1,
        "models": "best_match"
    }
    
    try:
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
            "precip": minutely.Variables(1).ValuesAsNumpy(),
            "wind": minutely.Variables(2).ValuesAsNumpy(),
            "cloud": minutely.Variables(3).ValuesAsNumpy(),
            "dir": minutely.Variables(5).ValuesAsNumpy(),
        }
        
        df = pd.DataFrame(data)
        now = pd.Timestamp.now(tz='UTC')
        
        # Filter: Circuit (3 uur vooruit), Rally (1 uur vooruit per punt)
        hours = 3 if mode == "circuit" else 1
        df = df[(df['time'] >= now) & (df['time'] <= now + timedelta(hours=hours))]
        
        if mode == "rally":
             # Samenvatting voor dit routepunt
             return {
                "precip_max": df['precip'].max(),
                "temp": df['temp'].mean(),
                "wind": df['wind'].mean(),
                "risk": "WET" if df['precip'].max() > 0.2 else "DRY"
            }
        
        return df # Circuit geeft volledige tijdlijn terug
        
    except Exception as e:
        return None

def parse_gpx_route(uploaded_file, step_km=4):
    gpx = gpxpy.parse(uploaded_file)
    points = []
    for track in gpx.tracks:
        for segment in track.segments:
            points.extend(segment.points)
            
    if not points: return []
    
    selected = [{"name": "START", "lat": points[0].latitude, "lon": points[0].longitude}]
    last = points[0]
    total_dist = 0
    
    for p in points:
        dist = geodesic((last.latitude, last.longitude), (p.latitude, p.longitude)).kilometers
        if dist >= step_km:
            total_dist += dist
            selected.append({"name": f"KM {int(total_dist)}", "lat": p.latitude, "lon": p.longitude})
            last = p
            
    end = points[-1]
    selected.append({"name": "FINISH", "lat": end.latitude, "lon": end.longitude})
    return selected

def get_strategy(row):
    # Eenvoudige strategie logica voor circuit tabel
    if row['precip'] == 0:
        tire = "SLICKS"
        color = "green"
    elif row['precip'] < 0.5:
        tire = "INTERS"
        color = "orange"
    else:
        tire = "WETS"
        color = "red"
    
    return pd.Series([
        row['time'].strftime("%H:%M"), 
        f"{row['precip']:.1f} mm", 
        f"{row['temp']:.1f}°C", 
        f"{row['wind']:.0f} km/h",
        tire
    ], index=["Time", "Rain", "Temp", "Wind", "TIRE CALL"])

# --- DE UI ---
st.title("🏎️ Race Control HQ")

# 1. KIES JE MODUS
mode = st.sidebar.radio("Selecteer Modus:", ["📍 Circuit / Vaste Locatie", "🏁 Rally Stage (GPX)"])

# 2. CIRCUIT MODUS
if mode == "📍 Circuit / Vaste Locatie":
    st.sidebar.header("Locatie Setup")
    
    # Presets
    circuits = {
        "Zandvoort 🇳🇱": (52.387, 4.540),
        "Spa-Francorchamps 🇧🇪": (50.437, 5.971),
        "Nürburgring 🇩🇪": (50.335, 6.947),
        "Assen 🇳🇱": (52.958, 6.523),
        "Zolder 🇧🇪": (50.989, 5.260),
        "Monaco 🇲🇨": (43.734, 7.420),
        "Custom (Vul zelf in)": (0,0)
    }
    
    choice = st.sidebar.selectbox("Kies Circuit:", list(circuits.keys()))
    
    if choice == "Custom (Vul zelf in)":
        lat = st.sidebar.number_input("Latitude", value=52.0)
        lon = st.sidebar.number_input("Longitude", value=5.0)
    else:
        lat, lon = circuits[choice]
        st.sidebar.caption(f"GPS: {lat}, {lon}")

    if st.button("📡 Scan Atmosfeer"):
        data = get_weather_data(lat, lon, mode="circuit")
        
        if data is not None:
            # Huidige status
            curr = data.iloc[0]
            c1, c2, c3 = st.columns(3)
            c1.metric("Regen Nu", f"{curr['precip']} mm", delta_color="inverse")
            c2.metric("Wind", f"{int(curr['wind'])} km/h")
            c3.metric("Temp", f"{curr['temp']:.1f} °C")
            
            # Strategie Tabel
            st.subheader(f"Forecast: {choice}")
            strategy_df = data.apply(get_strategy, axis=1)
            
            def style_wet(s):
                return ['background-color: #550000' if 'WETS' in s['TIRE CALL'] or 'INTERS' in s['TIRE CALL'] else '' for _ in s]

            st.dataframe(strategy_df.style.apply(style_wet, axis=1), use_container_width=True)
            
            # Grafiek
            st.line_chart(data.set_index("time")["precip"])

# 3. RALLY MODUS
else:
    st.sidebar.header("Route Upload")
    uploaded_file = st.sidebar.file_uploader("Upload GPX Bestand", type=['gpx'])
    
    st.markdown("### 🏁 Rally Stage Profiler")
    
    if uploaded_file:
        st.info(f"Route '{uploaded_file.name}' analyseren...")
        waypoints = parse_gpx_route(uploaded_file)
        
        results = []
        bar = st.progress(0)
        
        for i, wp in enumerate(waypoints):
            w = get_weather_data(wp['lat'], wp['lon'], mode="rally")
            if w:
                results.append({
                    "Punt": wp['name'],
                    "Status": w['risk'],
                    "Regen": f"{w['precip_max']:.1f} mm",
                    "Wind": f"{w['wind']:.0f} km/h",
                    "Temp": f"{w['temp']:.1f} °C"
                })
            bar.progress((i + 1) / len(waypoints))
        
        bar.empty()
        
        # Resultaat
        df = pd.DataFrame(results)
        
        def color_risk(val):
            return f'color: {"red" if val == "WET" else "green"}; font-weight: bold'

        st.dataframe(df.style.map(color_risk, subset=['Status']), use_container_width=True)
        
        # Samenvatting
        n_wet = len(df[df['Status'] == 'WET'])
        if n_wet == 0:
            st.success("ADVIES: Volledig Slicks (Hele proef droog)")
        elif n_wet == len(df):
            st.error("ADVIES: Full Wets (Hele proef nat)")
        else:
            st.warning(f"ADVIES: Crossover! {n_wet} sectoren zijn nat. Check de tabel waar de regen valt.")
            
    else:
        st.info("Upload een GPX bestand in de zijbalk om te beginnen.")