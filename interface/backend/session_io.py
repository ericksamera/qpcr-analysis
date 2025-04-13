# interface/backend/session_io.py

import json
import streamlit as st
from typing import Any, Dict
from ddct_pipeline.types import CtRow, GroupingVariable
from ddct_pipeline.converters import rows_to_df, df_to_rows

from interface.backend.session_schema import ExperimentConfig

# --- Core Session State Keys ---
STATE_KEYS = {
    "experiment_config",
    "grouping_variables",
    "ct_data_df",
    "ddct_results_df"
}

def serialize_session() -> Dict[str, Any]:
    """Convert session state to a JSON-safe dict."""
    config = st.session_state.get("experiment_config", {})
    grouping_vars = [
        gv.__dict__ if isinstance(gv, GroupingVariable) else gv
        for gv in config.get("grouping_variables", [])
    ]
    config["grouping_variables"] = grouping_vars

    session = {
        "experiment_config": config,
        "ct_rows": [r.__dict__ for r in df_to_rows(st.session_state.get("ct_data_df", rows_to_df([])))],
    }
    return session


def deserialize_session(data: Dict[str, Any]):
    """Restore session state from a previously exported session dict."""


    config: ExperimentConfig = data.get("experiment_config", {})

    if "grouping_variables" in config:
        config["grouping_variables"] = [
            GroupingVariable(**gv) if isinstance(gv, dict) else gv
            for gv in config["grouping_variables"]
        ]
    st.session_state["experiment_config"] = config

    ct_rows = [CtRow(**r) for r in data.get("ct_rows", [])]
    st.session_state["ct_data_df"] = rows_to_df(ct_rows)
    st.toast("Session imported.", icon="📥")
    st.rerun()


def session_export_button():
    if st.button("Export", use_container_width=True):
        session_data = serialize_session()
        st.download_button(
            label="Download JSON",
            data=json.dumps(session_data, indent=2),
            file_name="ddct_session.json",
            mime="application/json",
            use_container_width=True
        )


@st.dialog("Import Session")
def session_import_dialog():
    uploaded = st.file_uploader("Upload session JSON", type="json")
    if uploaded:
        try:
            data = json.load(uploaded)
            deserialize_session(data)
        except Exception as e:
            st.error(f"Failed to load session: {e}")


def session_import_button():
    if st.button("Import", use_container_width=True):
        session_import_dialog()


@st.dialog("Restart Session")
def session_restart_dialog():
    st.error("This will clear all session data.")
    if st.button("Confirm Reset", type="primary"):
        st.session_state.clear()
        st.rerun()


def session_restart_button():
    if st.button("", type='primary', icon=":material/restart_alt:", use_container_width=True):
        session_restart_dialog()
