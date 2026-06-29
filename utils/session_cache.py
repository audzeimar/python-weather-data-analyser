from __future__ import annotations

import time
from threading import Lock
from typing import Any

# pojedynczy wpis w pamięci podręcznej
class _Entry:
    __slots__:tuple[str, str] = ("data", "expires_at") # zapobiega tworzeniu wewnętrznego słownika dla każdej instancji (zaoszczędza RAM)

    def __init__(self, data: Any, ttl_seconds: float) -> None:
        self.data:Any = data
        #Obliczenie absolutnego punktu w czasie, w którym ten wpis przestanie być ważny
        self.expires_at:float = time.monotonic() + ttl_seconds

# prosty cache słownikowy z wygasającymi wpisami (TTL)
class SessionCache:

    def __init__(self, ttl_minutes: float = 10.0) -> None:

        self._ttl:float = ttl_minutes * 60 # Przeliczamy minuty na sekundy dla time.monotonic()

        self._store: dict[str, _Entry] = {} # tylko jeden wątek naraz może modyfikować słownik _store
        self._lock:Lock = Lock()


    # Zwraca dane jeśli klucz istnieje i nie wygasł, inaczej None
    def get(self, key: str) -> Any | None:

        # blokujemy dostęp dla innych wątków na czas odczytu i potencjalnego usuwania ze słownika
        with self._lock:
            entry:_Entry = self._store.get(key)
            
            # cache miss - niema żadnego wpisu pod danym kluczem
            if entry is None:
                return None
            
            # Weryfikacja TTL 
            if time.monotonic() > entry.expires_at:
                del self._store[key]  # Usuwamy przestarzały wpis
                return None
            
            # cache hit - dane istn i są aktualne
            return entry.data


    # Zapisuje/nadpisuje dane pod kluczem z aktualnym TTL
    def set(self, key: str, data: Any) -> None:

        # Chronimy zapis przed jednoczesną modyfikacją z innego wątku
        with self._lock:

            # nowa instancja _Entry, sama oblicza swój czas wygaśnięcia
            self._store[key] = _Entry(data, self._ttl)

    # Usuwa konkretny wpis z cache
    def invalidate(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None) # usuwa klucz ze słownika

    # Czyści cały cache
    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    # validacja klucza, czy istnieje i nie wygasł
    def is_valid(self, key: str) -> bool:
        return self.get(key) is not None # automatycznie usuwa klucz, jeśli ten już wygasł

    # Zmienia TTL dla nowych wpisów 
    def set_ttl(self, ttl_minutes: float) -> None:
        self._ttl = ttl_minutes * 60

    @property
    #Liczba wpisów (wliczając te przeterminowane)
    def size(self) -> int:
        with self._lock:
            return len(self._store)

    # --------- metody pomocnicze (stat generatory unik kluczy cache)---------

    @staticmethod
    # klucz dla wyszukiwania po nazwie miasta
    def key_name(city: str) -> str:
        return f"name:{city.lower().strip()}"

    @staticmethod
    # klucz łączący kod pocztowy oraz kod państwa
    def key_zip(zip_code: str, country: str) -> str:
        return f"zip:{zip_code.strip()},{country.lower().strip()}"

    @staticmethod
    # klucz na podstawie współrzędnych geograf
    def key_coords(lat: float, lon: float) -> str:
        # .2f - 2 miejsca po przecinku
        return f"coords:{lat:.2f},{lon:.2f}"