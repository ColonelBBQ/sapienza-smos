from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).parent
INPUT_PATH = BASE_DIR / "dataset" / "dataset_raw.csv"
OUTPUT_PATH = BASE_DIR / "dataset" / "dataset_enriched.csv"
LT_OUTPUT_PATH = BASE_DIR / "dataset" / "dataset_lt.csv"
ST_OUTPUT_PATH = BASE_DIR / "dataset" / "dataset_st.csv"
LT_COLUMNS = [
    "region",
    "year",
    "tfr",
    "share_pop_25_39",
    "median_age",
    "population_total",
    "welfare_users",
    "weddings_per_1000",
    "marriage_age_mean",
    "housing_cost_ratio",
]


def _predict_2024_for_column(region_df: pd.DataFrame, column: str) -> float | pd.NA:
    """
    Fit a simple linear regression (value ~ year) on the available years for a single region/column
    and return the predicted value for 2024. Returns pd.NA if there is not enough data.
    """
    known = region_df[["year", column]].dropna()
    known = known[known["year"] != 2024]
    if len(known) < 2:
        return pd.NA

    years = known["year"].astype(float).to_numpy()
    values = known[column].astype(float).to_numpy()
    slope, intercept = np.polyfit(years, values, 1)
    return float(slope * 2024 + intercept)


def _predict_for_year(region_df: pd.DataFrame, column: str, year: int) -> float | pd.NA:
    """Same as _predict_2024_for_column but allows a custom target year."""
    known = region_df[["year", column]].dropna()
    known = known[known["year"] != year]
    if len(known) < 2:
        return pd.NA

    years = known["year"].astype(float).to_numpy()
    values = known[column].astype(float).to_numpy()
    slope, intercept = np.polyfit(years, values, 1)
    return float(slope * year + intercept)


def _fill_year_for_columns(df: pd.DataFrame, columns: Iterable[str], year: int) -> pd.DataFrame:
    """Return a copy of df with the requested year filled for the provided columns."""
    if year not in set(df["year"].dropna().astype(int)):
        raise ValueError(f"No rows for year {year} found in input dataset")

    enriched = df.copy()
    for col in columns:
        for region, region_df in df.groupby("region"):
            mask_yr = (enriched["region"] == region) & (enriched["year"] == year)
            if not mask_yr.any():
                continue
            current_val = enriched.loc[mask_yr, col].iloc[0]
            if pd.notna(current_val):
                continue

            predicted = _predict_for_year(region_df, col, year)
            if pd.notna(predicted):
                enriched.loc[mask_yr, col] = predicted
    return enriched


def enrich_2024_values(input_path: Path = INPUT_PATH, output_path: Path = OUTPUT_PATH) -> Path:
    """
    Read the raw dataset and fill missing values for 2024 for all numeric columns,
    additionally fill missing 2023 for salary_avg_hourly,
    and persist two extra views:
      - dataset_lt.csv with a limited column set.
      - dataset_st.csv with all columns but only years 2019–2024.
    """
    df = pd.read_csv(input_path)
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")

    numeric_columns: Iterable[str] = [col for col in df.columns if col not in {"region", "year"}]

    enriched = _fill_year_for_columns(df, numeric_columns, 2024)
    if "salary_avg_hourly" in numeric_columns:
        enriched = _fill_year_for_columns(enriched, ["salary_avg_hourly"], 2023)

    # Convert weddings count to weddings per 1,000 inhabitants.
    if "weddings_total" in enriched.columns and "population_total" in enriched.columns:
        enriched["weddings_per_1000"] = (enriched["weddings_total"] / enriched["population_total"]) * 1000
        enriched = enriched.drop(columns=["weddings_total"])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    enriched.to_csv(output_path, index=False)

    # Save limited target view.
    missing_cols = [col for col in LT_COLUMNS if col not in enriched.columns]
    if missing_cols:
        raise ValueError(f"Cannot build dataset_lt, missing columns: {missing_cols}")
    lt_df = enriched[LT_COLUMNS].copy()
    lt_df.to_csv(LT_OUTPUT_PATH, index=False)

    # Save short-term view (all columns, 2019–2024).
    years_numeric = pd.to_numeric(enriched["year"], errors="coerce")
    st_df = enriched[years_numeric.between(2019, 2024, inclusive="both")].copy()
    st_df.to_csv(ST_OUTPUT_PATH, index=False)

    return output_path


if __name__ == "__main__":
    path = enrich_2024_values()
    print(f"Created enriched dataset with 2023/2024 backfilled values at: {path}")
    print(f"Created limited-target dataset at: {LT_OUTPUT_PATH}")
    print(f"Created short-term dataset at: {ST_OUTPUT_PATH}")
