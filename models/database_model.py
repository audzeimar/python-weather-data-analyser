import datetime
from pathlib import Path
from typing import Any
from sqlalchemy import create_engine, Integer, String, Float, text, Engine
from sqlalchemy.orm import DeclarativeBase, Session, Mapped, mapped_column
from models.weather_model import WeatherData, CurrentWeather, ForecastPoint

class Base(DeclarativeBase):
    # podstawowa def tabeli bazy danych
    pass

# reprezentuje pojed rekord
class WeatherRecord(Base):
    __tablename__:str = "weather_records"

    id:Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    city:Mapped[str] = mapped_column(String, nullable=False)
    country:Mapped[str] = mapped_column(String, default="")
    lat:Mapped[float] = mapped_column(Float, default=0.0)
    lon:Mapped[float] = mapped_column(Float, default=0.0)
    temperature:Mapped[float] = mapped_column(Float)
    feels_like:Mapped[float] = mapped_column(Float)
    humidity:Mapped[int] = mapped_column(Integer)
    pressure:Mapped[int] = mapped_column(Integer)
    wind_speed:Mapped[float] = mapped_column(Float)
    description:Mapped[str] = mapped_column(String)
    weather_time:Mapped[int] = mapped_column(Integer, nullable=False)  # data i godzina wpisu (unix timestamp)
    data_type:Mapped[str] = mapped_column(String, nullable=False)  # typ wpisu (current lub forecast)

# zarządza BD, wykonuje CRUD
class WeatherDatabase:
    DB_PATH:Path = Path.home() / ".weather_app" / "history.db" #domysl ścieżka

    # inicjalizuje połączenie, tworzy tabele jeśli nie istnieją
    def __init__(self, db_path:Path|None = None) -> None:
        path:Path = db_path or self.DB_PATH
        path.parent.mkdir(parents=True, exist_ok=True)  # tworzy katalog, jeśli nie istnieje

        self._engine:Engine = create_engine(f"sqlite:///{path}", echo=False) #tworzy silnik bazy danych SQLAlchemy
        Base.metadata.create_all(self._engine) # tworzy tabele w bazie danych, jeśli jeszcze nie istnieją

    # zapisuje dane bieżące oraz wszystkie punkty prognozy do bazy danych
    def save_weather (self, weather_data: WeatherData) -> None:
        c:CurrentWeather = weather_data.current # pobranie danych pogody bieżąc
        location_data:dict[str, Any] = {'city':c.city, 'country':c.country, 'lat':c.lat, 'lon':c.lon} 
        self._save_record(c, location_data, False)

        #iteruje po wszytkim punktam prognozy i zapisuje każdy
        for point in weather_data.forecast:
            self._save_record(point, location_data, True)

    # pobiera z BD historyczne wpisy pogodowe dla danego miasta ogranicz filtrem czasu (ostatnie N dni)
    def get_history(self, city:str, days: int = 30) -> list[dict[str, Any]]:
        cutoff:int = int((datetime.datetime.now() - datetime.timedelta(days=days)).timestamp()) # punkt odcięcia

        with Session(self._engine) as session:
            # SELECT
            rows = ( 
                session.query(WeatherRecord)
                .filter(WeatherRecord.city.like(f"%{city}%")) #filtr po nazwie
                .filter(WeatherRecord.weather_time > cutoff) # odzrucanie starszych niż okr czas
                .order_by(WeatherRecord.weather_time.asc()) # sort rosn według daty
                .all()
            )

        # orm na listę słowników
        return [
            {
                "city": r.city,
                "country": r.country,
                "temperature": r.temperature,
                "feels_like": r.feels_like,
                "humidity": r.humidity,
                "pressure": r.pressure,
                "wind_speed": r.wind_speed,
                "description": r.description,
                "weather_time": datetime.datetime.fromtimestamp(r.weather_time).isoformat(), # konwert na ISO
                "data_type": r.data_type
            }
            for r in rows
        ]

    # pobiera listę wszystkich miast, dla których zapisano dane pogodowe, wraz z liczbą rekordów i datą ostatniego zapisu
    def get_all_cities(self) -> list[dict[str, Any]]:
        with Session(self._engine) as session:
            # GROUP BY
            rows = (
                session.query(
                    WeatherRecord.city,
                    WeatherRecord.country,
                    text("COUNT(*) as records"), # liczy wyst rekordów dla każd miasta 
                    text("MAX(weather_time) as last_date") # wyzn najnowszy znacznik czasu 
                )
                .group_by(WeatherRecord.city)
                .order_by(text("last_date DESC"))
                .all()
            )

        return [ # lista krotek na listę słowników
            { "city": r[0], "country": r[1], "records": r[2], "last_date": r[3] }
            for r in rows
        ]

    # zwraca całkowitą liczbę zapisanych rekordów pogodowych w bazie danych
    def get_total_records(self) -> int:
        with Session(self._engine) as session:
            return session.query(WeatherRecord).count()

    # usuwa rekordy pogodowe starsze niż określona liczba dni, zwraca liczbę usuniętych rekordów
    def delete_old_records(self, older_than_days: int = 90) -> int:

        # obl graniczn znacznik czasu
        cutoff:int = int((datetime.datetime.now() - datetime.timedelta(days=older_than_days)).timestamp())
        with Session(self._engine) as session:
            deleted = (
                session.query(WeatherRecord)
                .filter(WeatherRecord.weather_time < cutoff)
                .delete()
            )
            session.commit()
        return deleted

    # Całkowicie czyści zawartość tabeli weather_records
    def clear_database(self):
        with Session(self._engine) as session:
            deleted = (
                session.query(WeatherRecord)
                .delete()
            )
            session.commit()
        return deleted

    # Funkcja pomocnicza do zapisywania/nadpisywania rekordu w bazie
    def _save_record(self, data:CurrentWeather|ForecastPoint, location_data:dict[str, Any], is_forecast:bool):
        weather_time:int = int(data.timestamp.replace(minute=0, second=0, microsecond=0).timestamp()) # normalizacja czasu
        data_type:str = 'forecast' if is_forecast else 'current'

        with Session(self._engine) as session:
            # Sprawdzenie czy istnieje rekord o danej godzinie dla tego samego miasta
            existing_record = session.query(WeatherRecord).filter_by(
                city=location_data['city'],
                weather_time=weather_time
            ).first()

            if existing_record:
                # Jesli istnieje to nadpisujemy forecasty i pomijamy current
                if existing_record.data_type == "current" and data_type == "forecast":
                    return

                # jeśli nie - napdpisujemy wszystko w istn rekordzie
                existing_record.temperature = data.temperature
                existing_record.feels_like = data.feels_like
                existing_record.humidity = data.humidity
                existing_record.pressure = data.pressure
                existing_record.wind_speed = data.wind_speed
                existing_record.description = data.description
                existing_record.data_type = data_type

            else: 
                #tworzenie nowej instancji
                new_record = WeatherRecord(
                    city=location_data['city'],
                    country=location_data['country'],
                    lat=location_data['lat'],
                    lon=location_data['lon'],
                    temperature=data.temperature,
                    feels_like=data.feels_like,
                    humidity=data.humidity,
                    pressure=data.pressure,
                    wind_speed=data.wind_speed,
                    description=data.description,
                    weather_time=weather_time,
                    data_type=data_type,
                )
                session.add(new_record)

            session.commit()