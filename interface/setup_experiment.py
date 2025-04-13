# interface/setup_experiment.py

import streamlit as st
from ddct_pipeline.types import GroupingVariable
from interface.components.excel_dialog import show_excel_import_dialog

from interface.backend.session_schema import ExperimentConfig

# --- DIALOGS ---

@st.dialog("Add target gene")
def add_named_gene_modal():
    new_name = st.text_input("Gene name", placeholder="e.g. β-actin")
    if st.button("Add"):
        st.session_state.experiment_config["genes"].append(new_name)
        st.rerun()

@st.dialog("Add grouping variable")
def add_named_variable_modal():

    new_name = st.text_input("Variable name", placeholder="e.g. condition, tissue")
    if st.button("Add"):
        st.session_state.experiment_config["grouping_variables"].append(GroupingVariable(name=new_name, values=["N/A",]))
        st.rerun()

@st.dialog("Reset all config?", width="small")
def clear_all_config_dialog():
    st.error("This cannot be undone.")
    if st.button("Confirm Reset", use_container_width=True):
        st.session_state.experiment_config = {
            "genes": [],
            "reference_genes": [],
            "grouping_variables": [],
            "reference_condition": "",
            "groups": {}
        }
        st.rerun()

# --- HELPERS ---

def add_value_to_group(index: int):
    key = f"new_value_{index}"
    value = st.session_state.get(key, "").strip()
    if not value:
        return
    group_var = st.session_state.experiment_config["grouping_variables"][index]
    if value not in group_var.values:
        group_var.values.append(value)
    st.session_state.experiment_config["groups"][group_var.name] = group_var.values
    st.session_state[key] = ""

def render_grouping_variable(var: GroupingVariable, index: int):
    with st.expander(f"{var.name}", expanded=True):
        col_add, col_del = st.columns([8, 2])

        with col_add:
            st.text_input(
                label="Add category",
                key=f"new_value_{index}",
                placeholder="e.g. Treated, Control",
                label_visibility="collapsed",
                on_change=lambda i=index: add_value_to_group(i)
            )

        with col_del:
            if st.button("", icon=":material/clear:", key=f"del_group_{index}", type="primary", use_container_width=True):
                del st.session_state.experiment_config["grouping_variables"][index]
                st.rerun()

        selected = st.pills("Values", options=var.values, selection_mode="single", key=f"sel_{index}")
        if selected:
            var.values.remove(selected)
            st.session_state.experiment_config["groups"][var.name] = var.values
            st.rerun()

def run():
    st.title("Experiment Setup")

    config: ExperimentConfig = st.session_state.experiment_config



    col1, col2 = st.columns(2)

    # --- Gene Targets ---
    with col1:
        st.subheader("qPCR Target Genes")
        for i, gene in enumerate(config["genes"]):
            cols = st.columns([6, 1])
            cols[0].text_input(f"Gene {i+1}", value=gene, key=f"gene_{i}", disabled=True, label_visibility="collapsed")
            if cols[1].button("", icon=":material/delete:", key=f"del_gene_{i}", use_container_width=True):
                config["genes"].pop(i)
                if gene in config.get("reference_genes", []):
                    config["reference_genes"].remove(gene)
                st.rerun()

        st.button("Add Gene", icon=":material/add_circle_outline:", on_click=add_named_gene_modal)

    # --- Grouping Variables ---
    with col2:
        st.subheader("Experimental Variables")
        for i, var in enumerate(config["grouping_variables"]):
            render_grouping_variable(var, i)

        st.button("Add Grouping Variable", icon=":material/add_circle_outline:", on_click=add_named_variable_modal)

    # --- Reference Genes & Condition ---
    st.divider()

    st.subheader("Reference gene and reference condition")
    col_ref_genes, col_ref_condition = st.columns(2)

    with col_ref_genes:
        config["reference_genes"] = st.multiselect(
            "Reference Genes",
            options=config["genes"],
            default=config.get("reference_genes", [])
        )

    with col_ref_condition:
        if config["grouping_variables"]:

            grouping_names = ["Sample ID"] + [g.name for g in config["grouping_variables"]]

            # Ensure reference_grouping is initialized
            if not config.get("reference_grouping") and grouping_names:
                config["reference_grouping"] = grouping_names[0]

            config["reference_grouping"] = st.selectbox(
                "Grouping variable to normalize against",
                options=grouping_names,
                index=grouping_names.index(config["reference_grouping"]) if config["reference_grouping"] in grouping_names else 0
            )

            reference_grouping = config.get("reference_grouping")
            selected_group = next(
                (g for g in config["grouping_variables"] if g.name == reference_grouping),
                None
            )

            if reference_grouping == "Sample ID":
                df = st.session_state.get("ct_data_df")
                if df is not None and not df.empty:
                    sample_ids = sorted(df["Sample ID"].unique().tolist())
                    config["reference_condition"] = st.selectbox(
                        "Reference Sample",
                        options=sample_ids,
                        index=sample_ids.index(config["reference_condition"])
                        if config["reference_condition"] in sample_ids else 0
                    )
                else:
                    st.warning("No Ct data available to populate Sample IDs.")
            elif selected_group and selected_group.values:
                group_values = selected_group.values
                config["reference_condition"] = st.selectbox(
                    "Reference condition",
                    options=group_values,
                    index=group_values.index(config["reference_condition"])
                    if config["reference_condition"] in group_values else 0
                )
            else:
                st.warning("Define values for the selected grouping variable.")

                st.warning("Define values for the selected grouping variable.")



    # --- Validation Checklist ---
    with st.expander("Analysis Checklist"):
        genes_ok = len(config["genes"]) >= 2
        refs_ok = len(config.get("reference_genes", [])) >= 1
        ref_not_only = any(g not in config["reference_genes"] for g in config["genes"])
        groupvars_ok = len(config.get("grouping_variables", [])) >= 1

        selected_group = next(
            (g for g in config["grouping_variables"] if g.name == config.get("reference_grouping")), None
        )
        group_vals_ok = selected_group and len(selected_group.values) >= 2

        st.checkbox("At least 2 genes defined", value=genes_ok, disabled=True)
        st.checkbox("At least 1 reference gene selected", value=refs_ok, disabled=True)
        st.checkbox("At least 1 non-reference gene", value=ref_not_only, disabled=True)
        st.checkbox("At least 1 grouping variable", value=groupvars_ok, disabled=True)
        st.checkbox("Selected grouping variable has ≥ 2 values", value=group_vals_ok, disabled=True)

        if all([genes_ok, refs_ok, ref_not_only, groupvars_ok, group_vals_ok]):
            st.success("Setup looks good!")

            # Dynamic summary
            ref_gene_str = ", ".join(config["reference_genes"])
            target_genes = [g for g in config["genes"] if g not in config["reference_genes"]]
            target_gene_str = ", ".join(target_genes)
            group_name = config["reference_grouping"]
            ref_condition = config["reference_condition"]
            other_conditions = [v for v in selected_group.values if v != ref_condition]

            if group_name and ref_condition and other_conditions:
                st.markdown(
                    f"""This experiment compares **{target_gene_str}** expression across **{group_name}** groups  
                    (e.g. {", ".join(other_conditions)}) normalized to **{ref_gene_str}**, using **{ref_condition}** as the reference condition."""
                )
        else:
            st.info("Complete all required items before analysis.")


    #if st.button("Reset All Config", type="primary", use_container_width=True):
    #    clear_all_config_dialog()


run()
