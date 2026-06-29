from matplotlib.figure import Figure
from matplotlib.axes import Axes
import streamlit as st
from utils.ui_helpers import render_plots

class PlotsUI:
    @staticmethod
    def render(plots:dict[str,tuple[Figure, Axes]]):
        st.header("Wykresy prognozy danych pogodowych")
        render_plots(plots)
