# interface/home.py

import streamlit as st

def run():
    st.header("Welcome to the ΔΔCt Expression App")
    st.text("(or whatever i decide to call it)")

    st.markdown(
        """
        This app helps you calculate and visualize **gene expression** using the **ΔΔCt method**.

        **Key Features:**
        - Upload long-form Ct data (e.g., straight from the QuantStudio's exporting software)
        - Set up genes, reference conditions, and grouping variables
        - Compute ΔCt, ΔΔCt, and Fold Change with replicates handled properly
        - Visualize expression changes with interactive bar/box plots
        - Export results or session state for reuse

        **Next step:** Go to the **Quick Setup** page to begin your analysis.
        """
    )

run()
