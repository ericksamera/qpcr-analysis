import streamlit as st
import pandas as pd
from ddct_pipeline.converters import df_to_rows
from ddct_pipeline.processor import process_ddct
from ddct_pipeline.types import GroupingVariable
from interface.components.excel_dialog import show_excel_import_dialog

# --- Dialogs ---
@st.dialog("Add Grouping Variable")
def manual_grouping_dialog():
    with st.form("grouping_form"):
        group_name = st.text_input("Grouping Variable Name", placeholder="e.g., Sex")
        values_str = st.text_area("Values (one line each)", placeholder="e.g.,\nmale\nfemale")
        if st.form_submit_button("Add Grouping"):
            if not group_name or not values_str:
                st.warning("Both name and values are required.")
                return

            values = [v.strip() for v in values_str.splitlines() if v.strip()]
            if group_name != "Samples":
                values = ["N/A"] + [v for v in values if v != "N/A"]

            new_row = {"Grouping Name": group_name, "Values": values, "Delete?": False}
            df = st.session_state.get("custom_group_df", pd.DataFrame(columns=["Delete?", "Grouping Name", "Values"]))
            updated_df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            st.session_state["custom_group_df"] = updated_df
            st.rerun()

# --- Step 1: Upload + Genes ---
def step_upload_and_genes():
    if st.button("Upload Files", use_container_width=True):
        show_excel_import_dialog()
        return False

    df = st.session_state.get("ct_data_df")
    if df is None or df.empty:
        st.info("No Ct data loaded.")
        return False

    genes = sorted(df["Gene"].unique())
    st.session_state.setdefault("experiment_config", {})
    st.session_state["experiment_config"]["genes"] = genes

    sample_count = df["Sample ID"].nunique()
    st.success(f"Detected {len(genes)} unique genes and {sample_count} samples.")
    return True

# --- Step 2: Grouping Variables ---
def step_grouping_variables():
    st.button("Add Variable", icon=":material/add_circle_outline:", on_click=manual_grouping_dialog, use_container_width=True)

    df = st.session_state.get("custom_group_df", pd.DataFrame(columns=["Delete?", "Grouping Name", "Values"]))
    ct_df = st.session_state.get("ct_data_df")

    if ct_df is not None and not ct_df.empty:
        sample_ids = sorted(ct_df["Sample ID"].unique())
        sample_row = {"Grouping Name": "Samples", "Values": sample_ids, "Delete?": False}
        if not (df["Grouping Name"] == "Samples").any():
            df = pd.concat([pd.DataFrame([sample_row]), df], ignore_index=True)

    if "Delete?" not in df.columns:
        df["Delete?"] = False

    df = df[["Delete?", "Grouping Name", "Values"]]
    edited_df = st.data_editor(
        df,
        column_config={
            "Delete?": st.column_config.CheckboxColumn("Delete"),
            "Grouping Name": st.column_config.TextColumn("Variable"),
            "Values": st.column_config.ListColumn("Values"),
        },
        use_container_width=True,
        hide_index=True,
        key="group_editor"
    )

    prev_state = st.session_state.get("prev_checkbox_state", [])
    current_state = edited_df["Delete?"].tolist()
    to_keep = ~edited_df.index.isin(edited_df[edited_df["Delete?"]].index) | (edited_df["Grouping Name"] == "Samples")
    filtered_df = edited_df[to_keep].copy()
    st.session_state["custom_group_df"] = filtered_df
    st.session_state["prev_checkbox_state"] = current_state
    if prev_state != current_state:
        st.rerun()

    if not filtered_df.empty:
        group_vars = []
        group_dict = {}
        for _, row in filtered_df.iterrows():
            name = row["Grouping Name"]
            raw_values = row["Values"]
            values = raw_values if name == "Samples" else (["N/A"] + [v for v in raw_values if v != "N/A"])
            group_vars.append(GroupingVariable(name=name, values=values))
            group_dict[name] = values

        st.session_state["experiment_config"]["grouping_variables"] = group_vars
        st.session_state["experiment_config"]["groups"] = group_dict
        st.session_state["experiment_config"]["reference_grouping"] = group_vars[0].name

# --- Step 3: Reference Genes ---
def step_reference_genes():
    genes = st.session_state["experiment_config"].get("genes", [])
    default_refs = st.session_state["experiment_config"].get("reference_genes", [])
    selected = st.multiselect("Select reference gene(s)", options=genes, default=default_refs)
    st.session_state["experiment_config"]["reference_genes"] = selected

# --- Step 4: Reference Condition ---
def step_reference_condition():
    grouping_names = [g.name for g in st.session_state["experiment_config"].get("grouping_variables", [])]
    if not grouping_names:
        st.warning("Please define at least one grouping variable.")
        return

    ref_grouping = st.selectbox("Select grouping variable for reference", options=grouping_names)
    st.session_state["experiment_config"]["reference_grouping"] = ref_grouping
    possible_values = st.session_state["experiment_config"]["groups"].get(ref_grouping, [])
    ref_cond = st.selectbox("Select reference condition", options=possible_values)
    st.session_state["experiment_config"]["reference_condition"] = ref_cond

# --- Step 5: Assign Metadata ---
def step_assign_metadata():
    df = st.session_state.get("ct_data_df")
    grouping_vars = st.session_state["experiment_config"].get("grouping_variables", [])

    if df is None or df.empty or not grouping_vars:
        return

    sample_genes = df.groupby("Sample ID")["Gene"].unique().apply(list)
    rows = []

    for sample_id, genes in sample_genes.items():
        row = {"Sample ID": sample_id, "Genes": list(genes)}
        for gv in grouping_vars:
            if gv.name == "Samples":
                row[gv.name] = sample_id
            else:
                row[gv.name] = st.session_state.get("sample_metadata", {}).get(sample_id, {}).get(gv.name, "")
        rows.append(row)

    editor_df = pd.DataFrame(rows)

    column_config = {
        "Genes": st.column_config.ListColumn(label="Genes"),
    }
    for gv in grouping_vars:
        if gv.name == "Samples":
            continue
        column_config[gv.name] = st.column_config.SelectboxColumn(label=gv.name, options=gv.values, required=True)

    edited = st.data_editor(
        editor_df,
        use_container_width=True,
        column_config=column_config,
        column_order=["Sample ID", "Genes"] + [g.name for g in grouping_vars if g.name != "Samples"],
        disabled=["Sample ID", "Genes"],
        hide_index=True,
        key="quick_meta_editor"
    )

    if st.button("💾 Save Metadata", use_container_width=True):
        sample_meta = {}
        for _, row in edited.iterrows():
            sid = row["Sample ID"]
            sample_meta[sid] = {gv.name: row[gv.name] for gv in grouping_vars}
        st.session_state["sample_metadata"] = sample_meta
        st.toast("Sample metadata saved!", icon="✅")


# --- Step 6: Run Analysis ---
def step_run_analysis():
    if st.button("Run Analysis", type="primary", use_container_width=True):
        df_copy = st.session_state["ct_data_df"].copy()
        df_copy = df_copy.rename(columns={"Sample ID": "sample_id", "Gene": "gene", "Ct": "ct"})
        df_copy["ct"] = pd.to_numeric(df_copy["ct"], errors="coerce")

        metadata = st.session_state.get("sample_metadata", {})
        for gv in st.session_state["experiment_config"].get("grouping_variables", []):
            df_copy[gv.name] = df_copy["sample_id"].map(lambda sid: metadata.get(sid, {}).get(gv.name, sid if gv.name == "Samples" else None))

        rows = df_to_rows(df_copy)
        result = process_ddct(rows, st.session_state["experiment_config"])
        st.session_state["ddct_results_df"] = result
        st.success("∆∆Ct analysis complete.")
        st.page_link("interface/plot_viewer.py", label="→ Go to Plots", icon="📊", use_container_width=True)


# --- Main Entrypoint ---
def run():
    st.title("Quick Setup Wizard")

    if st.session_state.get("excel_upload_complete"):
        st.session_state.pop("excel_upload_complete")
        st.switch_page("interface/data_import.py")
        return

    col1, col2, col3, col4 = st.columns([2, 3, 2, 2])

    with col1:
        st.subheader("Step 1.")
        st.text("Upload exported Excel file.")
        ct_loaded = step_upload_and_genes()
    if not ct_loaded:
        st.info("Once data is loaded, the next steps will appear.")
        return

    with col2:
        st.subheader("Step 2.")
        st.text("Define variables for grouping samples.")
        step_grouping_variables()

    with col3:
        st.subheader("Step 3.")
        st.text("Define reference gene(s).")
        step_reference_genes()

    with col4:
        st.subheader("Step 4.")
        st.text("Define baseline/reference condition.")
        step_reference_condition()

    st.subheader("Step 5.")
    st.text("Assign Sample Metadata")
    step_assign_metadata()


    # --- Optional: Experiment Summary ---
    config = st.session_state.get("experiment_config", {})
    genes = config.get("genes", [])
    ref_genes = config.get("reference_genes", [])
    grouping_vars = config.get("grouping_variables", [])
    ref_group = config.get("reference_grouping")
    ref_condition = config.get("reference_condition")


    grouping_details = {
        gv.name: gv.values for gv in config.get("grouping_variables", [])
    }
    sample_count = st.session_state["ct_data_df"]["Sample ID"].nunique()


    # --- Validation state ---
    is_ready = all([
        len(genes) >= 2,
        len(ref_genes) >= 1,
        any(g not in ref_genes for g in genes),
        grouping_vars,
        ref_group,
        ref_condition,
        len(config.get("groups", {}).get(ref_group, [])) >= 2
    ])

    if is_ready:
        target_genes = [g for g in genes if g not in ref_genes]
        other_conditions = [v for v in config["groups"].get(ref_group, []) if v != ref_condition]

        ref_gene_str = ", ".join(ref_genes)
        target_gene_str = ", ".join(target_genes)
        sample_count = st.session_state["ct_data_df"]["Sample ID"].nunique()

        grouping_var_sentences = []
        for gv in grouping_vars:
            vals = ", ".join(gv.values)
            grouping_var_sentences.append(f"{gv.name} ({vals})")
        grouping_description = "; ".join(grouping_var_sentences)

        methods_paragraph = (
            f"Gene expression analysis was performed on **{sample_count} samples** across **{len(genes)} targets** "
            f"(**{target_gene_str}**, normalized to **{ref_gene_str}**) using the ΔΔCt method. "
            f"Samples were grouped by **{ref_group}**, with **{ref_condition}** defined as the reference condition "
            f"and comparisons made against other conditions including {', '.join(other_conditions)}.  \n\n"
            f"Experimental grouping variables included: {grouping_description}."
        )

        st.markdown("### Methods Summary")
        st.markdown(methods_paragraph)

        st.subheader("Step 6:")
        st.text("Run ∆∆Ct Analysis (finally).")
        step_run_analysis()
    else:
        st.info("⚠️ You're almost there! The following are required before you can run analysis:")

        missing = []
        if len(genes) < 2:
            missing.append("• At least **2 genes** must be defined.")
        if len(ref_genes) < 1:
            missing.append("• Select at least **1 reference gene**.")
        if all(g in ref_genes for g in genes):
            missing.append("• Add at least **1 non-reference gene**.")
        if not grouping_vars:
            missing.append("• Define at least **1 grouping variable**.")
        if not ref_group:
            missing.append("• Select a **reference grouping variable**.")
        if not ref_condition:
            missing.append("• Choose a **reference condition** for the selected grouping.")
        elif len(config.get("groups", {}).get(ref_group, [])) < 2:
            missing.append("• The selected grouping must have at least **2 conditions**.")

        for item in missing:
            st.markdown(item)

run()
