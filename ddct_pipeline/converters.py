# ddct_pipeline/converters.py

import pandas as pd
from ddct_pipeline.types import CtRow
import numpy as np

def df_to_rows(df: pd.DataFrame) -> list[CtRow]:
    return [
        CtRow(
            sample_id=row["sample_id"],
            gene=row["gene"],
            ct=row["ct"],
            metadata={k: row[k] for k in row.index if k not in {"sample_id", "gene", "ct"}}
        )
        for _, row in df.iterrows()
    ]

def rows_to_df(rows: list[CtRow]) -> pd.DataFrame:
    data = []
    for r in rows:
        base = {
            "sample_id": r.sample_id,
            "gene": r.gene,
            "ct": r.ct  # <- could be tuple
        }
        base.update(r.metadata)
        data.append(base)
    return pd.DataFrame(data)

def df_to_rows(df: pd.DataFrame) -> list[CtRow]:
    return [
        CtRow(
            sample_id=row["sample_id"],
            gene=row["gene"],
            ct=row["ct"],
            metadata={k: row[k] for k in row.index if k not in {"sample_id", "gene", "ct"}}
        )
        for _, row in df.iterrows()
    ]

def rows_to_df(rows: list[CtRow]) -> pd.DataFrame:
    data = []
    for r in rows:
        base = {
            "sample_id": r.sample_id,
            "gene": r.gene,
            "ct": r.ct
        }
        base.update(r.metadata)
        data.append(base)
    return pd.DataFrame(data)

# --- NEW Excel parser utils ---

EXPECTED_COLUMNS = {
    "sample name": "sample_id",
    "target name": "gene",
    "ct": "ct"
}

def parse_excel_ct_file(file) -> pd.DataFrame:
    """Parse and clean Ct data from a single Excel file."""
    raw = pd.read_excel(file, sheet_name="Results", header=None)

    header_row_idx = None
    for i, row in raw.iterrows():
        row_vals = row.astype(str).str.lower().str.strip().tolist()
        if "sample name" in row_vals and "target name" in row_vals:
            header_row_idx = i
            break

    if header_row_idx is None:
        raise ValueError("Could not find header row.")

    df = pd.read_excel(file, sheet_name="Results", header=header_row_idx)
    df.columns = df.columns.str.strip().str.lower()

    if not all(col in df.columns for col in EXPECTED_COLUMNS):
        missing = [col for col in EXPECTED_COLUMNS if col not in df.columns]
        raise ValueError(f"Missing required columns: {missing}")

    df = df[list(EXPECTED_COLUMNS.keys())].rename(columns=EXPECTED_COLUMNS)
    df["ct"] = pd.to_numeric(df["ct"], errors="coerce")
    df = df.dropna(subset=["sample_id", "gene", "ct"])
    df = df[df["ct"].apply(lambda x: isinstance(x, (int, float)))]
    df["source_file"] = file.name
    df["original_sample_id"] = df["sample_id"]

    return df


def collapse_replicates(df: pd.DataFrame) -> pd.DataFrame:
    """Collapse technical replicates and compute mean Ct."""
    grouped = df.groupby(["sample_id", "gene", "source_file", "original_sample_id"])
    collapsed = []

    for (sid, gene, src, orig), group in grouped:
        ct_vals = tuple(round(v, 2) for v in group["ct"].tolist())
        ct_mean = round(np.mean(ct_vals), 2)

        collapsed.append({
            "Sample ID": sid,
            "Gene": gene,
            "Ct": ct_mean,
            "Replicates": list(ct_vals),
            "n": len(ct_vals),
            "Original Sample ID": orig,
            "Source File": src
        })

    return pd.DataFrame(collapsed)
