from typing import Any
import pandas as pd
from pandas import DataFrame

from models.database_model import WeatherDatabase


class DBDataProcessor:
    def __init__(self, db: WeatherDatabase, measurement_units:dict[str, str]) -> None:
        self.db = db
        self.cities: list[dict[str, Any]] = db.get_all_cities()
        self.total_records:int = db.get_total_records()
        self.measurement_units = measurement_units

    def select_records(self, selected_city:str, days:int) -> tuple[DataFrame, DataFrame]:
        df: DataFrame = pd.DataFrame(self.db.get_history(selected_city, days))
        display_df = df[["weather_time", "city", "temperature", "feels_like",
                         "humidity", "pressure", "wind_speed", "description"]].copy()
        display_df.columns = ["Data Pogody", "Miasto", f"Temp ({self.measurement_units['temperature']})",
                              f"Odczuwalna ({self.measurement_units['temperature']})",
                              "Wilgotność (%)", "Ciśnienie (hPa)", f"Wiatr ({self.measurement_units['wind_speed']})", "Opis"]

        return df, display_df