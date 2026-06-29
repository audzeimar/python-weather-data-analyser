from pandas import DataFrame
import streamlit as st

class StatsUI:
    @staticmethod
    def render(stats:DataFrame) -> None:
        st.header("Analiza statystyczna prognozowanych danych pogodowych")
        with st.expander("Podstawowe informacje"):
            st.dataframe(stats[['temperature_min', 'temperature_max', 'temperature_mean',
                                     'feels_like_min', 'feels_like_max', 'feels_like_mean',
                                     'humidity_mean', 'pressure_mean', 'wind_speed_max']])
        with st.expander("Pełne statystyki"):
            st.dataframe(stats)