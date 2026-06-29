from typing import Any

import streamlit as st
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from pandas import DataFrame

from data_processors.forecast_data_analyzer import ForecastDataAnalyzer
from models.database_model import WeatherDatabase
from models.weather_model import WeatherData
from ui_classes.ForecastUI import ForecastUI
from ui_classes.PlotsUI import PlotsUI
from ui_classes.SettingsUI import SettingsUI
from ui_classes.StatsUI import StatsUI
from ui_classes.WeatherHistoryUI import WeatherHistoryUI


class MainUI:
    def __init__(self, units:dict[str,str]) -> None:
        st.set_page_config(page_title="Aplikacja do analizy danych pogodowych", page_icon="🌤️", layout="wide")

        self._inject_css()
        self.forecast_analyzer:ForecastDataAnalyzer|None = None
        self.stats_tab:StatsUI = StatsUI()
        self.plots_tab:PlotsUI = PlotsUI()
        self.settings_popover:SettingsUI = SettingsUI()
        self.forecast_tab:ForecastUI = ForecastUI()
        self.history_section:WeatherHistoryUI = WeatherHistoryUI()
        self.measurement_units:dict[str, str] = units

    @staticmethod
    # css strony
    def _inject_css() -> None:
        st.markdown("""
        <style>
        [data-testid="metric-container"] {
            background-color: #1E2130;
            border: 1px solid #313244;
            border-radius: 12px;
            padding: 14px 18px;
        }
        [data-testid="stMetricValue"] { color: #4FACFE !important; }
        .stButton > button {
            background: linear-gradient(135deg, #4FACFE, #00F2FE);
            color: #0E1117 !important;
            border: none;
            border-radius: 8px;
            font-weight: 700;
        }
        .stTabs [aria-selected="true"] {
            color: #4FACFE !important;
            border-bottom: 2px solid #4FACFE !important;
        }
        </style>
        """, unsafe_allow_html=True)

    @staticmethod
    def render_input_section() -> tuple[str, str, str|None]:
        search_option:str = st.radio("Wybierz opcję wyszukiwania danych:", ["Nazwa Miasta", "Kod Pocztowy"], horizontal=True)
        label:str = "Podaj nazwę miasta:" if search_option == "Nazwa Miasta" else " Podaj kod pocztowy:"
        search_val:str = st.text_input(label)
        if search_option == "Kod Pocztowy":
            country_val:str|None = st.text_input("Podaj kod kraju:")
        else:
            country_val = None
        return search_option, search_val, country_val

    def render_tabs(self, stats:DataFrame, plots:dict[str, tuple[Figure, Axes]], weather_data:WeatherData, display_df:DataFrame|None,
                    plots_db:dict[str, tuple[Figure, Axes]]|None, cities:list[dict[str, Any]], total_records:int) -> None:
        plots_tab_handler:str
        stats_tab_handler:str
        forecast_tab_handler:str
        history_tab_handler:str

         
        c = weather_data.current
        st.markdown(
            f"📍 **{c.city}, {c.country}** &nbsp;·&nbsp; "
            f"🕒 {c.timestamp.strftime('%d.%m.%Y %H:%M')} &nbsp;·&nbsp; "
            f"{c.description.capitalize()}",
            unsafe_allow_html=True,
        )

        (forecast_tab_handler, plots_tab_handler,
         stats_tab_handler, history_tab_handler) = st.tabs(["Prognoza pogody","Wykresy prognozy danych pogodowych",
                                                            "Analiza statystyczna prognozownych danych pogodowych",
                                                            "Analiza historycznych danych pogodowych"])

        with forecast_tab_handler:
            self.forecast_tab.render(weather_data, self.measurement_units)
        with plots_tab_handler:
            self.plots_tab.render(plots)
        with stats_tab_handler:
            self.stats_tab.render(stats)
        with history_tab_handler:
            self.history_section.render(display_df, plots_db, cities, total_records)

    #przycisk ręcznego zapisu do BD
    def render_db_save_button(self):
        st.divider()
        button_pressed:bool = st.button("💾 Zapisz bieżące dane do bazy danych")
        return button_pressed

    @staticmethod
    def render_error(error:str) -> None:
        st.error(error)

    @staticmethod
    def render_search_button():
        return st.button("Wyszukaj dane pogodowe")

    @staticmethod
    def render_success_toast(message:str, icon:str|None = None) -> None:
        st.success(message, icon=icon)

    def render_header_and_settings(self, ttl: int, units: str, db_auto_save: bool) -> dict[str, Any]:
        # tytuł po lewej, przycisk po prawej
        col_title, col_btn = st.columns([0.88, 0.12])

        with col_title:
            st.markdown("""
            <div style="background:linear-gradient(135deg,#1E2130,#2D3250);
                        border-radius:14px;padding:14px 24px;border:1px solid #313244;">
                <h1 style="color:#4FACFE;margin:0;font-size:1.75rem;">
                    🌤️ Analiza Danych Pogodowych
                </h1>
                <p style="color:#A6ADC8;margin:4px 0 0;font-size:0.85rem;">
                    Prognoza i analiza statystyczna · OpenWeatherMap API
                </p>
            </div>
            """, unsafe_allow_html=True)

        with col_btn:
            # padding żeby przycisk był wycentrowany pionowo względem karty
            st.markdown("<div style='padding-top:22px'></div>", unsafe_allow_html=True)
            settings = self.settings_popover.render(ttl, units, db_auto_save)

        return settings

    @staticmethod
    def rerun():
        st.rerun()

    def set_measurement_units(self, units:dict[str, str]) -> None:
        self.measurement_units = units

