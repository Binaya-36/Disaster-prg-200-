import sqlite3
from datetime import datetime

DB_NAME = "disaster_system.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_weather_table():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS weather (
            weather_id INTEGER PRIMARY KEY AUTOINCREMENT,
            city TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            temperature REAL,
            feels_like REAL,
            humidity REAL,
            pressure REAL,
            wind_speed REAL,
            rainfall REAL,
            description TEXT,
            icon TEXT
        )
    """)
    conn.commit()
    conn.close()


def save_weather_reading(weather_data):
    """
    Saves one weather reading to history.
    Expects the dictionary returned by get_weather() in weather_api.py.
    """
    create_weather_table()  # make sure the table exists before inserting

    conn = get_connection()
    cur = conn.cursor()
    timestamp = datetime.now().isoformat(timespec="seconds")

    cur.execute("""
        INSERT INTO weather
        (city, timestamp, temperature, feels_like, humidity, pressure, wind_speed, rainfall, description, icon)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        weather_data.get("city"),
        timestamp,
        weather_data.get("temperature"),
        weather_data.get("feels_like"),
        weather_data.get("humidity"),
        weather_data.get("pressure"),
        weather_data.get("wind_speed"),
        weather_data.get("rainfall"),
        weather_data.get("description"),
        weather_data.get("icon"),
    ))

    conn.commit()
    conn.close()


def get_weather_history(city=None, limit=50):
    """
    Returns past weather readings, most recent first.
    Pass a city name to filter to just that city.
    """
    create_weather_table()

    conn = get_connection()
    cur = conn.cursor()

    if city:
        cur.execute("""
            SELECT * FROM weather WHERE city = ? COLLATE NOCASE
            ORDER BY timestamp DESC LIMIT ?
        """, (city, limit))
    else:
        cur.execute("""
            SELECT * FROM weather
            ORDER BY timestamp DESC LIMIT ?
        """, (limit,))

    rows = cur.fetchall()
    conn.close()
    return rows


def get_all_cities_logged():
    """Returns a list of distinct city names that have history saved."""
    create_weather_table()

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT city FROM weather ORDER BY city")
    rows = cur.fetchall()
    conn.close()
    return [row[0] for row in rows]