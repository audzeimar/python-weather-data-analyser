# obraz bazowy
FROM python:3.11-slim 

# Katalog roboczy wewnątrz kontenera, kolejne komendy wykonują się w /app
WORKDIR /app

# Kopiujemy NAJPIERW tylko requirements.txt, jeśli  się nie zmienił, nie reinstaluje paczek przy każdym buildzie
COPY requirements.txt .

# Instalujemy zależności, nie zapisujemy cache pip 
RUN pip install --no-cache-dir -r requirements.txt

# Kopiujemy resztę kodu 
COPY . .

# Tworzymy folder na BD i ustawienia
RUN mkdir -p /app/data

# Informacja dla Dockera 0 porcie 8501
EXPOSE 8501

# Sprawdzenie czy aplikacja żyje (co 30s)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Komenda uruchamiająca aplikację
CMD ["python", "-m", "streamlit", "run", "Application.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]