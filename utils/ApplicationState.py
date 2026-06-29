import streamlit as st

class ApplicationState:
    @staticmethod
    def get(key, default=None):
        return st.session_state.get(key, default)
    @staticmethod
    def set(key, value):
        st.session_state[key] = value