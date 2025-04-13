# interface/components/excel_dialog.py

import streamlit as st
import pandas as pd
import numpy as np

@st.dialog("Import Ct Excel Files", width="large")
def show_excel_import_dialog():
    uploaded = st.file_uploader(
        "Upload exported Excel files (.xls/.xlsx)",
        type=["xls", "xlsx"],
        accept_multiple_files=True,
    )

    if uploaded:
        st.session_state["uploaded_excel_files"] = uploaded
        st.success(f"{len(uploaded)} file(s) stored for import.")

    if st.button("Confirm upload"):
        st.session_state["excel_upload_complete"] = True
        st.rerun()
