from models.weather_model import WeatherData, ForecastPoint, CurrentWeather
import streamlit as st

class ForecastUI:
    def render(self, weather_data:WeatherData, measurement_units:dict[str, str]) -> None:
        st.header("Prognoza pogody")
        weather_points:list[CurrentWeather|ForecastPoint] = []
        weather_labels:list[str] = []

        c:CurrentWeather = weather_data.current
        time_str = c.timestamp.strftime("%Y-%m-%d %H:%M")
        weather_labels.append(f"🕒 [Aktualna] {time_str} — {c.description}")
        weather_points.append(c)

        for p in weather_data.forecast:
            time_str = p.timestamp.strftime("%Y-%m-%d %H:%M")
            weather_labels.append(f"🔮 [Prognoza] {time_str} — {p.description}")
            weather_points.append(p)

        selected_label = st.selectbox("Wybierz punkt czasowy:", weather_labels, key="active_data_inspector_select")
        selected_index = weather_labels.index(selected_label)
        selected_point = weather_points[selected_index]

        self._render_point(selected_point, selected_index != 0, measurement_units)


    @staticmethod
    def _render_point(weather_point: CurrentWeather | ForecastPoint, is_forecast:bool, measurement_units:dict[str, str]) -> None:
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Temperatura", f"{weather_point.temperature} {measurement_units['temperature']}")
            st.metric("Odczuwalna", f"{weather_point.feels_like} {measurement_units['temperature']}")
            if is_forecast:
                st.metric("Prawdopodobieństwo opadów", f"{weather_point.pop * 100:.2f}%")
        with col2:
            st.metric("Wilgotność", f"{weather_point.humidity}%")
            st.metric("Ciśnienie", f"{weather_point.pressure} hPa")
        with col3:
            st.metric("Prędkość wiatru", f"{weather_point.wind_speed} {measurement_units['wind_speed']}")
            st.markdown(f"**Opis synoptyczny:**\n\n_{weather_point.description.capitalize()}_")