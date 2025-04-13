# ddct_pipeline/validators.py
import pandas as pd

def validate_rows(rows, config) -> list[str]:
    errors = []
    genes = set(r.gene for r in rows)
    samples = set(r.sample_id for r in rows)

    for ref_gene in config["reference_genes"]:
        if ref_gene not in genes:
            errors.append(f"Missing reference gene: {ref_gene}")

    ref_cond = config["reference_condition"]
    grouping_var = config["grouping_variables"][0].name
    if ref_cond not in config["groups"].get(grouping_var, []):
        errors.append(f"Reference condition '{ref_cond}' not found in group '{grouping_var}'")

    for row in rows:
        if row.ct is None or pd.isna(row.ct):
            errors.append(f"Missing Ct value for sample '{row.sample_id}', gene '{row.gene}'")

    return errors
