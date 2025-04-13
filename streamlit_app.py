import streamlit as st

from interface.backend.session import initialize_session_state

st.set_page_config(page_title="ΔΔCt Calculator", layout="wide")

__VERSION__="1.0.0"
__COMMENT__="works?"

from interface.backend.session_io import (
    session_export_button,
    session_import_button,
    session_restart_button
)

def main():
    initialize_session_state()

    custom_pages = {"Analysis Tools": [], "Manual Analysis Tools": []}

    custom_pages["Analysis Tools"].append(
        st.Page("interface/home.py", title="Home", icon=":material/info:")
    )

    custom_pages["Analysis Tools"].append(
        st.Page("interface/quick_wizard.py", title="Quick Setup", icon=":material/bolt:")
    )

    custom_pages["Analysis Tools"].append(
        st.Page("interface/plot_viewer.py", title="Plotting", icon=":material/file_present:")
    )

    custom_pages["Manual Analysis Tools"].append(
        st.Page("interface/data_import.py", title="Excel Import", icon=":material/file_present:")
    )

    custom_pages["Manual Analysis Tools"].append(
        st.Page("interface/setup_experiment.py", title="Experiment Setup", icon=":material/file_present:")
    )

    custom_pages["Manual Analysis Tools"].append(
        st.Page("interface/data_entry.py", title="Data Entry", icon=":material/file_present:")
    )



    page = st.navigation(custom_pages)
    page.run()

    st.divider()

    with st.sidebar:
        st.caption("Session Options")
        col_import, col_export, col_del = st.columns([3, 3, 1])

        with col_import:
            session_import_button()

        with col_export:
            session_export_button()

        with col_del:
            session_restart_button()

    st.divider()
    st.caption(f"[qpcr-analysis v {__VERSION__}{': ' + __COMMENT__ if __COMMENT__ else ''}](https://github.com/ericksamera/fla-analysis) | Developed by Erick Samera ([@ericksamera](https://github.com/ericksamera))")

if __name__ == "__main__":
    main()