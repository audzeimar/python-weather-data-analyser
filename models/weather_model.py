from __future__ import annotations

import datetime
from typing import Any
from dataclasses import dataclass, field

import requests

# -------- dataclasy - czyli niezmienne struktury danych --------

@dataclass(frozen=True)
class CurrentWeather: #niezmienny model danych dla aktualnej pogody
    city: str
    country: str
    lat: float  # szerokość geograficzna
    lon: float  # długość geograficzna
    temperature: float
    feels_like: float
    humidity: int   # wilgotność
    pressure: int
    wind_speed: float
    wind_deg: int # kierunek wiatru w stopniach
    description: str
    icon_code: str
    sunrise: datetime.datetime
    sunset: datetime.datetime
    timestamp: datetime.datetime  # czas aktualizacji danych

@dataclass(frozen=True)
class ForecastPoint: # Niezmienny model danych pojedynczego punktu w czasie prognozy pogody
    timestamp: datetime.datetime
    temperature: float
    feels_like: float
    humidity: int
    pressure: int
    wind_speed: float
    description: str
    icon_code: str
    pop: float  # prawdopodobieństwo opadów

@dataclass(frozen=True)
class WeatherData: # główny model danych, który zawiera zarówno aktualną pogodę, jak i prognozę
    current: CurrentWeather
    # Lista obiektów ForecastPoint 
    forecast: list[ForecastPoint] = field(default_factory=list) # zapobiega współdzieleniu referencji pustej listy przez instancje


## -------- wyjątki związane z API --------

class WeatherAPIError(Exception):
    """Ogólny błąd komunikacji z API"""


class CityNotFoundError(WeatherAPIError):
    """Miasto nie zostało znalezione (HTTP 404)"""


class UnauthorizedError(WeatherAPIError):
    """Nieprawidłowy klucz API (HTTP 401)"""

# -------- Model Biznesowy --------

# Klasa odpowiedzialna za komunikację z API  oraz parsowanie danych
class WeatherDataModel:

    BASE_URL = "https://api.openweathermap.org/data/2.5"
    TIMEOUT = 10 # maksymalny czas oczekiwania na odpowiedź API w sekundach


    # Inicjuje model API, sprawdza obecność klucza  i konfiguruje sesję HTTP
    def __init__(self, api_key: str, units:str) -> None:
        if not api_key:
            raise ValueError("Klucz API nie może być pusty.")
        self.api_key = api_key 

        # tworzy stałą sesję HTTP, która będzie używana do wszystkich zapytań
        self._session = requests.Session() 


        # dodaje domyślne parametry do sesji, przesyłany w każdym GET tej sesji
        self._session.params = {"appid": self.api_key, "units": units, "lang": "pl"}


    # ----- tryby wyszukiwania ------

    # po nazwie miasta
    def fetch_weather(self, city: str) -> WeatherData:
        city = city.strip()
        if not city:
            raise ValueError("Nazwa miasta nie może być pusta.")  
        
        raw_c = self._get(f"{self.BASE_URL}/weather", {"q": city}) # pobiera aktualną pogodę
        raw_f = self._get(f"{self.BASE_URL}/forecast", {"q": city}) # pobiera prognozę pogody
       
       # parsuje surowe dane i zwraca obiekt WeatherData zawierający aktualną pogodę i prognozę
        return WeatherData(current=self._parse_current(raw_c),
                           forecast=self._parse_forecast(raw_f))

    # po kodzie pocztowym
    def fetch_weather_by_zip(self, zip_code: str, country: str = "PL") -> WeatherData:
        zip_code = zip_code.strip()
        if not zip_code:
            raise ValueError("Kod pocztowy nie może być pusty.")
        
        query = f"{zip_code},{country}" # format: kod_pocztowy,kraj

        raw_c = self._get(f"{self.BASE_URL}/weather", {"zip": query})
        raw_f = self._get(f"{self.BASE_URL}/forecast", {"zip": query})

        return WeatherData(current=self._parse_current(raw_c),
                           forecast=self._parse_forecast(raw_f))

    # po współrzędnych geograficznych
    def fetch_weather_by_coords(self, lat: float, lon: float) -> WeatherData:

        # zaokrągla współrzędne do 4 miejsc po przecinku
        params = {"lat": round(lat, 4), "lon": round(lon, 4)}

        raw_c = self._get(f"{self.BASE_URL}/weather", params)
        raw_f = self._get(f"{self.BASE_URL}/forecast", params)

        return WeatherData(current=self._parse_current(raw_c),
                           forecast=self._parse_forecast(raw_f))
    

    # ----- prywatne metody pomocnicze -----

    # metoda do wykonywania zapytań HTTP GET i obsługi błędów
    def _get(self, url: str, extra: dict[str, Any]) -> dict[str, Any]:

        try:
            resp = self._session.get(url, params=extra, timeout=self.TIMEOUT)

        except requests.exceptions.ConnectionError as exc:
            raise WeatherAPIError("Brak połączenia z internetem.") from exc
        
        except requests.exceptions.Timeout as exc:
            raise WeatherAPIError("Przekroczono czas oczekiwania.") from exc

        # analiza kodów HTTP
        if resp.status_code == 401:
            raise UnauthorizedError("Nieprawidłowy klucz API.")
        if resp.status_code == 404:
            raise CityNotFoundError(f"Nie znaleziono: {extra}")
        
        # inne błędy HTTP
        if not resp.ok:
            raise WeatherAPIError(f"Błąd API: HTTP {resp.status_code}")
        
        # zwraca dane w formie słownika
        return resp.json() 

    @staticmethod
    # metoda do parsowania danych aktualnej pogody z odpowiedzi API w obiekt CurrentWeather
    def _parse_current(data: dict[str, Any]) -> CurrentWeather:

        main = data["main"] # tam gdzie dane napewno muszą być

        # opcjonalne dane, które mogą nie być obecne w odpowiedzi API, dlatego używamy get() z wartościami domyślnymi
        wind = data.get("wind", {})
        sys = data.get("sys", {})
        coord = data.get("coord", {})

        # pobiera pierwszy element z listy "weather"
        desc = data["weather"][0]

        return CurrentWeather( #kompletny obiekt
            city=data["name"],
            country=sys.get("country", ""),
            lat=coord.get("lat", 0.0),
            lon=coord.get("lon", 0.0),
            temperature=main["temp"],
            feels_like=main["feels_like"],
            humidity=main["humidity"],
            pressure=main["pressure"],
            wind_speed=wind.get("speed", 0.0),
            wind_deg=wind.get("deg", 0),
            description=desc["description"].capitalize(),
            icon_code=desc["icon"],
            sunrise=datetime.datetime.fromtimestamp(sys.get("sunrise", 0)),
            sunset=datetime.datetime.fromtimestamp(sys.get("sunset", 0)),
            timestamp=datetime.datetime.fromtimestamp(data["dt"]),
        )

    @staticmethod
    # metoda do parsowania danych prognozy pogody z odpowiedzi API na ForecastPoint
    def _parse_forecast(data: dict[str, Any]) -> list[ForecastPoint]:

        points: list[ForecastPoint] = [] #pusta lista, będzie wypełniana danymi prognozy

        # iteruje po każdym elemencie listy prognozy zwróconej przez API 
        for item in data.get("list", []):
            main = item["main"]
            wind = item.get("wind", {})
            desc = item["weather"][0]

            # dla każdego punktu prognozy tworzy obiekt ForecastPoint i dodaje go na koniec listy
            points.append(ForecastPoint(
                timestamp=datetime.datetime.fromtimestamp(item["dt"]),
                temperature=main["temp"],
                feels_like=main["feels_like"],
                humidity=main["humidity"],
                pressure=main["pressure"],
                wind_speed=wind.get("speed", 0.0),
                description=desc["description"].capitalize(),
                icon_code=desc["icon"],
                pop=item.get("pop", 0.0),
            ))
        return points # zwraca gotową i posortowaną listę punktów prognozy
