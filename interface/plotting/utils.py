# interface/plotting/utils.py

import streamlit as st
import pandas as pd
from typing import List, Tuple, Union

def render_plot_data_tables(
    df: pd.DataFrame,
    plot_result: Union[List[Tuple], Tuple],
    opts: dict
):
    with st.expander("Show Raw Plot Values"):
        if df is None:
            st.warning("Could not display raw data — no DataFrame provided.")
            return

        # Dynamically detect key columns
        x_label_col = next((c for c in df.columns if c.lower() in {"_x_label", "x_label"}), None)
        y_value_col = next((c for c in df.columns if c.lower() in {"plot_value", "ΔΔct", "fold change", "log₂(fold change)"}), None)

        if x_label_col is None or y_value_col is None:
            st.warning("Required columns for plotting not found (e.g., _x_label, plot_value).")
            return

        if isinstance(plot_result, list):  # Faceted
            for fig, facet_df, label in plot_result:
                _render_facet_table(facet_df, label, opts, x_label_col, y_value_col)
        else:
            fig, summary_df, full_df = plot_result
            _render_facet_table(full_df, "All Data", opts, x_label_col, y_value_col)


def _render_facet_table(
    df: pd.DataFrame,
    label: str,
    opts: dict,
    x_label_col: str,
    y_value_col: str
):
    try:
        sample_col = "sample_id" if "sample_id" in df.columns else "Sample ID"
        group_cols = [opts.get("color_by")] + opts.get("group_by", [])
        group_cols = [c for c in group_cols if c and c in df.columns]

        stats_cols = ["mean", "std", "sem", "count"]
        all_cols = [x_label_col, sample_col, "gene", y_value_col] + stats_cols + group_cols
        cols_to_show = [col for col in dict.fromkeys(all_cols) if col in df.columns]

        df_display = df[cols_to_show].copy().sort_values(by=x_label_col)

        # Rename _x_label to something meaningful
        if x_label_col == "_x_label":
            group_label = opts["group_by"]
            label_str = " + ".join(group_label) if isinstance(group_label, list) else group_label
            df_display = df_display.rename(columns={x_label_col: f"Group: {label_str}"})
        elif x_label_col:
            df_display = df_display.rename(columns={x_label_col: "Group"})

        st.markdown(f"**Facet: `{label}`**")
        if not df_display.empty:
            st.dataframe(df_display, use_container_width=True)
        else:
            st.caption("*(empty)*")

    except Exception as e:
        st.error(f"Error rendering table for facet '{label}': {e}")
