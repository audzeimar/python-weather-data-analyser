# Weather Data Analyser

A web application for reading and analyzing current weather data and weather forecasts for a chosen city. It also lets you save the current weather and forecast to a local database for later historical analysis.

Weather data is fetched from OpenWeatherMap(https://openweathermap.org/)

---

## Project structure

```
├── Application.py          # entry point — application controller
├── models/
│   ├── weather_model.py    # API communication, data models (dataclasses)
│   └── database_model.py   # database layer
├── data_processors/
│   ├── forecast_data_analyzer.py  # statistical analysis and chart generation
│   └── DBDataProcessor.py         # processes database data for display
├── ui_classes/
│   ├── MainUI.py           # main view, header, tabs
│   ├── ForecastUI.py       # weather forecast tab
│   ├── PlotsUI.py          # charts tab
│   ├── StatsUI.py          # statistics tab
│   ├── SettingsUI.py       # settings panel
│   └── WeatherHistoryUI.py # data history tab
├── utils/
│   ├── ApplicationState.py   # session state management
│   ├── session_cache.py      # results cache with TTL
│   ├── measurement_units.py  # unit definitions (metric / imperial)
│   └── ui_helpers.py         # helper functions for rendering charts
├── tests/
│   └── test_weather_app.py # unit tests (pytest)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── start.bat               # launch script for Windows
```

---

## Installation
1. Download the repository archive and unpack it.
2. Create a .env file based on the .env.example template.
3. Open the .env file and enter your OpenWeatherMap API key:
   ```
   OPEN_WEATHER_MAP_KEY=your_key_here
   ```
   You can get a free key after registering at openweathermap.org (https://openweathermap.org/api).

---

## Running the application

The application can be started in two ways.

### Option 1: Docker (recommended, requires Docker)
1. Open a terminal in the application folder.
2. Run:
   ```
   docker compose up --build
   ```
3. Open your browser at **http://localhost:8501**.

### Option 2: Manual run (requires Python and pip)

1. Open a terminal in the application folder.
2. *(Optional)* Create and activate a virtual environment:
   **Windows**:
   ```cmd
   python -m venv venv
   venv\Scripts\activate
   ```
   **Linux/macOS**:
   ```cmd
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install the required libraries:
   ```
   pip install -r requirements.txt
   ```
4. Run the application:
   **Windows** — run start.bat, or in the terminal:
   ```
   python -m streamlit run Application.py
   ```
   **Linux/macOS:**
   ```
   python3 -m streamlit run Application.py
   ```

The application opens in your web browser at http://localhost:8501. The terminal window must stay open — closing it stops the application.

---

## User guide

### Searching for weather data

After launching the app, choose a search mode:

- **City name** — type a city name (e.g. Wrocław, London).
- **Postal code** — ype a postal code and a two-letter country code (e.g. 50-001, PL).

Then click **"Search weather data"**. The results appear in the tabs below.

---

### Data tabs

Once the data is loaded, four tabs are available:

#### Weather forecast
Shows the current weather and the forecast for upcoming time points (every 3 hours, over 5 days). From the dropdown you can pick a specific moment and view its parameters: temperature, feels-like temperature, humidity, atmospheric pressure, wind speed, and a description. Forecast points also show the probability of precipitation.

#### Weather forecast charts
Charts showing how weather parameters change over time: temperature (actual and feels-like), humidity, atmospheric pressure, and wind speed. The charts can be scrolled horizontally when they cover a long time range.

#### Statistical analysis of forecast data
Forecast statistics grouped by day. Two views are available:
- **Basic information** — minimum, maximum, and average temperature, humidity, pressure, and wind speed.
- **Full statistics** — additionally includes the standard deviation for all parameters.

#### Historical weather data analysis
A view of data previously saved to the local database. You can select a city and a range of the last X days (slider 1–90). 

---

### Saving data to the database

Weather data (current + forecast) can be saved to the local database in two ways:

- **Manually** — click the **"💾Save current data to database"** button shown below the tabs after searching for a city.
- **Automatically** — enable the **"Automatically save data to the database after each search"**option in the settings menu.

Saved data is available in the **Historical weather data analysis** tab.

---

### Settings menu

The settings menu is in the top-right corner of the screen (the **⚙️ Option** button). Available options:

| Option | Description |
|---|---|
| **Cache TTL (minutes)** | How long search results stay valid in the cache (5–60 min). After the TTL expires, searching for the same city again fetches fresh data from the API. |
| **Data unit type** | Choose between **SI (metric)** units (°C, m/s) and **imperial** units (°F, mph).Changing units clears the cache and the database (data in different units is inconsistent). |
| **Automatically save data** | Toggle for auto-saving to the database after each search. |
| **Clear cache** | Removes temporarily stored search results from the session memory. |
| **Clear database** | Removes all records from the local history database (irreversible operation). |
| **💾 Save settings** | Saves the current settings (TTL, units, auto-save) to a configuration file — they will be active on the next launch. |

---



