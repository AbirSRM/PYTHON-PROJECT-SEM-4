import requests
import pandas as pd
import plotly.express as px
import tkinter as tk
from tkinter import ttk, scrolledtext, END, StringVar
from ttkthemes import ThemedTk
import threading
import webbrowser
import os
import tempfile

# OpenWeatherMap API key
API_KEY = "bda3852b40fc38f040518743ec07a933"
BASE_URL = "http://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "http://api.openweathermap.org/data/2.5/forecast"

# List of cities to track
cities = ["London", "New York", "Tokyo", "Sydney"]

# Global variables
weather_cache = {}
map_file = os.path.join(tempfile.gettempdir(), "weather_map.html")
fig = px.scatter_geo(title="Live Weather Dashboard")  # Initialize empty figure

def fetch_weather(city):
    """Fetch real-time weather data with caching."""
    if city in weather_cache:
        return weather_cache[city]
    
    params = {"q": city, "appid": API_KEY, "units": "metric"}
    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            weather = {
                "city": city,
                "temperature": data["main"]["temp"],
                "humidity": data["main"]["humidity"],
                "conditions": data["weather"][0]["description"],
                "lat": data["coord"]["lat"],
                "lon": data["coord"]["lon"],
            }
            weather_cache[city] = weather
            return weather
    except Exception:
        return None

def fetch_forecast(city):
    """Fetch 5-day forecast with error handling."""
    params = {"q": city, "appid": API_KEY, "units": "metric"}
    try:
        response = requests.get(FORECAST_URL, params=params, timeout=10)
        return response.json()["list"] if response.ok else None
    except Exception:
        return None

def update_map(weather_data):
    """Update the map figure with new data."""
    global fig
    df = pd.DataFrame(weather_data)
    fig = px.scatter_geo(
        df,
        lat="lat",
        lon="lon",
        hover_name="city",
        size="temperature",
        color="temperature",
        projection="natural earth",
        title="Live Weather Dashboard"
    )
    fig.write_html(map_file, auto_open=False)

def update_dashboard(text_widget, city_var, status_var):
    """Update all dashboard components."""
    text_widget.delete(1.0, END)
    all_weather = []
    
    # Fetch data in parallel using threads
    threads = []
    results = {}
    
    def worker(city):
        results[city] = fetch_weather(city)
    
    for city in cities + [city_var.get().strip()]:
        if city:
            t = threading.Thread(target=worker, args=(city,))
            threads.append(t)
            t.start()
    
    for t in threads:
        t.join()
    
    # Process results
    for city in cities + [city_var.get().strip()]:
        if city and city in results:
            weather = results[city]
            if weather:
                all_weather.append(weather)
                display_weather(city, text_widget)
                if city == city_var.get().strip():
                    display_forecast(city, text_widget)
    
    update_map(all_weather)
    webbrowser.open(f"file://{map_file}", new=0)  # Reuse same browser tab
    status_var.set("Updated: " + pd.Timestamp.now().strftime("%H:%M:%S"))

def display_weather(city, widget):
    """Show formatted weather data."""
    weather = fetch_weather(city)
    if weather:
        widget.insert(END, f"🌡 {weather['city']}:\n")
        widget.insert(END, f"   Temperature: {weather['temperature']}°C\n")
        widget.insert(END, f"   Humidity: {weather['humidity']}%\n")
        widget.insert(END, f"   Conditions: {weather['conditions'].title()}\n\n")

def display_forecast(city, widget):
    """Show formatted forecast data."""
    forecast = fetch_forecast(city)
    if forecast:
        widget.insert(END, f"📅 5-Day Forecast for {city}:\n")
        for entry in forecast[:8]:  # Show first 8 intervals (≈2 days)
            dt = pd.to_datetime(entry["dt_txt"]).strftime("%a %H:%M")
            widget.insert(END, 
                f"   {dt}: {entry['main']['temp']}°C | "
                f"{entry['weather'][0]['description'].title()}\n"
            )
        widget.insert(END, "\n")

# UI Setup
root = ThemedTk(theme="equilux")  # Use a modern theme
root.title("Weather Dashboard Pro")
root.geometry("1000x700")
root.configure(bg="#f0f0f0")  # Light background

# Custom styles
style = ttk.Style()
style.configure("TFrame", background="#f0f0f0")
style.configure("TLabel", background="#f0f0f0", font=("Roboto", 12))
style.configure("TButton", font=("Roboto", 12, "bold"), padding=10, relief="flat")
style.map("TButton", background=[("active", "#4CAF50")])  # Hover effect
style.configure("TEntry", font=("Roboto", 12), padding=5)

# Main frame
main_frame = ttk.Frame(root, padding=20)
main_frame.pack(fill=tk.BOTH, expand=True)

# Header
header_frame = ttk.Frame(main_frame)
header_frame.pack(fill=tk.X, pady=10)

ttk.Label(header_frame, text="🌤 Weather Dashboard Pro", font=("Roboto", 24, "bold")).pack(side=tk.LEFT)

# Search bar
search_frame = ttk.Frame(main_frame)
search_frame.pack(fill=tk.X, pady=10)

city_var = StringVar()
search_entry = ttk.Entry(search_frame, textvariable=city_var, width=30)
search_entry.pack(side=tk.LEFT, padx=5, ipady=5)

search_button = ttk.Button(search_frame, text="🔍 Search & Update", 
                          command=lambda: threading.Thread(
                              target=update_dashboard, 
                              args=(text_widget, city_var, status_var)
                          ).start())
search_button.pack(side=tk.LEFT, padx=5)

# Weather display
text_widget = scrolledtext.ScrolledText(
    main_frame, 
    width=80, 
    height=20,
    font=("Roboto", 12),
    wrap=tk.WORD,
    bg="#ffffff",  # White background for text area
    fg="#333333",  # Dark text
    bd=0,  # No border
    highlightthickness=0  # No highlight
)
text_widget.pack(pady=10, fill=tk.BOTH, expand=True)

# Status bar
status_var = StringVar(value="Ready")
status_bar = ttk.Label(main_frame, textvariable=status_var, font=("Roboto", 10), foreground="#666666")
status_bar.pack(side=tk.BOTTOM, fill=tk.X)

# Initial update
update_dashboard(text_widget, city_var, status_var)

# Schedule periodic updates
def auto_update():
    threading.Thread(
        target=update_dashboard,
        args=(text_widget, city_var, status_var)
    ).start()
    root.after(300000, auto_update)  # 5 minutes

auto_update()
root.mainloop()