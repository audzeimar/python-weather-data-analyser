# Testy jednostkowe - pytest
# python -m pytest tests/ -v wszystkie testy

import matplotlib
matplotlib.use('Agg') # zapobiega próbom otwierania okien graf z wykresami

import datetime
import os
import sys
import tempfile # bezpieczne tworzenie tymczas plików i katalogów
import time
from pathlib import Path
from unittest.mock import MagicMock, patch # tworzenie obiektów imitujących oraz dekoratora patch do podmieniania obiektów w locie

import pandas as pd
import pytest

# Dodajemy katalog nadrzędny do ścieżki Pythona
# importy (models., utils., data_processors.) będą działały bez instalowania pakietu
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from models.weather_model import (
    CurrentWeather, ForecastPoint, WeatherData, WeatherDataModel,
    WeatherAPIError, CityNotFoundError, UnauthorizedError,
)

from utils.session_cache import SessionCache
from models.database_model import WeatherDatabase
from data_processors.forecast_data_analyzer import ForecastDataAnalyzer
from data_processors.DBDataProcessor import DBDataProcessor
from utils.measurement_units import METRIC, IMPERIAL


# ------ Funkcje pomocnicze — do tworzenia danych wejściowych ------ 


# Tworzy CurrentWeather z domyślnymi wartościami, **kwargs nadpisuje wybrane pola
def _make_current(**kwargs) -> CurrentWeather:
    now = datetime.datetime.now().replace(minute=0, second=0, microsecond=0)
    defaults = dict(
        city="Warsaw", country="PL", lat=52.23, lon=21.01,
        temperature=15.0, feels_like=13.0, humidity=70, pressure=1013,
        wind_speed=5.0, wind_deg=180, description="Clear sky", icon_code="01d",
        sunrise=now.replace(hour=4),
        sunset=now.replace(hour=21),
        timestamp=now,
    )
    defaults.update(kwargs)
    return CurrentWeather(**defaults)

# generuje pojedynczy punkt prognozy pogody przesunięty o określoną liczbę godzin (domysl 3)
def _make_forecast_point(hours_offset: int = 3) -> ForecastPoint:
    now = datetime.datetime.now().replace(minute=0, second=0, microsecond=0) #punkt odniesienia czasu
    return ForecastPoint(
        timestamp=now + datetime.timedelta(hours=hours_offset), #obl czas przysł na podst przesunięcia
        temperature=14.0, feels_like=12.0, humidity=72, pressure=1012,
        wind_speed=4.1, description="Few clouds", icon_code="02d", pop=0.1,
    )

# Tworzy kompletny WeatherData z current + 5 punktami prognozy co 3 godziny,
# parametr city pozwala tworzyć dane dla różnych miast w testach bazy danych
def _make_weather_data(city: str = "Warsaw") -> WeatherData:
    return WeatherData(
        current=_make_current(city=city),
        forecast=[_make_forecast_point(i * 3) for i in range(1, 6)], 
    )

# Tworzy fałszywą odpowiedź HTTP imitującą requests.Response —
# MagicMock automatycznie tworzy atrybuty: status_code, ok, json(): status=200 → ok=True, inne kody → ok=False, data trafia do json()
def _make_response(status: int = 200, data: dict = None) -> MagicMock:
    r = MagicMock()
    r.status_code = status
    r.ok = (status == 200) # 200 -> właściwość .ok zwraca True, w przeciwnym razie False
    r.json.return_value = data or {} 
    return r

# Przykładowe dane JSON zwracane przez API dla aktualnej pogody (w testach parsowania zamiast wywołania API)
SAMPLE_CURRENT_JSON = {
    "name": "Warsaw", "dt": 1717232400,
    "coord": {"lat": 52.23, "lon": 21.01},
    "main": {"temp": 15.0, "feels_like": 13.0, "humidity": 70, "pressure": 1013},
    "wind": {"speed": 5.0, "deg": 180},
    "weather": [{"description": "clear sky", "icon": "01d"}],
    "sys": {"country": "PL", "sunrise": 1717207800, "sunset": 1717267200},
}

# Przykładowe dane JSON zwracane przez API dla prognozy pogody — lista dwóch punktów z różnymi warunkami i p-stwem opadów
SAMPLE_FORECAST_JSON = {
    "list": [
        {
            "dt": 1717243200,
            "main": {"temp": 14.0, "feels_like": 12.0, "humidity": 72, "pressure": 1012},
            "wind": {"speed": 4.0},
            "weather": [{"description": "few clouds", "icon": "02d"}],
            "pop": 0.1,  # prawdopodobieństwo opadów 10%
        },
        {
            "dt": 1717254000,
            "main": {"temp": 16.5, "feels_like": 14.5, "humidity": 65, "pressure": 1010},
            "wind": {"speed": 6.0},
            "weather": [{"description": "light rain", "icon": "10d"}],
            "pop": 0.6,  # prawdopodobieństwo opadów 60%
        },
    ]
}


# @pytest.fixture — wynik jest automatycznie wstrzykiwany do parametru testu o tej samej nazwie; 
# pytest tworzy nową instancję przed każdym testem który jej używa

@pytest.fixture
# WeatherDataModel z testowym kluczem API i jednostkami metrycznymi
def model() -> WeatherDataModel:
    return WeatherDataModel("test_key", units="metric")

@pytest.fixture
# Fixture konf-cy pamięć podr z czasem wygasania równym 1 minuta
def cache() -> SessionCache:
    return SessionCache(ttl_minutes=1)

@pytest.fixture
# Tymczasowa baza SQLite w tmp_path — wbudowany fixture pytest, każdy test dostaje czystą, izolowaną bazę danych
def db(tmp_path) -> WeatherDatabase:    
    return WeatherDatabase(db_path=tmp_path / "test.db")

@pytest.fixture
# Baza danych z wstępnie zapisanymi danymi dla Warsaw i Kraków — dla testów które wymagają istniejących rekordów
def db_with_data(db) -> WeatherDatabase:
    db.save_weather(_make_weather_data("Warsaw"))
    db.save_weather(_make_weather_data("Kraków"))   
    return db

@pytest.fixture
# Fixture symul-cy tryb analizy prognozy na bazie czystych struktur WeatherData
def analyzer_from_data() -> ForecastDataAnalyzer:
    base = datetime.datetime(2024, 6, 1, 12, 0)
    forecast = [
        ForecastPoint(
            timestamp=base + datetime.timedelta(hours=3 * i),
            temperature=15.0 + i,   # rośnie o 1 co punkt 
            feels_like=13.0 + i,
            humidity=70 - i, pressure=1013, wind_speed=5.0, # wilgotnośc maleje
            description="Clear", icon_code="01d", pop=0.0,
        )
        for i in range(9) # 9 kroków prognozy
    ]
    return ForecastDataAnalyzer(data=WeatherData(current=_make_current(), forecast=forecast))

@pytest.fixture
# Fixture symulujący tryb analizy danych historycznych pobranych z BD (struktura tabeli Pandas DataFrame))
def analyzer_from_df() -> ForecastDataAnalyzer:
    base = datetime.datetime(2024, 6, 1, 0, 0)
    df = pd.DataFrame({
        "weather_time": [
            # datetime do formatu ISO (zgodn z strukt BD)
            (base + datetime.timedelta(hours=3 * i)).isoformat()
            for i in range(10)
        ],
        "temperature": [10.0 + i * 0.5 for i in range(10)],
        "feels_like":  [8.0 + i * 0.5 for i in range(10)],
        "humidity":    [70 + i for i in range(10)],
        "pressure":    [1013 - i for i in range(10)],
        "wind_speed":  [3.0 + i * 0.1 for i in range(10)],
    })
    return ForecastDataAnalyzer(df=df)  



# ------ WeatherDataModel — inicjalizacja ------ 

# sprawdz reguły inicjal i walid parametrów wejściowych w konstr WeatherDataModel.
class TestWeatherDataModelInit:

    # pusty klucz API powinien rzucić ValueError zanim zostanie wysłany request
    def test_raises_on_empty_key(self):
        with pytest.raises(ValueError):
            WeatherDataModel("", units="metric")

    # poprawny (niepusty) klucz tworzy instancję bez wyjątku
    def test_creates_with_valid_key(self):
        assert WeatherDataModel("valid_key", units="metric") is not None

    # model akceptuje zarówno metryczne jak i imperialne jednostki
    def test_creates_with_imperial_units(self):
        assert WeatherDataModel("key", units="imperial") is not None



# ------ WeatherDataModel — parsowanie JSON -> dataclassy ------ 

# weryfik mechanizmy dekodowania i mapowania JSON z  API na ob Pythona
class TestWeatherDataModelParsing:

    # wyodrębnianie nazwy miasta, klucz 'name' w JSON
    def test_parse_current_city(self):
        assert WeatherDataModel._parse_current(SAMPLE_CURRENT_JSON).city == "Warsaw"

    # wyodrębnianie skrótu państwa , country - klucza 'sys.country' w JSON
    def test_parse_current_country(self):
        assert WeatherDataModel._parse_current(SAMPLE_CURRENT_JSON).country == "PL"

    # parsowanie temperatury, pytest.approx pozwala na porównanie wartości float z tolerancją
    def test_parse_current_temperature(self):
        c = WeatherDataModel._parse_current(SAMPLE_CURRENT_JSON)
        assert c.temperature == pytest.approx(15.0)

    # współrzędne geograficzne z kluczy 'coord.lat' i 'coord.lon' JSON
    def test_parse_current_coordinates(self):
        c = WeatherDataModel._parse_current(SAMPLE_CURRENT_JSON)
        assert c.lat == pytest.approx(52.23)
        assert c.lon == pytest.approx(21.01)

    # wilgotność i ciśnienie z sekcji 'main' JSON
    def test_parse_current_humidity_and_pressure(self):
        c = WeatherDataModel._parse_current(SAMPLE_CURRENT_JSON)
        assert c.humidity == 70
        assert c.pressure == 1013

    # API zwraca opis małymi literami ("clear sky")  _parse_current robi z tego "Clear sky"
    def test_parse_current_description_capitalized(self):
        c = WeatherDataModel._parse_current(SAMPLE_CURRENT_JSON)
        assert c.description[0].isupper()

    # CurrentWeather ma frozen=True — jest niemutowalny, próba zmiany pola -> FrozenInstanceError
    def test_parse_current_is_frozen(self):
        c = WeatherDataModel._parse_current(SAMPLE_CURRENT_JSON)
        with pytest.raises(Exception):
            c.city = "Kraków"  # type: ignore

    # czy iterator pętli przetworzył wszystkie punkty prognozy z listy JSON
    def test_parse_forecast_returns_two_points(self):
        assert len(WeatherDataModel._parse_forecast(SAMPLE_FORECAST_JSON)) == 2

    # weryf wartość temperatury w pierwszym punkcie prognozy
    def test_parse_forecast_first_temperature(self):
        pts = WeatherDataModel._parse_forecast(SAMPLE_FORECAST_JSON)
        assert pts[0].temperature == pytest.approx(14.0)

    # prawdopodobieństwo opadów (pop) z klucza 'pop' każdego elementu listy
    def test_parse_forecast_pop_values(self):
        pts = WeatherDataModel._parse_forecast(SAMPLE_FORECAST_JSON)
        assert pts[0].pop == pytest.approx(0.1)
        assert pts[1].pop == pytest.approx(0.6)

    # ciśnienie pierwszego punktu prognozy z klucza 'main.pressure'
    def test_parse_forecast_pressure(self):
        pts = WeatherDataModel._parse_forecast(SAMPLE_FORECAST_JSON)
        assert pts[0].pressure == 1012

    # jeśli API zwróci pustą listę 'list', model powinien zwrócić []
    def test_parse_forecast_empty_list(self):
        assert WeatherDataModel._parse_forecast({"list": []}) == []


# ------ WeatherDataModel — komunikacja z API ------ 

# weryf komunikację sieciową z API przy użyciu techniki mockowania (podmieniania modułów w locie)
class TestWeatherDataModelFetch:

    # @patch podmienia requests.Session.get na MagicMock — żadne realne żądania HTTP nie są wysyłane podczas testów

    # side_effect = lista -> pierwsze wywołanie mock_get zwraca dane aktualnej pogody (/weather),
    # drugie wywołanie zwraca dane prognozy (/forecast), bo fetch_weather woła API dwa razy
    @patch("models.weather_model.requests.Session.get")
    def test_fetch_by_name_returns_weather_data(self, mock_get, model):
        mock_get.side_effect = [
            _make_response(200, SAMPLE_CURRENT_JSON),
            _make_response(200, SAMPLE_FORECAST_JSON),
        ]
        result = model.fetch_weather("Warsaw")
        assert result.current.city == "Warsaw"
        assert len(result.forecast) == 2

    # ten sam schemat, ale dla wyszukiwania po kodzie pocztowym
    @patch("models.weather_model.requests.Session.get")
    def test_fetch_by_zip_returns_weather_data(self, mock_get, model):
        mock_get.side_effect = [
            _make_response(200, SAMPLE_CURRENT_JSON),
            _make_response(200, SAMPLE_FORECAST_JSON),
        ]
        assert isinstance(model.fetch_weather_by_zip("00-001", "PL"), WeatherData)

    # HTTP 404 oznacza że miasto nie istnieje w API -> CityNotFoundError
    @patch("models.weather_model.requests.Session.get")
    def test_raises_city_not_found_on_404(self, mock_get, model):
        mock_get.return_value = _make_response(404)
        with pytest.raises(CityNotFoundError):
            model.fetch_weather("XYZXYZ")

    # HTTP 401 oznacza błędny klucz API -> UnauthorizedError
    @patch("models.weather_model.requests.Session.get")
    def test_raises_unauthorized_on_401(self, mock_get, model):
        mock_get.return_value = _make_response(401)
        with pytest.raises(UnauthorizedError):
            model.fetch_weather("Warsaw")

    # HTTP 500 to błąd po stronie serwera -> ogólny WeatherAPIError
    @patch("models.weather_model.requests.Session.get")
    def test_raises_api_error_on_500(self, mock_get, model):
        mock_get.return_value = _make_response(500)
        with pytest.raises(WeatherAPIError):
            model.fetch_weather("Warsaw")

    # brak połączenia z internetem -> requests rzuca ConnectionError, model zamienia na WeatherAPIError
    @patch("models.weather_model.requests.Session.get")
    def test_raises_on_connection_error(self, mock_get, model):
        import requests
        mock_get.side_effect = requests.exceptions.ConnectionError
        with pytest.raises(WeatherAPIError):
            model.fetch_weather("Warsaw")

    # serwer nie odpowiada w czasie -> requests rzuca Timeout → WeatherAPIError
    @patch("models.weather_model.requests.Session.get")
    def test_raises_on_timeout(self, mock_get, model):
        import requests
        mock_get.side_effect = requests.exceptions.Timeout
        with pytest.raises(WeatherAPIError):
            model.fetch_weather("Warsaw")

    # pusty string jako nazwa miasta -> ValueError zanim zostanie wysłany request
    def test_raises_on_empty_city(self, model):
        with pytest.raises(ValueError):
            model.fetch_weather("")

    # sama spacja po .strip() daje pusty string -> ValueError
    def test_raises_on_whitespace_city(self, model):
        with pytest.raises(ValueError):
            model.fetch_weather("   ")

    # pusty kod pocztowy -> ValueError zanim zostanie wysłany request
    def test_raises_on_empty_zip(self, model):
        with pytest.raises(ValueError):
            model.fetch_weather_by_zip("")



# ------ Testy SessionCache ------ 

class TestSessionCache:

    # nieistniejący klucz powinien zwrócić None, nie rzucać wyjątku
    def test_get_returns_none_for_missing_key(self, cache):
        assert cache.get("nonexistent") is None

    # zapisany obiekt powinien być identycznie odczytany przez get()
    def test_set_and_get_returns_same_object(self, cache):
        data = {"temperature": 15.0, "city": "Warsaw"}
        cache.set("key1", data)
        assert cache.get("key1") == data

    # TTL = 0.001 min, po 0.1 s  wpis powinien wygasnąć, time.sleep() - przetestować upływ czasu
    def test_expired_entry_returns_none(self):
        short_cache = SessionCache(ttl_minutes=0.001)
        short_cache.set("k", "value")
        time.sleep(0.1) # sztuczne opóźnienie, aby przekroczyć czas ważności wpisu w cache
        assert short_cache.get("k") is None

    # wpis z pełnym TTL (1 min) nie powinien zniknąć od razu
    def test_non_expired_entry_is_accessible(self, cache):
        cache.set("k", "value")
        assert cache.get("k") == "value"

    # invalidate() usuwa jeden konkretny klucz, reszta cache pozostaje nienaruszona
    def test_invalidate_removes_specific_key(self, cache):
        cache.set("a", 1)
        cache.set("b", 2)
        cache.invalidate("a")
        assert cache.get("a") is None
        assert cache.get("b") == 2  # b ma nadal istnieć

    # clear() usuwa wszystkie wpisy naraz
    def test_clear_removes_all_entries(self, cache):
        cache.set("a", 1)
        cache.set("b", 2)
        cache.clear()
        assert cache.get("a") is None
        assert cache.get("b") is None

    # is_valid() zwraca True gdy klucz istnieje i nie wygasł
    def test_is_valid_true_for_existing(self, cache):
        cache.set("x", "data")
        assert cache.is_valid("x") is True

    # is_valid() zwraca False dla klucza którego nie ma w cache
    def test_is_valid_false_for_missing(self, cache):
        assert cache.is_valid("missing") is False

    # key_name() normalizuje wejście: "  Warsaw  " -> "name:warsaw"; zapobiega duplikatom przy różnej wielkości liter i spacjach wokół nazwy
    def test_key_name_normalizes_input(self):
        assert SessionCache.key_name("  Warsaw  ") == "name:warsaw"

    # key_name() zawsze zwraca małe litery niezależnie od wejścia
    def test_key_name_is_lowercase(self):
        assert "london" in SessionCache.key_name("London")

    # klucz ZIP powinien zawierać kod pocztowy i kod kraju małymi literami
    def test_key_zip_contains_code_and_country(self):
        key = SessionCache.key_zip("00-001", "PL")
        assert "00-001" in key
        assert "pl" in key

    # współrzędne są zaokrąglane do 2 miejsc po przecinku, zapobiega duplikatom dla geograficznie bliskich punktów
    def test_key_coords_rounds_to_two_decimal_places(self):
        key = SessionCache.key_coords(52.2298, 21.0118)
        assert "52.23" in key
        assert "21.01" in key

    # size zwraca liczbę wpisów w cache (wliczając wygasłe które nie zostały jeszcze usunięte)
    def test_size_counts_entries(self, cache):
        cache.set("a", 1)
        cache.set("b", 2)
        assert cache.size == 2

    # set_ttl() zmienia TTL tylko dla nowych wpisów — stare zachowują swój oryginalny czas
    def test_set_ttl_affects_new_entries_only(self, cache):
        cache.set_ttl(0.001)  # 0.06 sekundy dla nowych wpisów
        cache.set("new", "v")
        time.sleep(0.1)
        assert cache.get("new") is None


# ------ WeatherDatabase testy ------ 

class TestWeatherDatabase:
    # każdy test dostaje własną tymczasową bazę przez fixture db(tmp_path)

    # nowo utworzona baza danych powinna mieć 0 rekordów
    def test_new_database_is_empty(self, db):
        assert db.get_total_records() == 0

    # każdy zapis powinien zwiększyć liczbę rekordów (current + punkty prognozy)
    def test_save_increases_record_count(self, db):
        before = db.get_total_records()
        db.save_weather(_make_weather_data())
        assert db.get_total_records() > before

    # po zapisaniu danych get_history powinno zwrócić przynajmniej jeden rekord
    def test_get_history_returns_records_after_save(self, db):
        db.save_weather(_make_weather_data())
        assert len(db.get_history("Warsaw", days=30)) > 0

    # get_history filtruje po nazwie miasta — nie powinny wracać dane innych miast
    def test_get_history_filters_by_city(self, db):
        db.save_weather(_make_weather_data("Warsaw"))
        db.save_weather(_make_weather_data("Kraków"))
        records = db.get_history("Warsaw", days=30)
        assert all(r["city"] == "Warsaw" for r in records)

    # po zapisaniu dwóch miast oba powinny być widoczne na liście get_all_cities()
    def test_get_all_cities_lists_saved_cities(self, db_with_data):
        city_names = [c["city"] for c in db_with_data.get_all_cities()]
        assert "Warsaw" in city_names
        assert "Kraków" in city_names

    # clear_database() powinno usunąć wszystkie rekordy ze wszystkich miast
    def test_clear_database_removes_all(self, db):
        db.save_weather(_make_weather_data())
        db.clear_database()
        assert db.get_total_records() == 0

    # zapytanie o nieistniejące miasto powinno zwrócić [], nie None ani wyjątek
    def test_history_empty_for_unknown_city(self, db):
        assert db.get_history("Nieznane Miasto", days=30) == []

    # każdy rekord historii musi zawierać wszystkie kluczowe pola 
    def test_history_record_contains_required_fields(self, db):
        db.save_weather(_make_weather_data())
        record = db.get_history("Warsaw", days=30)[0]
        required = {
            "city", "country", "temperature", "feels_like",
            "humidity", "pressure", "wind_speed", "weather_time",
        }
        for field_name in required:
            assert field_name in record, f"Brakuje pola: {field_name}"

    #  _save_record: dwa zapisy tych samych danych nie tworzą duplikatu — istniejący rekord jest nadpisywany zamiast dodawania nowego wiersza
    def test_deduplication_same_timestamp(self, db):
        wd = _make_weather_data()
        db.save_weather(wd)
        count_after_first = db.get_total_records()
        db.save_weather(wd)  # drugi identyczny zapis
        assert db.get_total_records() == count_after_first

    # get_total_records() zlicza rekordy ze wszystkich miast łącznie
    def test_get_total_records_counts_all_cities(self, db):
        db.save_weather(_make_weather_data("Warsaw"))
        db.save_weather(_make_weather_data("Kraków"))
        assert db.get_total_records() > 0


# ------ ForecastDataAnalyzer — tryb WeatherData (prognoza) ------ 

class TestForecastDataAnalyzerFromData:
    # time_col = 'timestamp', city jest ustawione na podstawie WeatherData

    # wywołanie bez żadnego argumentu powinno rzucić AttributeError
    def test_raises_when_no_arguments(self):
        with pytest.raises(AttributeError):
            ForecastDataAnalyzer()

    # po inicjalizacji z WeatherData pole city powinno być ustawione
    def test_city_is_set(self, analyzer_from_data):
        assert analyzer_from_data.city == "Warsaw"

    # w trybie WeatherData kolumna czasu nosi nazwę 'timestamp'
    def test_time_col_is_timestamp(self, analyzer_from_data):
        assert analyzer_from_data.time_col == "timestamp"

    # po resamplingu DataFrame powinien mieć kolumnę 'timestamp'
    def test_weather_points_has_timestamp_column(self, analyzer_from_data):
        assert "timestamp" in analyzer_from_data.weather_points.columns

    # DataFrame powinien zawierać wszystkie kolumny danych pogodowych
    def test_weather_points_has_required_columns(self, analyzer_from_data):
        required = {"temperature", "feels_like", "humidity", "pressure", "wind_speed"}
        assert required.issubset(set(analyzer_from_data.weather_points.columns))

    # calculate_forecasted_stats() powinno zwrócić obiekt DataFrame, nie None
    def test_stats_returns_dataframe(self, analyzer_from_data):
        from pandas import DataFrame
        assert isinstance(analyzer_from_data.calculate_forecasted_stats(), DataFrame)

    # kolumny statystyk powinny zawierać 'temperature_*' (min, max, mean, std)
    def test_stats_has_temperature_columns(self, analyzer_from_data):
        cols = list(analyzer_from_data.calculate_forecasted_stats().columns)
        assert any("temperature" in c for c in cols)

    # agregaty min, max i mean muszą być obecne — weryfikuje konfigurację groupby().agg()
    def test_stats_has_min_max_mean(self, analyzer_from_data):
        cols = list(analyzer_from_data.calculate_forecasted_stats().columns)
        assert any("min" in c for c in cols)
        assert any("max" in c for c in cols)
        assert any("mean" in c for c in cols)

    # calculate_temperature_plot() zwraca krotkę (Figure, Axes) — sprawdzamy typy
    def test_temperature_plot_returns_figure_and_axes(self, analyzer_from_data):
        from matplotlib.figure import Figure
        from matplotlib.axes import Axes
        fig, ax = analyzer_from_data.calculate_temperature_plot()
        assert isinstance(fig, Figure)
        assert isinstance(ax, Axes)

    # wykres temperatury rysuje dwie linie: rzeczywistą i odczuwalną — ax.get_lines() powinno zwrócić co najmniej 2 elementy
    def test_temperature_plot_has_two_lines(self, analyzer_from_data):
        _, ax = analyzer_from_data.calculate_temperature_plot()
        assert len(ax.get_lines()) >= 2

    # każdy wykres powinien zwracać obiekt Figure
    def test_humidity_plot_returns_figure(self, analyzer_from_data):
        from matplotlib.figure import Figure
        fig, _ = analyzer_from_data.calculate_humidity_plot()
        assert isinstance(fig, Figure)

    def test_pressure_plot_returns_figure(self, analyzer_from_data):
        from matplotlib.figure import Figure
        fig, _ = analyzer_from_data.calculate_pressure_plot()
        assert isinstance(fig, Figure)

    def test_wind_speed_plot_returns_figure(self, analyzer_from_data):
        from matplotlib.figure import Figure
        fig, _ = analyzer_from_data.calculate_wind_speed_plot()
        assert isinstance(fig, Figure)


# ------ ForecastDataAnalyzer — tryb DataFrame (dane historyczne z BD) ------ 

class TestForecastDataAnalyzerFromDataFrame:
    # time_col = 'weather_time', city = None bo dane nie pochodzą z API

    # w trybie DataFrame self.city powinno być None
    def test_city_is_none(self, analyzer_from_df):
        assert analyzer_from_df.city is None

    # w trybie DataFrame kolumna czasu nosi nazwę 'weather_time' (jak w BD)
    def test_time_col_is_weather_time(self, analyzer_from_df):
        assert analyzer_from_df.time_col == "weather_time"

    # po resamplingu DataFrame powinien mieć kolumnę 'weather_time'
    def test_weather_points_has_weather_time_column(self, analyzer_from_df):
        assert "weather_time" in analyzer_from_df.weather_points.columns

    # statystyki powinny działać tak samo jak w trybie WeatherData
    def test_stats_returns_dataframe(self, analyzer_from_df):
        from pandas import DataFrame
        assert isinstance(analyzer_from_df.calculate_forecasted_stats(), DataFrame)

    # wykresy powinny działać w obu trybach — WeatherData i DataFrame
    def test_temperature_plot_works(self, analyzer_from_df):
        from matplotlib.figure import Figure
        fig, _ = analyzer_from_df.calculate_temperature_plot()
        assert isinstance(fig, Figure)

    def test_humidity_plot_works(self, analyzer_from_df):
        from matplotlib.figure import Figure
        fig, _ = analyzer_from_df.calculate_humidity_plot()
        assert isinstance(fig, Figure)


# T------ DBDataProcessor ------ 

class TestDBDataProcessor:

    @pytest.fixture
    # DBDataProcessor z bazą zawierającą Warsaw i Kraków z fixture db_with_data
    def processor(self, db_with_data) -> DBDataProcessor:
        return DBDataProcessor(db_with_data, METRIC)

    # po zapisaniu danych lista miast nie powinna być pusta
    def test_cities_not_empty_after_save(self, processor):
        assert len(processor.cities) > 0

    # Warsaw powinno być na liście zapisanych miast
    def test_cities_contains_warsaw(self, processor):
        city_names = [c["city"] for c in processor.cities]
        assert "Warsaw" in city_names

    # łączna liczba rekordów powinna być większa od zera
    def test_total_records_positive(self, processor):
        assert processor.total_records > 0

    # select_records() zwraca krotkę dwóch DataFrame: (surowy df, df do wyświetlenia)
    def test_select_records_returns_tuple(self, processor):
        result = processor.select_records("Warsaw", days=30)
        assert isinstance(result, tuple)
        assert len(result) == 2

    # display_df ma polskie nazwy kolumn z jednostką z METRIC, np. "Temp (°C)"
    def test_display_df_has_celsius_in_column_name(self, processor):
        _, display_df = processor.select_records("Warsaw", days=30)
        assert any("°C" in col for col in display_df.columns)

    # surowy df (pierwszy element) zachowuje oryginalną kolumnę 'temperature' (potrzebną przez ForecastDataAnalyzer do generowania wykresów)
    def test_raw_df_has_temperature_column(self, processor):
        raw_df, _ = processor.select_records("Warsaw", days=30)
        assert "temperature" in raw_df.columns

    # z jednostkami imperialnymi (IMPERIAL)
    def test_imperial_units_in_column_names(self, db_with_data):
        processor = DBDataProcessor(db_with_data, IMPERIAL)
        _, display_df = processor.select_records("Warsaw", days=30)
        assert any("°F" in col for col in display_df.columns)

    # dla pustej bazy lista miast powinna być pustą listą []
    def test_empty_db_has_empty_cities(self, db):
        assert DBDataProcessor(db, METRIC).cities == []

    # dla pustej bazy total_records powinno wynosić 0
    def test_empty_db_has_zero_records(self, db):
        assert DBDataProcessor(db, METRIC).total_records == 0