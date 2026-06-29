from typing import Any
import streamlit as st
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from pandas import DataFrame

from models.database_model import WeatherDatabase
from utils.ui_helpers import render_plots


class WeatherHistoryUI:
    @staticmethod
    def render(display_df:DataFrame|None, plots:dict[str, tuple[Figure, Axes]]|None, cities:list[dict[str, Any]], total_records:int) -> None:
        """wyświetla sekcję historii zapisanych danych pogodowych dla aktywnego miasta, z możliwością filtrowania po liczbie dni wstecz"""
        st.header("Analiza historycznych danych pogodowych")

        if not cities:
            st.info("Baza danych jest pusta. Wyszukaj miasto i kliknij 'Zapisz'.")
            return

        st.write(f"**Łączna liczba rekordów w bazie:** {total_records}")

        # Mapowanie czystej nazwy miasta (np. 'Warszawa') na pełną etykietę do wyświetlenia
        city_label_map = {
            c["city"]: f"{c['city']}, {c['country']} ({c['records']} rekordów)"
            for c in cities
        }

        # Magia dzieje się tutaj: parametr key="db_selected_city" automatycznie i w odpowiednim momencie 
        # wpisuje wartość (klucz ze słownika, czyli czystą nazwę miasta) do st.session_state.
        selected_city = st.selectbox(
            "Wybierz miasto:",
            options=list(city_label_map.keys()),
            format_func=lambda c: city_label_map[c],
            key="db_selected_city" 
        )
        
        # To samo dotyczy slidera
        days = st.slider("Ostatnie X dni:", min_value=1, max_value=90, value=30, key="db_days")

        with st.expander("🗄️ Historia zapisanych danych"):
            st.dataframe(display_df, use_container_width=True)
              
        if plots is not None:
            with st.expander("Wykresy historycznych danych pogodowych"):
                render_plots(plots)

