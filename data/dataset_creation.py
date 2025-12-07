import re
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent
DEPENDENT_PATH = DATA_DIR / "dependent_variable" / "dependent_1_tfr.csv"
INDEP_DEMO_PATH = DATA_DIR / "independent_variables" / "independent_1_demo.csv"
OUTPUT_PATH = DATA_DIR / "dataset.csv"


def load_dependent_tfr(path: Path = DEPENDENT_PATH) -> pd.DataFrame:
    """Load the dependent TFR CSV and return a tidy region/year/value DataFrame."""
    df = pd.read_csv(path, encoding="utf-8-sig")
    if "Territorio" not in df.columns:
        raise ValueError("Expected 'Territorio' column in dependent variable file")

    df = df.rename(columns={"Territorio": "region"})

    # Drop note/empty columns if present.
    note_cols = [col for col in df.columns if isinstance(col, str) and ("Note" in col or col.strip() == "")]
    df = df.drop(columns=note_cols, errors="ignore")

    # Normalize year column names (e.g., '2024 (p)' -> 2024).
    rename_map = {}
    for col in df.columns:
        if col == "region":
            continue
        match = re.search(r"\d{4}", str(col))
        rename_map[col] = int(match.group(0)) if match else col
    df = df.rename(columns=rename_map)

    value_cols = [c for c in df.columns if c != "region"]
    tidy = df.melt(id_vars="region", value_vars=value_cols, var_name="year", value_name="tfr")
    tidy["year"] = pd.to_numeric(tidy["year"], errors="coerce").astype("Int64")
    tidy["tfr"] = pd.to_numeric(tidy["tfr"], errors="coerce")
    tidy = tidy.dropna(subset=["tfr"]).sort_values(["region", "year"]).reset_index(drop=True)

    # Keep only years from 2004 onward (aligns with most independent series coverage).
    tidy = tidy[tidy["year"] >= 2004].reset_index(drop=True)

    # Remove aggregates / unwanted territories.
    drop_regions = {
        "Italia",
        "Provincia Autonoma di Trento",
        "Provincia Autonoma di Bolzano",
    }
    tidy = tidy[~tidy["region"].isin(drop_regions)].reset_index(drop=True)
    return tidy


def load_independent_demo(path: Path = INDEP_DEMO_PATH) -> pd.DataFrame:
    """
    Load the demographic CSV and compute the share of population aged 25–39.
    The source contains only 2002, so we treat this share as static by region.
    """
    df = pd.read_csv(path, sep=";", skiprows=4)
    df = df.rename(columns={"Territorio/Età": "code", "Unnamed: 1": "region"})
    df = df[df["code"] != "Codice regione"]

    # Keep only region-level rows (2-digit codes).
    df["code"] = df["code"].astype(str)
    df = df[df["code"].str.fullmatch(r"\d{2}")]

    # Keep numeric age columns (0–100) and convert everything numeric.
    age_cols = [col for col in df.columns if col not in {"code", "region"}]
    df[age_cols] = df[age_cols].apply(pd.to_numeric, errors="coerce")

    # Total population across all ages.
    df["total"] = df[age_cols].sum(axis=1)

    # Share of population aged 25–39.
    age_25_39_cols = [col for col in age_cols if 25 <= int(col) <= 39]
    df["pop_25_39"] = df[age_25_39_cols].sum(axis=1)
    df["share_pop_25_39"] = df["pop_25_39"] / df["total"]

    demo = df[["region", "share_pop_25_39"]].copy()
    demo = demo.drop_duplicates(subset=["region"])
    drop_regions = {
        "Italia",
        "Provincia Autonoma di Trento",
        "Provincia Autonoma di Bolzano",
    }
    demo = demo[~demo["region"].isin(drop_regions)]
    return demo.reset_index(drop=True)


def create_dataset_csv() -> Path:
    """Create dataset.csv combining dependent and available independent variables."""
    tidy_dep = load_dependent_tfr()
    demo = load_independent_demo()

    merged = tidy_dep.merge(demo, on="region", how="left")
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(OUTPUT_PATH, index=False)
    return OUTPUT_PATH


if __name__ == "__main__":
    path = create_dataset_csv()
    print(f"Created dataset (dependent variable) at: {path}")
