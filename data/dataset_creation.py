import io
import re
from pathlib import Path
from typing import Optional, Set
import pandas as pd

DATA_DIR = Path(__file__).parent
DEPENDENT_PATH = DATA_DIR / "dependent_variable" / "dependent_1_tfr.csv"
INDEP_DEMO_DIR = DATA_DIR / "independent_variables" / "independent_1_demo"
INDEP_DEMO_PATH = INDEP_DEMO_DIR / "independent_1_demo.csv"
INDEP_WELFARE_PATH = DATA_DIR / "independent_variables" / "independent_2_welfare.csv"
INDEP_FEMALE_EMPLOY_PATH = DATA_DIR / "independent_variables" / "independent_3_female_employment.csv"
OUTPUT_PATH = DATA_DIR / "dataset.csv"
DROP_REGIONS = {
    "Italia",
    "Provincia Autonoma di Trento",
    "Provincia Autonoma di Bolzano",
}

def _clean_region_name(raw: str) -> str:
    """Normalize region names to match the dependent variable naming throught the ISTAT datasets"""
    if pd.isna(raw):
        return ""
    name = str(raw).strip().strip("'\"")
    name = name.replace("  ", " ")
    name = name.replace(" / ", "/")
    name = name.replace("Valle d\"Aosta / Vallée d\"Aoste", "Valle d'Aosta/Vallée d'Aoste")
    name = name.replace("Valle d’Aosta / Vallée d’Aoste", "Valle d'Aosta/Vallée d'Aoste")
    name = name.replace("Trentino Alto Adige / Südtirol", "Trentino-Alto Adige/Südtirol")
    name = name.replace("Trentino-Alto Adige / Südtirol", "Trentino-Alto Adige/Südtirol")
    name = name.replace("Provincia Autonoma Bolzano / Bozen", "Provincia Autonoma di Bolzano")
    name = name.replace("Provincia Autonoma Trento", "Provincia Autonoma di Trento")
    return name


def load_dependent_tfr(path: Path = DEPENDENT_PATH) -> pd.DataFrame:
    """Load the dependent TFR CSV on region/year/value"""

    df = pd.read_csv(path, encoding="utf-8-sig")
    if "Territorio" not in df.columns:
        raise ValueError("Expected 'Territorio' column in dependent variable file")

    # Translate to english
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
    tidy = tidy[~tidy["region"].isin(DROP_REGIONS)].reset_index(drop=True)
    return tidy


def load_independent_demo(path: Path = INDEP_DEMO_PATH, years: Optional[pd.Series] = None) -> pd.DataFrame:
    """
    Load the demographic CSV (stacked blocks by year) and compute the share of population aged 25–39.
    Each block starts with a line containing "Tutte le cittadinanze - Anno: <YEAR>".
    """
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    title_indices = [idx for idx, line in enumerate(lines) if "Tutte le cittadinanze - Anno:" in line]
    title_indices.append(len(lines))

    # Keep only region-level rows (2-digit codes).
    blocks = []
    for i in range(len(title_indices) - 1):
        start = title_indices[i]
        end = title_indices[i + 1]
        year_line = lines[start]
        match = re.search(r"Anno:\s*(\d{4})", year_line)
        if not match:
            continue
        year = int(match.group(1))

        block_lines = lines[start + 1 : end]
        # Identify the first table within the block (there are multiple: Totale, Maschi, Femmine).
        header_positions = [idx for idx, line in enumerate(block_lines) if line.startswith("Territorio/Età")]
        if not header_positions:
            continue
        first_header = header_positions[0]
        next_header = header_positions[1] if len(header_positions) > 1 else len(block_lines)
        table_lines = block_lines[first_header:next_header]
        if not table_lines:
            continue

        block_csv = "\n".join(table_lines)
        df = pd.read_csv(io.StringIO(block_csv), sep=";")
        if "Territorio/Età" not in df.columns:
            continue
        df = df.rename(columns={"Territorio/Età": "code", "Regione": "region", "Unnamed: 1": "region"})
        df = df[df["code"] != "Codice regione"]
        df["code"] = df["code"].astype(str)
        df = df[df["code"].str.fullmatch(r"\d{2}")]

        age_cols = [col for col in df.columns if str(col).isdigit()]
        df[age_cols] = df[age_cols].apply(pd.to_numeric, errors="coerce")
        df["total"] = df[age_cols].sum(axis=1)
        age_25_39_cols = [col for col in age_cols if 25 <= int(col) <= 39]
        df["pop_25_39"] = df[age_25_39_cols].sum(axis=1)
        df["share_pop_25_39"] = df["pop_25_39"] / df["total"]
        df["year"] = year
        blocks.append(df[["region", "year", "share_pop_25_39"]])

    if not blocks:
        return pd.DataFrame(columns=["region", "year", "share_pop_25_39"])

    demo = pd.concat(blocks, ignore_index=True)
    demo = demo[~demo["region"].isin(DROP_REGIONS)].reset_index(drop=True)

    if years is not None:
        years_set = set(pd.to_numeric(years, errors="coerce").dropna())
        demo = demo[demo["year"].isin(years_set)]
    return demo.reset_index(drop=True)


def load_independent_demo_alt(dir_path: Path = INDEP_DEMO_DIR, years: Optional[pd.Series] = None) -> pd.DataFrame:
    """
    Load alternative demographic CSVs (long by age, one year per file) under independent_1_demo/.
    File names contain the year (e.g., independent_1.1_demo_2023.csv); headers also include '1° gennaio <YYYY>'.
    """
    frames = []
    if not dir_path.exists():
        return pd.DataFrame(columns=["region", "year", "share_pop_25_39"])

    allowed_years = None
    if years is not None:
        allowed_years = set(pd.to_numeric(years, errors="coerce").dropna())

    for file in sorted(dir_path.glob("independent_1.1_demo_*.csv")):
        year = None
        fname_match = re.search(r"_(\d{4})", file.name)
        if fname_match:
            year = int(fname_match.group(1))

        lines = file.read_text(encoding="utf-8-sig").splitlines()
        if lines:
            hdr_match = re.search(r"1° gennaio\s+(\d{4})", lines[0])
            if hdr_match:
                year = year or int(hdr_match.group(1))

        if year is None:
            continue
        if allowed_years is not None and year not in allowed_years:
            continue

        df = pd.read_csv(file, sep=";", skiprows=1, quotechar='"')
        df = df.rename(
            columns={
                "Codice regione": "code",
                "Regione": "region",
                "Età": "age",
                "Totale": "total",
            }
        )
        if "total" not in df.columns or "age" not in df.columns or "region" not in df.columns:
            continue

        df["region"] = df["region"].apply(_clean_region_name)
        df["age"] = pd.to_numeric(df["age"], errors="coerce")
        df["total"] = pd.to_numeric(df["total"], errors="coerce")
        df = df.dropna(subset=["age", "total"])
        # Drop summary rows marked with age 999.
        df = df[df["age"] != 999]
        df = df[~df["region"].isin(DROP_REGIONS)]

        totals = df.groupby("region", as_index=False)["total"].sum()
        pop_25_39 = df[df["age"].between(25, 39)].groupby("region", as_index=False)["total"].sum()
        merged = totals.merge(pop_25_39, on="region", how="left", suffixes=("_total", "_25_39"))
        merged["share_pop_25_39"] = merged["total_25_39"] / merged["total_total"]
        merged["year"] = year
        frames.append(merged[["region", "year", "share_pop_25_39"]])

    if not frames:
        return pd.DataFrame(columns=["region", "year", "share_pop_25_39"])
    return pd.concat(frames, ignore_index=True)


def load_independent_welfare(
    path: Path = INDEP_WELFARE_PATH,
    allowed_regions: Optional[Set[str]] = None,
    years: Optional[pd.Series] = None,
) -> pd.DataFrame:
    """
    Load welfare data and aggregate total users per region/year.
    Values are merged on region+year; for years without data, the merge will yield NaN.
    """
    df = pd.read_csv(path, encoding="utf-8-sig")
    df["region"] = df["Territorio"].apply(_clean_region_name)
    df["year"] = pd.to_numeric(df["TIME_PERIOD"], errors="coerce").astype("Int64")
    df["Osservazione"] = pd.to_numeric(df["Osservazione"], errors="coerce")

    if allowed_regions is not None:
        df = df[df["region"].isin(allowed_regions)]

    df = df[~df["region"].isin(DROP_REGIONS)]
    grouped = df.groupby(["region", "year"], as_index=False)["Osservazione"].sum()
    grouped = grouped.rename(columns={"Osservazione": "welfare_users"})

    if years is not None:
        grouped = grouped[grouped["year"].isin(set(pd.to_numeric(years, errors="coerce").dropna()))]
    return grouped


def load_independent_female_employment(
    path: Path = INDEP_FEMALE_EMPLOY_PATH,
    allowed_regions: Optional[Set[str]] = None,
    years: Optional[pd.Series] = None,
) -> pd.DataFrame:
    """
    Load female employment rate (15-64) per region/year.
    """
    df = pd.read_csv(path, encoding="utf-8-sig")
    df["region"] = df["Territorio"].apply(_clean_region_name)
    df["year"] = pd.to_numeric(df["TIME_PERIOD"], errors="coerce").astype("Int64")
    df["female_employment_rate"] = pd.to_numeric(df["Osservazione"], errors="coerce")

    if allowed_regions is not None:
        df = df[df["region"].isin(allowed_regions)]
    df = df[~df["region"].isin(DROP_REGIONS)]

    grouped = df.groupby(["region", "year"], as_index=False)["female_employment_rate"].mean()
    if years is not None:
        grouped = grouped[grouped["year"].isin(set(pd.to_numeric(years, errors="coerce").dropna()))]
    return grouped




def create_dataset_csv() -> Path:
    """Create dataset.csv combining dependent and available independent variables."""
    tidy_dep = load_dependent_tfr()
    allowed_regions = set(tidy_dep["region"].unique())
    demo_main = load_independent_demo(years=tidy_dep["year"])
    demo_alt = load_independent_demo_alt(years=tidy_dep["year"])
    demo = pd.concat([demo_main, demo_alt], ignore_index=True)
    demo = demo.sort_values("year").drop_duplicates(subset=["region", "year"], keep="last")
    demo = demo[demo["region"].isin(allowed_regions)]

    welfare = load_independent_welfare(allowed_regions=allowed_regions, years=tidy_dep["year"])
    female_emp = load_independent_female_employment(allowed_regions=allowed_regions, years=tidy_dep["year"])

    merged = tidy_dep.merge(demo, on=["region", "year"], how="left")
    merged = merged.merge(welfare, on=["region", "year"], how="left")
    merged = merged.merge(female_emp, on=["region", "year"], how="left")
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(OUTPUT_PATH, index=False)
    return OUTPUT_PATH


if __name__ == "__main__":
    path = create_dataset_csv()
    print(f"Created dataset (dependent variable) at: {path}")
