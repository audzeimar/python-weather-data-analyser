from pathlib import Path
from typing import Any

from matplotlib.axes import Axes
from matplotlib.figure import Figure
from pandas import DataFrame

from data_processors.DBDataProcessor import DBDataProcessor
from data_processors.forecast_data_analyzer import ForecastDataAnalyzer
from models.weather_model import WeatherDataModel, WeatherData, WeatherAPIError, CityNotFoundError, UnauthorizedError
from models.database_model import WeatherDatabase
from ui_classes.MainUI import MainUI
from utils.ApplicationState import ApplicationState
from dotenv import load_dotenv
import os
import json
import streamlit as st

from utils.measurement_units import METRIC, IMPERIAL
from utils.session_cache import SessionCache

# Główna klasa aplikacji, koordynuje przepływ danych pomiędzy UI, BD a API
class Application:
    def __init__(self) -> None:
        load_dotenv()
        self.settings_file: str = os.environ.get("CONFIG_FILE")
        settings: dict[str, Any] = self._load_settings()

        # sprawdzanie jednostek
        if settings['units'] == 'SI (metryczne)':
            self.ui_controller: MainUI = MainUI(METRIC)
        else:
            self.ui_controller: MainUI = MainUI(IMPERIAL)

        self.state_controller:ApplicationState = ApplicationState()


    # główna pętla, uruchamianie aplikacji
    def run(self):
        pending_toast = self.state_controller.get("pending_toast")
        if pending_toast:
            self.ui_controller.render_success_toast(pending_toast, icon="🔄")
            self.state_controller.set("pending_toast", None)

        settings:dict[str, Any] = self._load_settings()

        weather_model: WeatherDataModel
        cache_engine: SessionCache

        #inicjalizacja/pobranie modeli na podstawie ustawień
        weather_model, cache_engine = self._initialize_session(settings)

        new_settings = self.ui_controller.render_header_and_settings(settings['ttl'],
                                                                                settings['units'], settings['db_auto_save'])
        if new_settings["clear_cache"]:
            cache_engine.clear()
            self._clear_active_data_state()
            self.ui_controller.rerun()

        if new_settings['clear_db']:
            self._initialize_database().clear_database()
            self.ui_controller.rerun()

        if new_settings['save_settings']:
            self._save_settings(new_settings['ttl'], new_settings['units'], new_settings['db_auto_save'])
            if new_settings['units'] == 'SI (metryczne)':
                self.ui_controller.set_measurement_units(METRIC)
            else:
                self.ui_controller.set_measurement_units(IMPERIAL)

            if new_settings['ttl'] != settings["ttl"] or new_settings['units'] != settings["units"]:#czyści cache w przypadku zmiany ustawień cachowania lub jednostekużywanych w systemie
                if new_settings['units'] != settings["units"]:
                    self._initialize_database().clear_database()
                cache_engine.clear()
                self._clear_active_data_state()
                self.state_controller.set("pending_toast", "Ustawienia zmienione. Cache został wyczyszczony!")
                self.ui_controller.rerun()
            else:
                self.ui_controller.render_success_toast("Ustawienia zmienione", icon="ℹ️")


        search_option: str
        search_val: str
        country_val: str
        search_option, search_val, country_val = MainUI.render_input_section()

        if self.ui_controller.render_search_button():
            cache_key:str|None = None
            weather_data:WeatherData|None = None

            # Generowanie unik klucza dla pamięci podr w zależności od metody wyszukiwania
            if search_option == "Nazwa Miasta":
                cache_key = SessionCache().key_name(search_val)
            elif search_option == "Kod Pocztowy":
                cache_key = SessionCache().key_zip(search_val, country_val)

            if cache_key:
                weather_data = cache_engine.get(cache_key)
                if not weather_data:
                    try:
                        if search_option == "Nazwa Miasta":
                            weather_data = weather_model.fetch_weather(search_val)
                        elif search_option == "Kod Pocztowy":
                            weather_data = weather_model.fetch_weather_by_zip(search_val, country_val)

                        if weather_data:
                            cache_engine.set(cache_key, weather_data)

                            if settings["db_auto_save"]:
                                db: WeatherDatabase = self._initialize_database()
                                db.save_weather(weather_data)
                                st.toast("💾 Dane automatycznie zapisane do bazy danych.")

                    # błęd autoryzacji (np zły klucz API)
                    except UnauthorizedError as e:
                        self.ui_controller.render_error(str(e))
                    # błęd braku szukanego miasta
                    except CityNotFoundError as e:
                        self.ui_controller.render_error(str(e))
                    # ogólne błędy API
                    except WeatherAPIError as e:
                        self.ui_controller.render_error(str(e))
                    # błęd walidacji danych wejściowych
                    except ValueError as e:
                        self.ui_controller.render_error(str(e))

            if weather_data:
                self.state_controller.set("active_weather_data", weather_data)

                analyzer:ForecastDataAnalyzer = ForecastDataAnalyzer(weather_data)

                stats:DataFrame = analyzer.calculate_forecasted_stats()
                self.state_controller.set("active_weather_data_stats", stats)
                self.state_controller.set("active_weather_data_plots", self._calculate_plots(analyzer))
        
        # pobranie aktywn danych pogodowych aby  wyrenderować w zakładkach
        active_data = self.state_controller.get("active_weather_data")

        if active_data:
            if settings['units'] == 'SI (metryczne)':
                units: dict[str, str] = METRIC
            else:
                units: dict[str, str] = IMPERIAL

            display_df:DataFrame|None = None
            analyzer:ForecastDataAnalyzer|None = None
            # procesor danych BD, łączy model bazy z jednostkami miary
            db_processor: DBDataProcessor = DBDataProcessor(self._initialize_database(), units)
            
            try:
                # przypisanie 1szego dostępn miasta z bazy jako domyślnego, jeśli BD nie jest pusta
                default_city = db_processor.cities[0]['city'] if db_processor.cities else None
                
                # odczyt parametrów filtracji historii
                selected_city:str = st.session_state.get("db_selected_city", default_city)
                days:int = st.session_state.get("db_days", 30)
                
                if selected_city is not None:
                    df:DataFrame
                    display_df
                    df, display_df = db_processor.select_records(selected_city, days)
                    analyzer = ForecastDataAnalyzer(df=df)

            except Exception as e:
                # przechwycenie i wypisanie błędu w konsoli serwera zamiast wysypania całej aplikacji
                print(f"Błąd podczas ładowania danych historycznych z bazy: {e}")

            self.ui_controller.render_tabs(self.state_controller.get("active_weather_data_stats"),
                                           self.state_controller.get("active_weather_data_plots"), active_data, display_df,
                                           self._calculate_plots(analyzer), db_processor.cities, db_processor.total_records)

            if self.ui_controller.render_db_save_button():
                db: WeatherDatabase = self._initialize_database()
                db.save_weather(active_data)
                c = active_data.current
                self.state_controller.set("pending_toast", f"✅ Zapisano dane dla **{c.city}, {c.country}**")
                # przeład aby odśwież tabel historii i sekcje statystyk bazy danych
                self.ui_controller.rerun()



    # inicjal lub pobiera ze stanu instancję modelu API oraz systemu pamięci podręcznej
    def _initialize_session(self, settings:dict[str, Any]) -> tuple[WeatherDataModel, SessionCache]:

        api_key:str = os.environ.get("OPEN_WEATHER_MAP_KEY")

        weather_model: WeatherDataModel = self.state_controller.get("weather_model")
        # jeśli model nie był jeszcze zainicj w tej sesji
        if not weather_model:
            if settings['units'] == "SI (metryczne)":
                weather_model = WeatherDataModel(api_key, units = 'metric')
            else:
                weather_model = WeatherDataModel(api_key, units = 'imperial')
            self.state_controller.set("weather_model", weather_model)

        cache_engine: SessionCache = self.state_controller.get("cache_engine")
        # if silnik cache nie istnieje w sesji
        if not cache_engine:
            cache_engine = SessionCache()
            self.state_controller.set("cache_engine", cache_engine)
        cache_engine.set_ttl(settings['ttl'])

        return weather_model, cache_engine
    
    # pobiera istn lub tworzy nową instancję managera bazy danych WeatherDatabase
    def _initialize_database(self) -> WeatherDatabase:
        db: WeatherDatabase = self.state_controller.get("database")

        if not db:
            db_path_str: str | None = os.environ.get("DB_PATH")
            db_path: Path | None = Path(db_path_str) if db_path_str else None
            db = WeatherDatabase(db_path)
            self.state_controller.set("database", db)
        return db

    # wczytuje ustawienia  z pliku konfiguracyjnego JSON lub zwraca wart domyślne
    def _load_settings(self) -> dict[str, Any]:
        defaults: dict[str, Any] = {"ttl": 10, "units": "SI (metryczne)", "db_auto_save": False}
        if self.settings_file and os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    # uzupełnia brakujące klucze wartościami domyślnymi
                    return {**defaults, **loaded}
            except Exception:
                pass
        return defaults

    # zapisuje przekaz parametry konfig do pliku JSON
    def _save_settings(self, ttl:int, units:str,db_auto_save:bool) -> None:
        settings = {"ttl":ttl, "units":units, "db_auto_save":db_auto_save}
        with open(self.settings_file, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)

    # Prywatna metoda pomocnicza do czyszczenia aktualnie wyświetlanych danych z UI
    def _clear_active_data_state(self) -> None:
        self.state_controller.set("active_weather_data", None)
        self.state_controller.set("active_weather_data_stats", None)
        self.state_controller.set("active_weather_data_plots", None)
        self.state_controller.set("weather_model", None)
        self.state_controller.set("database", None)

    @staticmethod
    # metoda stat generująca zestaw wykresów pogodowych przy użyciu dostarczo analizatora
    def _calculate_plots(analyzer: ForecastDataAnalyzer | None) -> dict[str, tuple[Figure, Axes]] | None:
        if not analyzer:
            return None
        plots: dict[str, tuple[Figure, Axes]] = {'temperature': analyzer.calculate_temperature_plot(),
                                                 'humidity': analyzer.calculate_humidity_plot(),
                                                 'pressure': analyzer.calculate_pressure_plot(),
                                                 'wind_speed': analyzer.calculate_wind_speed_plot()}
        return plots


if __name__ == "__main__":
    app = Application()
    app.run()
