import streamlit as st
import pandas as pd
import numpy as np

import plotly.graph_objects as go
from interface.plotting.plot_ddct import build_ddct_plot
from interface.plotting.utils import render_plot_data_tables

from interface.backend.session_schema import ExperimentConfig

def render_filter(df, label: str, group_name: str):
    if group_name and group_name != "None":
        col_name = _normalize_key(group_name)
        if col_name in df.columns:
            options = sorted(df[col_name].dropna().unique())
            return st.multiselect(
                f"Filter: {label} ({group_name})",
                options=options,
                default=options,
                key=f"filter_{label}_{group_name}"
            )
    return []

def _normalize_key(key: str) -> str:
    return {"Gene": "gene", "Samples": "Samples"}.get(key, key)


def _get_config_options(df: pd.DataFrame, config: dict):
    group_vars = ["Gene"] + list(config.get("groups", {}).keys())

    # Inject 'Samples' manually if not already present
    if "Samples" not in group_vars and "Samples" in df.columns:
        group_vars.append("Samples")

    genes = sorted(df["gene"].unique())
    return genes, group_vars


def _plot_controls(genes: list[str], group_vars: list[str]):
    st.markdown("### Plot Configuration")

    selected_genes = st.multiselect("Target Gene(s)", genes, default=genes)
    if not selected_genes:
        st.warning("Please select at least one gene to display.")
        st.stop()

    # --- Dropdowns for axis roles ---
    col1, col2, col3 = st.columns(3)

    filters = {}
    df = st.session_state["ddct_results_df"]

    with col1:
        x_axis = st.selectbox("X-axis Group", group_vars, index=0)
        if x_axis:
            x_filter = render_filter(df, "X-axis Group", x_axis)

    with col2:
        color_by = st.selectbox("Color By", ["None"] + group_vars, index=0)
        if color_by:
            c_filter = render_filter(df, "Color By", color_by)

    with col3:
        facet_by = st.selectbox("Facet By", ["None"] + group_vars, index=0)
        if facet_by:
            f_filter = render_filter(df, "Facet By", facet_by)

    # --- Dynamic filters for each selected group ---

    for k, v in [(x_axis, x_filter), (color_by, c_filter), (facet_by, f_filter)]:
        k_norm = _normalize_key(k)
        if k != "None" and v:
            filters[k_norm] = v

    # --- Plot options ---
    scale = st.radio("Y-axis Metric", ["ΔΔCt", "Fold Change (2^-ΔΔCt)"], horizontal=True)
    plot_type = st.radio("Plot Type", ["Bar", "Box"], horizontal=True)
    hide_ntc = st.checkbox("Hide NTC samples", value=True)

    return {
        "selected_genes": selected_genes,
        "group_by": [_normalize_key(x_axis)],
        "color_by": None if color_by == "None" else _normalize_key(color_by),
        "facet_col": None if facet_by == "None" else _normalize_key(facet_by),
        "scale": scale,
        "hide_ntc": hide_ntc,
        "plot_type": plot_type,
        "filters": filters
    }



def _has_plot_conflict(opts: dict) -> bool:
    keys = ["group_by", "color_by", "facet_col", "facet_row"]
    selected = [tuple(opts[k]) if isinstance(opts[k], list) else opts[k] for k in keys if opts.get(k)]
    seen = set()
    for val in selected:
        if val in seen:
            return True
        seen.add(val)
    return False

def run():
    st.title("Gene Expression Analysis")

    df: pd.DataFrame = st.session_state.get("ddct_results_df")
    config: ExperimentConfig = st.session_state.get("experiment_config")


    if df is None or config is None or df.empty:
        st.info("Please input Ct data and configure experiment.")
        return

    genes, group_vars = _get_config_options(df, config)
    opts = _plot_controls(genes, group_vars)

    for col, allowed_vals in opts["filters"].items():
        if col in df.columns:
            df = df[df[col].isin(allowed_vals)]

    if _has_plot_conflict(opts):
        st.warning("⚠️ You are using the same variable (e.g. 'Age') for multiple roles. Please adjust your selections.")
        return

    plot_result = build_ddct_plot(
        df=df,
        genes=opts["selected_genes"],
        group_by=opts["group_by"],
        y_scale=opts["scale"],
        kind=opts["plot_type"].lower(),
        facet_col=opts["facet_col"],
        facet_row=None,
        color_by=opts["color_by"],
        hide_ntc=opts["hide_ntc"]
    )

    if isinstance(plot_result, list):
        all_y = np.concatenate([
            d["plot_value"].values if "plot_value" in d.columns else d["mean"].values
            for _, d, _ in plot_result
        ])
        y_min, y_max = float(np.nanmin(all_y)), float(np.nanmax(all_y))
        num_plots = len(plot_result)

        base_fig = plot_result[0][0]
        legend_traces = [
            go.Bar(
                x=[None], y=[None],
                name=trace.name,
                marker=dict(color=trace.marker.color),
                showlegend=True
            )
            for trace in base_fig.data
            if trace.name and hasattr(trace, "marker") and getattr(trace.marker, "color", None)
        ]

        if legend_traces:
            cols = st.columns([4] * num_plots + [1])
        else:
            cols = st.columns(num_plots)

        for idx, (fig, _, _) in enumerate(plot_result):
            fig.update_layout(
                yaxis=dict(
                    range=[y_min, y_max],
                    showticklabels=(idx == 0),
                    title_text="Fold Change" if idx == 0 else None
                ),
                showlegend=False
            )
            fig.update_xaxes(tickangle=0)
            with cols[idx]:
                st.plotly_chart(fig, use_container_width=True)

        if legend_traces:
            legend_fig = go.Figure(data=legend_traces)
            legend_fig.update_layout(
                showlegend=True,
                legend=dict(orientation="v", yanchor="top", y=1.0, xanchor="left", x=0.0),
                height=300,
                margin=dict(l=0, r=0, t=10, b=10),
                xaxis_visible=False,
                yaxis_visible=False
            )
            with cols[-1]:
                st.plotly_chart(legend_fig, use_container_width=True)

        plot_df = next(
            (d for _, d, _ in plot_result if "_x_label" in d.columns and "plot_value" in d.columns),
            None
        )

    else:
        fig, summary, plot_df = plot_result
        st.plotly_chart(fig, use_container_width=True)

    if plot_df is not None:
        render_plot_data_tables(plot_df, plot_result, opts)
    else:
        st.warning("Could not display raw data — plotting frame missing or invalid.")


run()