# interface/backend/session.py

import streamlit as st

def initialize_session_state():
    defaults = {
        "experiment_config": {
            "genes": [],
            "reference_genes": [],
            "grouping_variables": [],
            "reference_grouping": "",
            "reference_condition": "",
            "groups": {}
        },
        "grouping_variables": [],
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
