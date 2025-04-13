import streamlit as st
import pandas as pd

from interface.components.excel_dialog import show_excel_import_dialog
from ddct_pipeline.converters import parse_excel_ct_file, collapse_replicates
from ddct_pipeline.types import GroupingVariable


def run():
    col_title, col_button = st.columns([8, 1])
    
    with col_title:
        st.title("Excel Ct Data Import")

    # --- Step 1: Upload Excel Files ---
    with col_button:
        if st.button("Import Excel"):
            show_excel_import_dialog()

    uploaded_files = st.session_state.get("uploaded_excel_files", [])
    if not uploaded_files:
        st.info("Use the **Import Excel** button to upload files.")
        return

    all_rows = []

    for file in uploaded_files:
        try:
            df = parse_excel_ct_file(file)
            all_rows.append(df)
            st.success(f"✅ {file.name}: {len(df)} rows parsed.")
        except Exception as e:
            st.error(f"❌ `{file.name}`: {e}")

    if not all_rows:
        return

    combined = pd.concat(all_rows, ignore_index=True)
    df_long = collapse_replicates(combined)

    # --- Step 2: Visual Summary Overview ---
    sample_names = sorted(df_long["Sample ID"].unique())
    gene_names = sorted(df_long["Gene"].unique())
    file_names = sorted(set(df_long["Source File"]))
    with st.expander("📁 Source Files"):
        st.write(file_names)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Sample Names**")
        with st.container(height=100, border=False):
            st.text(
                "Check that your sample names are all processed properly. " \
                "Each sample should have its own sample name. " \
                "But if you have the same sample loaded across multiple runs for some reason, " \
                "make sure that they're the same here.")
        st.dataframe(pd.DataFrame({"Sample ID": sample_names}), use_container_width=True, hide_index=True)

    with col2:
        st.markdown("**Gene Names**")
        with st.container(height=100, border=False):
            st.text(
                "Same here. Check that the same genes across runs" \
                "are referring to the same gene.")
        st.dataframe(pd.DataFrame({"Gene": gene_names}), use_container_width=True, hide_index=True)

    with st.expander("Renaming"):
        unique_samples = sorted(df_long["Sample ID"].unique())
        unique_genes = sorted(df_long["Gene"].unique())

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Rename Samples**")
            for sid in unique_samples:
                new_val = st.text_input(f"Sample: `{sid}`", value=sid, key=f"rename_sample_{sid}")
                if new_val != sid:
                    df_long["Sample ID"] = df_long["Sample ID"].replace(sid, new_val)

        with col2:
            st.markdown("**Rename Genes**")
            for g in unique_genes:
                new_val = st.text_input(f"Gene: `{g}`", value=g, key=f"rename_gene_{g}")
                if new_val != g:
                    df_long["Gene"] = df_long["Gene"].replace(g, new_val)

        # Collapse again if renaming caused duplicates
        df_long = df_long.groupby(["Sample ID", "Gene"], as_index=False).agg({
            "Ct": "mean",
            "Replicates": lambda x: sum(x, []),
            "n": "sum",
            "Original Sample ID": "first",
            "Source File": "first"
        })

    # --- Step 3: Preview Table ---
    st.markdown("### Table Preview")
    st.data_editor(
        df_long[["Sample ID", "Gene", "n", "Ct", "Replicates", "Source File"]],
        column_config={
            "Ct": st.column_config.NumberColumn("Mean Ct", format="%.2f"),
            "Replicates": st.column_config.ListColumn("Ct Replicates"),
            "Source File": st.column_config.TextColumn("Source File")
        },
        use_container_width=True,
        hide_index=True,
        disabled=True
    )

    # --- Step 4: Optional Renaming ---


    # --- Step 5: Finalize + Load ---
    if st.button("Load into Session", type="primary", use_container_width=True):
        df_export = df_long[["Sample ID", "Gene", "Ct"]].copy()
        st.session_state["ct_data_df"] = df_export

        # Inject grouping variable: "Samples"
        sample_ids = sorted(df_export["Sample ID"].unique())
        existing = [g.name for g in st.session_state["experiment_config"].get("grouping_variables", [])]
        if "Sample ID" not in existing:
            st.session_state["experiment_config"]["grouping_variables"].insert(
                0, GroupingVariable(name="Samples", values=sample_ids)
            )

        # Set genes if not already defined
        if not st.session_state["experiment_config"].get("genes"):
            st.session_state["experiment_config"]["genes"] = sorted(df_export["Gene"].unique())

        st.toast("Ct data loaded into session.")
        st.session_state.pop("uploaded_excel_files", None)
        st.switch_page("interface/quick_wizard.py")


run()
