
from typing import Union
import pandas as pd
from pandas import DataFrame, Series
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from models.weather_model import WeatherData, ForecastPoint, CurrentWeather
import matplotlib.dates as mdates

COLORS = {
    "temperature": "#4FACFE", "feels_like": "#F38BA8",
    "humidity": "#89DCEB",    "pressure":   "#A6E3A1",
    "wind_speed": "#CBA6F7",  "bg": "#1E2130",
    "axes": "#181825",        "grid": "#313244", "text": "#CDD6F4",
}

class ForecastDataAnalyzer:
    def __init__(self, data:WeatherData|None = None, df:DataFrame|None = None) -> None:

        if data is not None:
            self.weather_points:DataFrame = DataFrame(data = self._weather_entries_to_dict(data))
            current: CurrentWeather = data.current
            self.city: str|None = current.city
            self.country: str = current.country
            self.lat: float = current.lat
            self.lon: float = current.lon
            self.time_col:str = 'timestamp'
        elif df is not None:
            self.weather_points = df
            self.time_col = 'weather_time'
            self.city = None
        else:
            raise AttributeError("Either WeatherData or DataFrame must be provided")

        #resampling the data so that X-axis step is the same time
        self.weather_points[self.time_col] = pd.to_datetime(self.weather_points[self.time_col])
        self.weather_points = self.weather_points.sort_values(by=self.time_col)
        self.weather_points = self.weather_points.set_index(self.time_col)
        self.weather_points = self.weather_points.resample('3h').mean(numeric_only=True).interpolate(method='linear')
        self.weather_points = self.weather_points.reset_index()

    def calculate_forecasted_stats(self) -> DataFrame:
        dates:Series = self.weather_points[self.time_col].dt.date
        stats:DataFrame = self.weather_points.groupby(dates).agg({
            'temperature': ['min', 'max', 'mean', 'std'],
            'feels_like': ['min', 'max', 'mean', 'std'],
            'humidity': ['min', 'max', 'mean', 'std'],
            'pressure': ['min', 'max', 'mean', 'std'],
            'wind_speed': ['min', 'max', 'mean', 'std'],
        }).round(2)

        stats.columns = ['_'.join(col).strip() for col in stats.columns.values]

        return stats

    def calculate_temperature_plot(self) -> tuple[Figure, Axes]:
        return self._calculate_plot(self.weather_points[self.time_col],
                                    self.weather_points['temperature'],
                                    "Wykres prognozy temperatury",
                                    "Czas", "Temperatura",
                                    self.weather_points['feels_like'], "Rzeczywista temperatura",
                                    "Odczuwana temperatura")

    def calculate_humidity_plot(self) -> tuple[Figure, Axes]:
        return self._calculate_plot(self.weather_points[self.time_col],
                                    self.weather_points['humidity'],
                                    "Wykres prognozy wilgotności",
                                    "Czas", "Wilgotność")

    def calculate_pressure_plot(self) -> tuple[Figure, Axes]:
        return self._calculate_plot(self.weather_points[self.time_col],
                                    self.weather_points['pressure'],
                                    "Wykres prognozy ciśnienia",
                                    "Czas", "Ciśnienie")

    def calculate_wind_speed_plot(self) -> tuple[Figure, Axes]:
        return self._calculate_plot(self.weather_points[self.time_col],
                                    self.weather_points['wind_speed'],
                                    "Wykres prognozy prędkości powietrza",
                                    "Czas", "Prędkość powietrza")

    def _calculate_plot(self, x_data:Series, y_data:Series, title:str, x_label:str, y_label:str,  y2_data:Series|None = None, y1_label:str|None = None, y2_label:str|None = None) -> tuple[Figure, Axes]:
        """Funkcja pomocnicza do rysowanie wykresów typu plot"""
        fig:Figure
        ax:Axes
        fig,ax = plt.subplots(figsize=(6, 4))

        # ciemne tło wykresu i osi
        fig.patch.set_facecolor(COLORS["bg"])
        ax.set_facecolor(COLORS["axes"])


        ax.plot(x_data, y_data, color='blue', label = y1_label)
        if y2_data is not None:
            ax.plot(x_data, y2_data, color='red', label = y2_label)
        if self.city:
            ax.set_title(f"{title} dla miasta {self.city} w kraju {self.country} o współrzędnych geograficznych {self.lat}, {self.lon}")
        else:
            ax.set_title(title)

        # kolor tekstu tytułu, etykiet i znaczników osi
        ax.title.set_color(COLORS["text"])
        ax.xaxis.label.set_color(COLORS["text"])
        ax.yaxis.label.set_color(COLORS["text"])
        ax.tick_params(colors=COLORS["text"])
        for spine in ax.spines.values():
            spine.set_edgecolor(COLORS["grid"])

        ax.xaxis.set_major_locator(mdates.HourLocator(interval=3))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)
        if y1_label or y2_label:
            ax.legend(facecolor=COLORS["bg"], edgecolor=COLORS["grid"], labelcolor=COLORS["text"])

        # ciemna siatka 
        ax.grid(color=COLORS["grid"], linestyle='--', linewidth=0.6, alpha=0.7)

        fig.autofmt_xdate()
        return fig, ax

    def _weather_entries_to_dict(self, data:WeatherData) -> dict[str, list]:
        """Funkcja pomocnicza do sparsowania obiektu WeatherData na słownik"""
        all_data_points:list[Union[CurrentWeather, ForecastPoint]] = [data.current] + data.forecast

        weather_data_dict: dict[str, list] = {'timestamp': [point.timestamp for point in all_data_points],
                                              'temperature': [point.temperature for point in all_data_points],
                                              'feels_like': [point.feels_like for point in all_data_points],
                                              'humidity': [point.humidity for point in all_data_points],
                                              'pressure': [point.pressure for point in all_data_points],
                                              'wind_speed': [point.wind_speed for point in all_data_points]}

        return weather_data_dict



