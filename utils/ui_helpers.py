import streamlit as st
from matplotlib.axes import Axes
from matplotlib.figure import Figure
import io

def render_plots(plots:dict[str,tuple[Figure, Axes]]) -> None:
    #wyznaczenie liczby pktów na osi X
    try:
        fig_temp:Figure
        ax_temp:Axes
        fig_temp, ax_temp = plots["temperature"]
        num_points:int = len(ax_temp.lines[0].get_xdata())
    except (KeyError, IndexError, AttributeError):
        num_points = 20

    PIXELS_PER_POINT:int = 50
    MIN_WIDTH:int = 750
    DEFAULT_HEIGHT:int = 400

    dynamic_width:int = max(MIN_WIDTH, num_points * PIXELS_PER_POINT)

    with st.expander("🌡️ Wykres temperatury", expanded=True):
        _render_scrollable_plot(plots["temperature"][0], dynamic_width, DEFAULT_HEIGHT)
    with st.expander("💧 Wykres wilgotności", expanded=True):
        _render_scrollable_plot(plots["humidity"][0], dynamic_width, DEFAULT_HEIGHT)
    with st.expander("🌬️ Wykres ciśnienia", expanded=True):        # ← poprawka literówki
        _render_scrollable_plot(plots["pressure"][0], dynamic_width, DEFAULT_HEIGHT)
    with st.expander("💨 Wykres prędkości wiatru", expanded=True):
        _render_scrollable_plot(plots["wind_speed"][0], dynamic_width, DEFAULT_HEIGHT)

def _render_scrollable_plot(fig:Figure, width:int, height:int) -> None:
    st.markdown("""
            <style>
            div[data-testid="stImage"] {
                overflow-x: auto !important;
                max-width: 100% !important;
                border: 1px solid #e6e9ef;
                border-radius: 4px;
                padding: 4px;
                background-color: transparent;
            }
            div[data-testid="stImage"] > img {
                max-width: none !important;
                width: auto !important;
            }
            </style>
        """, unsafe_allow_html=True)

    buf:io.BytesIO = io.BytesIO()
    fig.set_size_inches(width / 100, height / 100)
    fig.tight_layout()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=140)
    buf.seek(0)
    st.image(buf, width=width)
    buf.close()

