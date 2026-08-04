import streamlit as st
from datetime import datetime
from weatgher.weather_api import get_weather

st.title("Weather Module - Smart Disaster Prediction System")

city = st.text_input("Enter District/City Name:", "Kathmandu")

if st.button("Get Weather"):
    with st.spinner("Fetching weather..."):
        result = get_weather(city)

    if "error" in result:
        st.error(result["error"])
    else:
        st.success("Weather data loaded successfully!")

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