import streamlit as st
import pandas as pd
from datetime import datetime
from weather_api import get_weather
from weather_db import save_weather_reading, get_weather_history

st.set_page_config(page_title="Weather Module", layout="wide")
st.title("Weather Module - Smart Disaster Prediction System")

city = st.text_input("Enter District/City Name:", "Kathmandu")

if st.button("Get Weather"):
    with st.spinner("Fetching weather..."):
        result = get_weather(city)

    if "error" in result:
        st.error(result["error"])
    else:
        save_weather_reading(result)
        st.success("Weather data loaded and saved to history!")

        icon_url = f"https://openweathermap.org/img/wn/{result['icon']}@2x.png"
        st.image(icon_url)

        st.subheader(f"Weather in {result['city']}")
        st.write(f"☁️ {result['description'].title()}")

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Temperature", f"{result['temperature']}°C")
            st.metric("Feels Like", f"{result['feels_like']}°C")
            st.metric("Humidity", f"{result['humidity']}%")
        with col2:
            st.metric("Wind Speed", f"{result['wind_speed']} m/s")
            st.metric("Rainfall", f"{result['rainfall']} mm")
            st.metric("Pressure", f"{result['pressure']} hPa")

        st.write("Last Updated:", datetime.now().strftime("%d-%m-%Y %H:%M"))

st.divider()

# ---------------- Weather History (formatted table) ----------------
st.subheader(f"Recent Weather History for {city}")

history = get_weather_history(city=city, limit=10)

if history:
    df = pd.DataFrame(history, columns=[
        "ID", "City", "Timestamp", "Temp (°C)", "Feels Like (°C)",
        "Humidity (%)", "Pressure (hPa)", "Wind Speed (m/s)",
        "Rainfall (mm)", "Description", "Icon"
    ])

    # Clean up for display: nicer timestamp, drop columns we don't need to show
    df["Timestamp"] = pd.to_datetime(df["Timestamp"]).dt.strftime("%d-%m-%Y %H:%M")
    df["Description"] = df["Description"].str.title()
    df_display = df[[
        "Timestamp", "Temp (°C)", "Feels Like (°C)", "Humidity (%)",
        "Rainfall (mm)", "Wind Speed (m/s)", "Pressure (hPa)", "Description"
    ]]

    st.dataframe(df_display, use_container_width=True, hide_index=True)
else:
    st.info("No history yet for this city. Click 'Get Weather' to start logging.")