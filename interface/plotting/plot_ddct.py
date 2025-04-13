# interface/plotting/plot_ddct.py

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.graph_objects import Figure
from typing import Optional, Tuple, Literal, Union, List


def build_ddct_plot(
    df: pd.DataFrame,
    genes: list[str],
    group_by: list[str],
    y_scale: Literal["ΔΔCt", "Fold Change", "log2FoldChange"] = "Fold Change",
    kind: Literal["box", "bar"] = "box",
    facet_col: Optional[str] = None,
    facet_row: Optional[str] = None,
    color_by: Optional[str] = None,
    hide_ntc: bool = False
) -> Union[Tuple[Figure, pd.DataFrame, pd.DataFrame], List[Tuple[Figure, pd.DataFrame, str]]]:

    df = _filter_genes(df, genes)
    if hide_ntc:
        df = _filter_ntc(df)

    df["plot_value"], ylabel = _get_plot_values(df, y_scale)
    df["_x_label"] = _build_x_label(df, group_by)

    group_keys = [color_by, facet_col, facet_row]
    group_keys = [k for k in group_keys if k]

    summary = _summarize_groups(df, group_keys)
    summary = summary[(summary["mean"].notna()) & (summary["count"] > 0)]

    if kind == "bar" and (facet_row or facet_col):
        return _split_barplots(summary, df, genes, y_scale, ylabel, color_by, facet_col, facet_row)
    if kind == "box" and (facet_row or facet_col):
        return _split_boxplots(df, genes, y_scale, ylabel, color_by, facet_col, facet_row)

    return _single_plot(df, summary, kind, genes, y_scale, ylabel, color_by, facet_col, facet_row)


# --- Plot paths ---

def _single_plot(
    df: pd.DataFrame,
    summary: pd.DataFrame,
    kind: str,
    genes: list[str],
    y_scale: str,
    ylabel: str,
    color_by: Optional[str],
    facet_col: Optional[str],
    facet_row: Optional[str]
) -> Tuple[Figure, pd.DataFrame, pd.DataFrame]:

    category_orders = {"_x_label": sorted(summary["_x_label"].unique())}

    if kind == "bar":
        fig = px.bar(
            summary,
            x="_x_label",
            y="mean",
            error_y="sem",
            color=color_by if color_by in summary.columns else None,
            facet_col=facet_col,
            facet_row=facet_row,
            labels={"_x_label": "", "mean": ylabel, "sem": "SEM"},
            category_orders=category_orders
        )
        fig.update_layout(barmode="group")
    else:
        fig = px.box(
            df,
            x="_x_label",
            y="plot_value",
            points="all",
            color=color_by,
            facet_col=facet_col,
            facet_row=facet_row,
            labels={"_x_label": "", "plot_value": ylabel},
            category_orders=category_orders
        )

    fig.update_layout(margin=dict(t=40, b=40))
    fig.update_xaxes(tickangle=0)
    return fig, summary, df


def _split_barplots(
    summary: pd.DataFrame,
    raw_df: pd.DataFrame,
    genes: list[str],
    y_scale: str,
    ylabel: str,
    color_by: Optional[str],
    facet_col: Optional[str],
    facet_row: Optional[str]
) -> List[Tuple[Figure, pd.DataFrame, str]]:
    facet_keys = [k for k in [facet_row, facet_col] if k]
    figures = []

    for facet_vals, subset in summary.groupby(facet_keys):
        facet_vals = (facet_vals,) if isinstance(facet_vals, str) else facet_vals
        label = ", ".join(f"{k}={v}" for k, v in zip(facet_keys, facet_vals))

        # Match raw data subset
        raw_subset = raw_df.copy()
        for k, v in zip(facet_keys, facet_vals):
            raw_subset = raw_subset[raw_subset[k] == v]

        fig = px.bar(
            subset,
            x="_x_label",
            y="mean",
            error_y="sem",
            color=color_by if color_by in subset.columns else None,
            labels={"_x_label": "", "mean": ylabel, "sem": "SEM"},
            category_orders={"_x_label": sorted(subset["_x_label"].unique())}
        )
        fig.update_layout(barmode="group", height=400)
        fig.update_xaxes(tickangle=0, automargin=True)
        figures.append((fig, raw_subset, label))

    return figures


def _split_boxplots(
    df: pd.DataFrame,
    genes: list[str],
    y_scale: str,
    ylabel: str,
    color_by: Optional[str],
    facet_col: Optional[str],
    facet_row: Optional[str]
) -> List[Tuple[Figure, pd.DataFrame, str]]:
    facet_keys = [k for k in [facet_row, facet_col] if k]
    figures = []

    for facet_vals, subset in df.groupby(facet_keys):
        facet_vals = (facet_vals,) if isinstance(facet_vals, str) else facet_vals
        label = ", ".join(f"{k}={v}" for k, v in zip(facet_keys, facet_vals))

        fig = px.box(
            subset,
            x="_x_label",
            y="plot_value",
            points="all",
            color=color_by if color_by in subset.columns else None,
            labels={"_x_label": "", "plot_value": ylabel},
            category_orders={"_x_label": sorted(subset["_x_label"].unique())}
        )
        fig.update_layout(height=400)
        fig.update_xaxes(tickangle=0, automargin=True)
        figures.append((fig, subset, label))

    return figures


# --- Helpers ---

def _filter_genes(df: pd.DataFrame, genes: list[str]) -> pd.DataFrame:
    return df[df["gene"].isin(genes)].copy()


def _filter_ntc(df: pd.DataFrame) -> pd.DataFrame:
    if "sample_id" not in df.columns and "Sample ID" in df.columns:
        df = df.rename(columns={"Sample ID": "sample_id"})
    return df[~df["sample_id"].str.contains(r"\bntc\b", case=False, na=False)]


def _get_plot_values(df: pd.DataFrame, y_scale: str) -> Tuple[pd.Series, str]:
    scale = y_scale.casefold()

    if scale in {"ddct", "δδct", "ΔΔct".casefold()}:
        if "ΔΔCt" not in df.columns or df["ΔΔCt"].isna().all():
            raise ValueError("ΔΔCt values not available. Ensure reference condition is set and ΔΔCt analysis was run.")
        return df["ΔΔCt"], "ΔΔCt"

    if scale in {"log2foldchange", "log₂(fold change)"}:
        if "Fold Change" not in df.columns:
            raise ValueError("Fold Change values not available. Run ΔΔCt processing first.")
        return np.log2(df["Fold Change"].replace(0, np.nan)), "log₂(Fold Change)"

    if "Fold Change" not in df.columns:
        raise ValueError("Fold Change values not available. Run ΔΔCt processing first.")
    return df["Fold Change"], "Fold Change (2^-ΔΔCt)"


def _build_x_label(df: pd.DataFrame, group_by: list[str]) -> pd.Series:
    group_by = ["gene" if g == "Gene" else g for g in group_by]
    return df[group_by].astype(str).agg("_".join, axis=1) if len(group_by) > 1 else df[group_by[0]].astype(str)


def _summarize_groups(df: pd.DataFrame, extra_group_cols: list[str]) -> pd.DataFrame:
    group_cols = ["_x_label"] + [col for col in extra_group_cols if col in df.columns]

    rename_map = {}
    safe_df = df.copy()
    for col in group_cols:
        if col in safe_df.columns and col in safe_df.index.names:
            new_col = f"{col}_grp"
            rename_map[col] = new_col
            safe_df = safe_df.rename(columns={col: new_col})
            group_cols = [rename_map.get(c, c) for c in group_cols]

    grouped = safe_df.groupby(group_cols)["plot_value"]
    summary = grouped.agg(mean="mean", std="std", count="count").reset_index()
    summary["sem"] = summary["std"] / summary["count"] ** 0.5

    return summary.rename(columns={v: k for k, v in rename_map.items()})
