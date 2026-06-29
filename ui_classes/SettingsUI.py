import streamlit as st
from typing import Any 

class SettingsUI:
    @staticmethod
    def render(current_ttl:int,  current_unit: str, current_db_auto_save: bool) -> dict[str, Any]:
        unit_options:list[str] = ["SI (metryczne)", "imperialne"]
        default_unit_idx: int = unit_options.index(current_unit) if current_unit in unit_options else 0
        with st.popover("⚙️ Opcje"):
            st.header("Ustawienia aplikacji")
            cache_cleared:bool = st.button("Wyczyść cache")
            db_cleared:bool = st.button("Wyczyść bazę danych")
            cache_ttl_minutes:int = st.number_input("TTL cache'u (minuty):", value=current_ttl, min_value=5, max_value=60, step=1)
            unit_type:str = st.radio("Typ jednostki danych:", unit_options, index=default_unit_idx)
            
            #opcja auto-zapisu do bazy danych, która będzie zapisywać dane do bazy po każdym wyszukaniu, jeśli jest włączona
            db_auto_save: bool = st.toggle("Automatycznie zapisuj dane do bazy po każdym wyszukaniu", value=current_db_auto_save) 
            saved_settings:bool = st.button("💾 Zapisz ustawienia")

        return {'clear_cache':cache_cleared, 'ttl':cache_ttl_minutes, 'units':unit_type,
                'save_settings':saved_settings, 'db_auto_save':db_auto_save, 'clear_db':db_cleared}
