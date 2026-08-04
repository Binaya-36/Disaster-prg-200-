import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("WEATHER_API_KEY")


def get_weather(city):
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city,
        "appid": API_KEY,
        "units": "metric"
    }

    response = requests.get(url, params=params)
    data = response.json()

    if response.status_code != 200:
        return {"error": "City not found. Please enter a valid district or city."}

    rainfall = data.get("rain", {}).get("1h", 0)

    weather_info = {
        "city": data["name"],
        "temperature": data["main"]["temp"],
        "feels_like": data["main"]["feels_like"],
        "humidity": data["main"]["humidity"],
        "pressure": data["main"]["pressure"],
        "wind_speed": data["wind"]["speed"],
        "rainfall": rainfall,
        "description": data["weather"][0]["description"],
        "icon": data["weather"][0]["icon"]
    }

    return weather_info


if __name__ == "__main__":
    result = get_weather("Kathmandu")
    print(result)
