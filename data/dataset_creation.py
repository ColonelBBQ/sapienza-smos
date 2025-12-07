import io
import re
import csv
from pathlib import Path
from typing import Optional, Set
import pandas as pd

DATA_DIR = Path(__file__).parent
DEPENDENT_PATH = DATA_DIR / "dependent_variable" / "dependent_1_tfr.csv"
INDEP_DEMO_DIR = DATA_DIR / "independent_variables" / "independent_1_demo"
INDEP_DEMO_PATH = INDEP_DEMO_DIR / "independent_1_demo.csv"
INDEP_WELFARE_PATH = DATA_DIR / "independent_variables" / "independent_2_welfare.csv"
INDEP_FEMALE_EMPLOY_PATH = DATA_DIR / "independent_variables" / "independent_3_female_employment.csv"
INDEP_SALARY_PATH = DATA_DIR / "independent_variables" / "independent_7_salary.csv"
INDEP_WEDDINGS_PATH = DATA_DIR / "independent_variables" / "independent_6_weddings.csv"
INDEP_HOUSING_PATH = DATA_DIR / "independent_variables" / "independent_9_housing.csv"
INDEP_STABILITY_PATH = DATA_DIR / "independent_variables" / "independent_8_stability.csv"
INDEP_PRIMARY_SCHOOLS_PATH = DATA_DIR / "independent_variables" / "independent_10_primary_schools.csv"
INDEP_YOUTH_UNEMPLOY_PATH = DATA_DIR / "independent_variables" / "independent_11_unemployment_youth.csv"
INDEP_STRANGERS_PATH = DATA_DIR / "independent_variables" / "independent_12_strangers_percentage.csv"
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


def _weighted_median_from_counts(ages, counts):
    """Compute weighted median age given aligned age and count iterables."""
    pairs = [
        (int(age), float(cnt))
        for age, cnt in zip(ages, counts)
        if pd.notna(age) and pd.notna(cnt)
    ]
    if not pairs:
        return pd.NA
    total = sum(cnt for _, cnt in pairs)
    if total <= 0:
        return pd.NA
    target = total / 2
    running = 0.0
    for age, cnt in sorted(pairs, key=lambda x: x[0]):
        running += cnt
        if running >= target:
            return age
    return sorted(pairs, key=lambda x: x[0])[-1][0]


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
    tidy = tidy[tidy["year"] >= 2011].reset_index(drop=True)

    # Remove aggregates / unwanted territories.
    tidy = tidy[~tidy["region"].isin(DROP_REGIONS)].reset_index(drop=True)
    return tidy


def load_independent_demo(path: Path = INDEP_DEMO_PATH, years: Optional[pd.Series] = None) -> pd.DataFrame:
    """
    Load the demographic CSV (stacked blocks by year), compute the share of population aged 25–39
    and total population.
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
        df["population_total"] = df["total"]
        df["median_age"] = df.apply(
            lambda row: _weighted_median_from_counts(age_cols, [row[c] for c in age_cols]),
            axis=1,
        )
        df["year"] = year
        blocks.append(df[["region", "year", "share_pop_25_39", "median_age", "population_total"]])

    if not blocks:
        return pd.DataFrame(columns=["region", "year", "share_pop_25_39", "median_age", "population_total"])

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
        return pd.DataFrame(columns=["region", "year", "share_pop_25_39", "median_age", "population_total"])

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
        median_age = (
            df.groupby("region")
            .apply(lambda g: _weighted_median_from_counts(g["age"], g["total"]))
            .reset_index(name="median_age")
        )
        merged = totals.merge(pop_25_39, on="region", how="left", suffixes=("_total", "_25_39"))
        merged = merged.merge(median_age, on="region", how="left")
        merged["share_pop_25_39"] = merged["total_25_39"] / merged["total_total"]
        merged["population_total"] = merged["total_total"]
        merged["year"] = year
        frames.append(merged[["region", "year", "share_pop_25_39", "median_age", "population_total"]])

    if not frames:
        return pd.DataFrame(columns=["region", "year", "share_pop_25_39", "median_age", "population_total"])
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


def load_independent_salary(
    path: Path = INDEP_SALARY_PATH,
    allowed_regions: Optional[Set[str]] = None,
    years: Optional[pd.Series] = None,
) -> pd.DataFrame:
    """
    Load salary (HOUWAG_ENTEMP_AV_MI) per region/year.
    """
    df = pd.read_csv(path, encoding="utf-8-sig")
    df = df[df["DATA_TYPE"] == "HOUWAG_ENTEMP_AV_MI"]
    df["region"] = df["Territorio"].apply(_clean_region_name)
    df["year"] = pd.to_numeric(df["TIME_PERIOD"], errors="coerce").astype("Int64")
    df["salary_avg_hourly"] = pd.to_numeric(df["Osservazione"], errors="coerce")

    if allowed_regions is not None:
        df = df[df["region"].isin(allowed_regions)]
    df = df[~df["region"].isin(DROP_REGIONS)]

    grouped = df.groupby(["region", "year"], as_index=False)["salary_avg_hourly"].mean()
    if years is not None:
        grouped = grouped[grouped["year"].isin(set(pd.to_numeric(years, errors="coerce").dropna()))]
    return grouped


def load_independent_housing(
    path: Path = INDEP_HOUSING_PATH,
    allowed_regions: Optional[Set[str]] = None,
    years: Optional[pd.Series] = None,
) -> pd.DataFrame:
    """
    Load housing indicator ABITAZ_SPESA_REDD per region/year.
    """
    df = pd.read_csv(path, encoding="utf-8-sig")
    df = df[df["DATA_TYPE"] == "ABITAZ_SPESA_REDD"]
    df["region"] = df["Territorio"].apply(_clean_region_name)
    df["year"] = pd.to_numeric(df["TIME_PERIOD"], errors="coerce").astype("Int64")
    df["housing_cost_ratio"] = pd.to_numeric(df["Osservazione"], errors="coerce")

    if allowed_regions is not None:
        df = df[df["region"].isin(allowed_regions)]
    df = df[~df["region"].isin(DROP_REGIONS)]

    grouped = df.groupby(["region", "year"], as_index=False)["housing_cost_ratio"].mean()
    if years is not None:
        grouped = grouped[grouped["year"].isin(set(pd.to_numeric(years, errors="coerce").dropna()))]
    return grouped


def load_independent_stability(
    path: Path = INDEP_STABILITY_PATH,
    allowed_regions: Optional[Set[str]] = None,
    years: Optional[pd.Series] = None,
) -> pd.DataFrame:
    """
    Load employment stability ratio: permanent / total employees per region/year.
    Uses POSIZ_PROF=1 Dipendenti, Sesso=Totale, PERM_TEMP_EMPLOYEES 2 (permanent) and 9 (total).
    """
    df = pd.read_csv(path, encoding="utf-8-sig")
    df["region"] = df["Territorio"].apply(_clean_region_name)
    df["year"] = pd.to_numeric(df["TIME_PERIOD"], errors="coerce").astype("Int64")
    df["value"] = pd.to_numeric(df["Osservazione"], errors="coerce")

    # Filter to employees total and sexes total.
    df = df[(df["POSIZ_PROF"] == 1) & (df["SEX"] == 9)]

    if allowed_regions is not None:
        df = df[df["region"].isin(allowed_regions)]
    df = df[~df["region"].isin(DROP_REGIONS)]

    # Pivot PERM_TEMP_EMPLOYEES to columns for permanent vs total.
    pivoted = df.pivot_table(
        index=["region", "year"],
        columns="PERM_TEMP_EMPLOYEES",
        values="value",
        aggfunc="sum",
    )
    # 2 = Tempo indeterminato, 9 = Totale
    pivoted = pivoted.rename(columns={2: "permanent", 9: "total"}).reset_index()
    pivoted["employment_stability_ratio"] = pivoted["permanent"] / pivoted["total"]

    result = pivoted[["region", "year", "employment_stability_ratio"]]
    if years is not None:
        result = result[result["year"].isin(set(pd.to_numeric(years, errors="coerce").dropna()))]
    return result


def load_independent_primary_schools(
    path: Path = INDEP_PRIMARY_SCHOOLS_PATH,
    allowed_regions: Optional[Set[str]] = None,
    years: Optional[pd.Series] = None,
) -> pd.DataFrame:
    """
    Load childcare places per 100 children aged 0-2 (DATA_TYPE P_100CH_Y0_2, total sector) per region/year.
    """
    df = pd.read_csv(path, encoding="utf-8-sig")
    df = df[df["DATA_TYPE"] == "P_100CH_Y0_2"]
    df["region"] = df["Territorio"].apply(_clean_region_name)
    df["year"] = pd.to_numeric(df["TIME_PERIOD"], errors="coerce").astype("Int64")
    df["childcare_places_per_100_children_0_2"] = pd.to_numeric(df["Osservazione"], errors="coerce")

    if allowed_regions is not None:
        df = df[df["region"].isin(allowed_regions)]
    df = df[~df["region"].isin(DROP_REGIONS)]

    grouped = df.groupby(["region", "year"], as_index=False)["childcare_places_per_100_children_0_2"].mean()
    if years is not None:
        grouped = grouped[grouped["year"].isin(set(pd.to_numeric(years, errors="coerce").dropna()))]
    return grouped


def load_independent_youth_unemployment(
    path: Path = INDEP_YOUTH_UNEMPLOY_PATH,
    allowed_regions: Optional[Set[str]] = None,
    years: Optional[pd.Series] = None,
) -> pd.DataFrame:
    """
    Load youth unemployment rate (15-34) per region/year using DATA_TYPE UNEM_R and SEX=9 (Totale).
    """
    df = pd.read_csv(path, encoding="utf-8-sig")
    df = df[(df["DATA_TYPE"] == "UNEM_R") & (df["SEX"] == 9)]
    df["region"] = df["Territorio"].apply(_clean_region_name)
    df["year"] = pd.to_numeric(df["TIME_PERIOD"], errors="coerce").astype("Int64")
    df["youth_unemployment_rate_15_34"] = pd.to_numeric(df["Osservazione"], errors="coerce")

    if allowed_regions is not None:
        df = df[df["region"].isin(allowed_regions)]
    df = df[~df["region"].isin(DROP_REGIONS)]

    grouped = df.groupby(["region", "year"], as_index=False)["youth_unemployment_rate_15_34"].mean()
    if years is not None:
        grouped = grouped[grouped["year"].isin(set(pd.to_numeric(years, errors="coerce").dropna()))]
    return grouped


def load_independent_strangers_percentage(
    path: Path,
    population_df: pd.DataFrame,
    allowed_regions: Optional[Set[str]] = None,
    years: Optional[pd.Series] = None,
) -> pd.DataFrame:
    """
    Load foreign population counts (FJAN, total sex) and compute share of total population per region/year.
    """
    df = pd.read_csv(path, encoding="utf-8-sig")
    df = df[(df["DATA_TYPE"] == "FJAN") & (df["SEX"] == 9)]
    df["region"] = df["Territorio"].apply(_clean_region_name)
    df["year"] = pd.to_numeric(df["TIME_PERIOD"], errors="coerce").astype("Int64")
    df["foreign_population"] = pd.to_numeric(df["Osservazione"], errors="coerce")

    if allowed_regions is not None:
        df = df[df["region"].isin(allowed_regions)]
    df = df[~df["region"].isin(DROP_REGIONS)]

    population = population_df[["region", "year", "population_total"]].dropna(subset=["population_total"])
    merged = df.merge(population, on=["region", "year"], how="left")
    merged["foreign_population_share"] = merged["foreign_population"] / merged["population_total"]

    result = merged[["region", "year", "foreign_population", "foreign_population_share"]]
    if years is not None:
        result = result[result["year"].isin(set(pd.to_numeric(years, errors="coerce").dropna()))]
    return result


def load_independent_weddings(
    path: Path = INDEP_WEDDINGS_PATH,
    allowed_regions: Optional[Set[str]] = None,
    years: Optional[pd.Series] = None,
) -> pd.DataFrame:
    """
    Load weddings indicators NUPT_TOTM_FROM2017 (total marriages) and MAGEMBR_FROM2017
    (average bride age) per region/year.
    """
    target_types = {"NUPT_TOTM_FROM2017", "MAGEMBR_FROM2017"}
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    if not lines:
        return pd.DataFrame(columns=["region", "year", "weddings_total", "marriage_age_mean"])

    records = []
    reader = csv.reader(lines)
    _ = next(reader, None)  # skip header
    for row in reader:
        if len(row) < 8:
            continue
        data_type = row[4]
        if data_type not in target_types:
            continue
        region = _clean_region_name(row[3])
        year = pd.to_numeric(row[6], errors="coerce")
        value = pd.to_numeric(row[7], errors="coerce")
        records.append({"region": region, "year": year, "data_type": data_type, "value": value})

    df = pd.DataFrame.from_records(records)
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")

    if allowed_regions is not None:
        df = df[df["region"].isin(allowed_regions)]
    df = df[~df["region"].isin(DROP_REGIONS)]

    grouped = df.groupby(["region", "year", "data_type"], as_index=False)["value"].mean()
    pivoted = grouped.pivot(index=["region", "year"], columns="data_type", values="value").reset_index()
    pivoted = pivoted.rename(
        columns={
            "NUPT_TOTM_FROM2017": "weddings_total",
            "MAGEMBR_FROM2017": "marriage_age_mean",
        }
    )
    result = pivoted[["region", "year", "weddings_total", "marriage_age_mean"]]
    if years is not None:
        result = result[result["year"].isin(set(pd.to_numeric(years, errors="coerce").dropna()))]
    return result




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
    salary = load_independent_salary(allowed_regions=allowed_regions, years=tidy_dep["year"])
    weddings = load_independent_weddings(allowed_regions=allowed_regions, years=tidy_dep["year"])
    housing = load_independent_housing(allowed_regions=allowed_regions, years=tidy_dep["year"])
    stability = load_independent_stability(allowed_regions=allowed_regions, years=tidy_dep["year"])
    primary_schools = load_independent_primary_schools(allowed_regions=allowed_regions, years=tidy_dep["year"])
    youth_unemployment = load_independent_youth_unemployment(allowed_regions=allowed_regions, years=tidy_dep["year"])
    strangers = load_independent_strangers_percentage(
        path=INDEP_STRANGERS_PATH,
        population_df=demo,
        allowed_regions=allowed_regions,
        years=tidy_dep["year"],
    )

    merged = tidy_dep.merge(demo, on=["region", "year"], how="left")
    merged = merged.merge(welfare, on=["region", "year"], how="left")
    merged = merged.merge(female_emp, on=["region", "year"], how="left")
    merged = merged.merge(salary, on=["region", "year"], how="left")
    merged = merged.merge(weddings, on=["region", "year"], how="left")
    merged = merged.merge(housing, on=["region", "year"], how="left")
    merged = merged.merge(stability, on=["region", "year"], how="left")
    merged = merged.merge(primary_schools, on=["region", "year"], how="left")
    merged = merged.merge(youth_unemployment, on=["region", "year"], how="left")
    merged = merged.merge(strangers, on=["region", "year"], how="left")
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(OUTPUT_PATH, index=False)
    return OUTPUT_PATH


if __name__ == "__main__":
    path = create_dataset_csv()
    print(f"Created dataset (dependent variable) at: {path}")
