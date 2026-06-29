# Aplikacja do analizy danych pogodowych

Aplikacja umożliwiająca analizę i odczyt aktualnych danych pogodowych oraz prognozy pogody dla wybranego miasta. Umożliwia również zapisywanie obecnych danych pogodowych i prognozy do lokalnej bazy danych w celu późniejszej analizy historycznej.

Dane pogodowe pobierane są z serwisu [OpenWeatherMap](https://openweathermap.org/)

---

## Struktura projektu

```
├── Application.py          # punkt wejścia — kontroler aplikacji
├── models/
│   ├── weather_model.py    # komunikacja z API, modele danych (dataclassy)
│   └── database_model.py   # warstwa bazy danych 
├── data_processors/
│   ├── forecast_data_analyzer.py  # analiza statystyczna i generowanie wykresów
│   └── DBDataProcessor.py         # przetwarzanie danych z bazy do wyświetlenia
├── ui_classes/
│   ├── MainUI.py           # główny widok, nagłówek, zakładki
│   ├── ForecastUI.py       # zakładka prognozy pogody
│   ├── PlotsUI.py          # zakładka wykresów
│   ├── StatsUI.py          # zakładka statystyk
│   ├── SettingsUI.py       # panel ustawień
│   └── WeatherHistoryUI.py # zakładka historii danych
├── utils/
│   ├── ApplicationState.py   # zarządzanie stanem sesji
│   ├── session_cache.py      # cache wyników z TTL
│   ├── measurement_units.py  # definicje jednostek (metryczne / imperialne)
│   └── ui_helpers.py         # pomocnicze funkcje renderowania wykresów
├── tests/
│   └── test_weather_app.py # testy jednostkowe (pytest)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── start.bat               # skrypt uruchomieniowy dla Windows
```

---

## Insturkcja instalacji
1. Pobierz archiwum z repozytorium i rozpakuj je.
2. Stwórz plik .env zgodnie z szablonem .env.example
3. Otwórz plik `.env` i wpisz swój klucz API OpenWeatherMap:
   ```
   OPEN-WEATHER-MAP-KEY=twój_klucz_tutaj
   ```
   Darmowy klucz uzyskasz po rejestracji na [openweathermap.org](https://openweathermap.org/api).

---

## Instrukcja uruchomienia

Aplikację można uruchomić na dwa sposoby:

### Sposób 1: Docker (zalecany, wymaga instalacji Dockera)
1. Otwórz terminal w folderze z aplikacją
2. Wpisz w terminalu:
   ```
   docker compose up --build
   ```
3. Otwórz przeglądarkę pod adresem **http://localhost:8501**.

### Sposób 2: ręczne uruchomienie (wymaga instalacji pythona i pip)

1. Otwórz terminal w folderze z aplikacją

2. *(Opcjonalnie)* Utwórz środowisko wirtualne i aktywuj je:
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

3. Zainstaluj wymagane biblioteki:
   ```
   pip install -r requirements.txt
   ```

4. Uruchom aplikację:
   **Windows** — uruchom plik `start.bat`, lub w terminalu:
   ```
   python -m streamlit run Application.py
   ```
   **Linux/macOS:**
   ```
   python3 -m streamlit run Application.py
   ```

Aplikacja otwiera się w przeglądarce webowej pod adresem http://localhost:8501. Okno terminala musi pozostać otwarte — jego zamknięcie zatrzymuje aplikację.

---

## Instrukcja obsługi

### Wyszukiwanie danych pogodowych

Po uruchomieniu aplikacji wybierz tryb wyszukiwania:

- **Nazwa Miasta** — wpisz nazwę miasta (np. `Wrocław`, `London`).
- **Kod Pocztowy** — wpisz kod pocztowy i dwuliterowy kod kraju (np. `50-001`, `PL`).

Następnie kliknij przycisk **„Wyszukaj dane pogodowe"**. Wyniki pojawią się w zakładkach poniżej.

---

### Zakładki z danymi

Po wczytaniu danych dostępne są cztery zakładki:

#### Prognoza pogody
Wyświetla aktualną pogodę oraz prognozę dla kolejnych punktów czasowych (co 3 godziny, przez 5 dni). Z listy rozwijanej możesz wybrać konkretny moment i zobaczyć jego parametry: temperaturę, temperaturę odczuwalną, wilgotność, ciśnienie atmosferyczne, prędkość wiatru oraz opis. Dla punktów prognozy wyświetlane jest również prawdopodobieństwo opadów.

#### Wykresy prognozy danych pogodowych
Wykresy zmian parametrów pogodowych w czasie: temperatury (rzeczywistej i odczuwalnej), wilgotności, ciśnienia atmosferycznego oraz prędkości wiatru. Wykresy można przewijać poziomo, jeśli obejmują długi przedział czasowy.

#### Analiza statystyczna prognozowanych danych pogodowych
Statystyki prognozowanych danych pogodowych pogrupowane po dniach. Dostępne są dwa widoki:
- **Podstawowe informacje** — minimalna, maksymalna i średnia temperatura, wilgotność, ciśnienie i prędkość wiatru.
- **Pełne statystyki** — dodatkowo odchylenie standardowe dla wszystkich parametrów.

#### Analiza historycznych danych pogodowych
Przegląd danych zapisanych wcześniej do lokalnej bazy danych. Możesz wybrać miasto oraz zakres ostatnich X dni (suwak 1–90). 

---

### Zapisywanie danych do bazy

Dane pogodowe (aktualne + prognoza) można zapisać do lokalnej bazy danych na dwa sposoby:

- **Ręcznie** — kliknij przycisk **„💾 Zapisz bieżące dane do bazy danych"** widoczny pod zakładkami po wyszukaniu miasta.
- **Automatycznie** — włącz opcję **„Automatycznie zapisuj dane do bazy po każdym wyszukaniu"** w menu ustawień.

Zapisane dane są dostępne w zakładce **Analiza historycznych danych pogodowych**.

---

### Menu ustawień

Menu ustawień znajduje się w prawym górnym rogu ekranu (przycisk **⚙️ Opcje**). Dostępne opcje:

| Opcja | Opis |
|---|---|
| **TTL cache (minuty)** | Czas ważności wyników wyszukiwania w pamięci podręcznej (5–60 min). Po upływie TTL kolejne wyszukanie tego samego miasta pobierze świeże dane z API. |
| **Typ jednostki danych** | Wybór między jednostkami **SI (metryczne)** (°C, m/s) a **imperialnymi** (°F, mph). Zmiana jednostek czyści cache i bazę danych (dane w różnych jednostkach są ze sobą niespójne). |
| **Automatycznie zapisuj dane** | Włącznik auto-zapisu do bazy po każdym wyszukaniu. |
| **Wyczyść cache** | Usuwa tymczasowo zapisane wyniki wyszukiwań z pamięci sesji. |
| **Wyczyść bazę danych** | Usuwa wszystkie rekordy z lokalnej bazy historycznej (operacja nieodwracalna). |
| **💾 Zapisz ustawienia** | Zapisuje bieżące ustawienia (TTL, jednostki, auto-zapis) do pliku konfiguracyjnego — będą aktywne przy kolejnym uruchomieniu. |

---

## Testy jednostkowe

### Uruchamianie testów jednostkowych

Projekt zawiera 77 testów jednostkowych pokrywających komunikację z API, cache, bazę danych oraz analizę danych.

```
python -m pytest tests/ -v
```


