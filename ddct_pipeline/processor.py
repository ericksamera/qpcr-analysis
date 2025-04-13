import pandas as pd
import numpy as np

from interface.backend.session_schema import ExperimentConfig
from ddct_pipeline.types import CtRow

def geo_mean(series):
    series = pd.to_numeric(series, errors="coerce")
    series = series[series > 0]  # filter out non-positive values
    return np.exp(np.mean(np.log(series))) if not series.empty else np.nan


def process_ddct(rows: list[CtRow], config: ExperimentConfig) -> pd.DataFrame:
    # Convert CtRows to DataFrame
    df = pd.DataFrame([{
        "sample_id": r.sample_id,
        "gene": r.gene,
        "ct": geo_mean(r.ct) if isinstance(r.ct, (tuple, list)) else r.ct,
        **r.metadata
    } for r in rows])

    df["ct"] = pd.to_numeric(df["ct"], errors="coerce")
    df = df[df["ct"] > 0]  # geometric mean requires positive values

    # Step 1: Average technical replicates using geometric mean
    metadata_keys = [k for k in df.columns if k not in {"sample_id", "gene", "ct"}]

    df["n"] = 1  # replicate count
    df = df.groupby(["sample_id", "gene"], as_index=False).agg({
        "ct": geo_mean,
        "n": "count",
        **{k: "first" for k in metadata_keys}
    })

    # Step 2: ΔCt = Ct - refCt
    ref_genes = config["reference_genes"]
    ref_cts = df[df["gene"].isin(ref_genes)].groupby("sample_id")["ct"].apply(geo_mean).rename("ref_ct")
    df = df.join(ref_cts, on="sample_id")
    df["ΔCt"] = df["ct"] - df["ref_ct"]

    # Step 3: ΔΔCt = ΔCt - ref(ΔCt)
    ref_cond = config["reference_condition"]
    grouping_var = config["grouping_variables"][0].name
    ref_means = df[df[grouping_var] == ref_cond].groupby("gene")["ΔCt"].mean().rename("ΔCt_ref")
    df = df.join(ref_means, on="gene")
    df["ΔΔCt"] = df["ΔCt"] - df["ΔCt_ref"]

    # Step 4: Fold change
    df["Fold Change"] = 2 ** (-df["ΔΔCt"])

    return df
