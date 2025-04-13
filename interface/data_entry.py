# interface/data_entry.py

import streamlit as st
import pandas as pd

from ddct_pipeline.processor import process_ddct
from ddct_pipeline.converters import df_to_rows

def run():
    st.title("Assign Sample Metadata")

    df = st.session_state.get("ct_data_df")
    config = st.session_state.get("experiment_config")

    if df is None or df.empty:
        st.warning("No Ct data available. Please import data first.")
        return

    grouping_vars = config.get("grouping_variables", [])
    if not grouping_vars:
        st.info("No grouping variables configured.")
        return

    # Group by sample → list genes per sample
    sample_genes = df.groupby("Sample ID")["Gene"].unique().apply(list)

    rows = []
    for sample_id, genes in sample_genes.items():
        row = {"Sample ID": sample_id, "Genes": ", ".join(genes)}
        # Include placeholders for each grouping variable
        for gv in grouping_vars:
            if gv.name == "Samples":
                row[gv.name] = sample_id  # assign default automatically
            else:
                row[gv.name] = st.session_state.get("sample_metadata", {}).get(sample_id, {}).get(gv.name, "")

        rows.append(row)

    editor_df = pd.DataFrame(rows)

    # --- Column config for grouping variables ---
    column_config = {
        "Genes": st.column_config.Column(disabled=True),
    }
    for gv in grouping_vars:
        if gv.name == "Samples":
            continue  # hide from UI
        column_config[gv.name] = st.column_config.SelectboxColumn(
            label=gv.name,
            options=gv.values,
            required=True
        )


    st.markdown("### Edit grouping metadata per sample")

    edited = st.data_editor(
        editor_df,
        use_container_width=True,
        column_config=column_config,
        column_order=["Sample ID", "Genes"] + [g.name for g in grouping_vars if g.name != "Samples"],
        disabled=["Sample ID", "Genes"],
        hide_index=True
    )

    if st.button("💾 Save Metadata"):
        sample_meta = {}
        for _, row in edited.iterrows():
            sid = row["Sample ID"]
            sample_meta[sid] = {gv.name: row[gv.name] for gv in grouping_vars}
        st.session_state["sample_metadata"] = sample_meta
        st.toast("Sample metadata updated.", icon="✅")



    if st.button("Run ΔΔCt Analysis", type="primary"):
        df = st.session_state.get("ct_data_df").copy()

        # Rename expected fields
        df = df.rename(columns={
            "Sample ID": "sample_id",
            "Gene": "gene",
            "Ct": "ct"
        })

        # Ensure 'ct' is numeric
        df["ct"] = pd.to_numeric(df["ct"], errors="coerce")

        # Merge in sample metadata if available
        metadata = st.session_state.get("sample_metadata", {})
        for gv in grouping_vars:
            df[gv.name] = df["sample_id"].map(lambda sid: metadata.get(sid, {}).get(gv.name, None))

        rows = df_to_rows(df)
        result_df = process_ddct(rows, st.session_state["experiment_config"])
        st.session_state["ddct_results_df"] = result_df
        st.success("ΔΔCt results computed.")



run()
