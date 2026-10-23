"""
Clean historical Statcast pitch data for model training.
"""

import argparse
import logging
from pathlib import Path
import re
import sys
import pandas as pd

logger = logging.getLogger(__name__)

KEEP_COLUMNS = [
    "pitcher",
    "pitcher_name",
    "game_pk",
    "game_date",
    "game_year",
    "game_type",
    "home_team",
    "away_team",
    "inning",
    "inning_topbot",
    "at_bat_number",
    "pitch_number",
    "balls",
    "strikes",
    "outs_when_up",
    "p_throws",
    "stand",
    "pitch_type",
    "pitch_name",
    "release_speed",
    "effective_speed",
    "release_spin_rate",
    "spin_axis",
    "release_pos_x",
    "release_pos_y",
    "release_pos_z",
    "release_extension",
    "pfx_x",
    "pfx_z",
    "plate_x",
    "plate_z",
    "zone",
    "description",
    "events",
    "n_thruorder_pitcher",
    "pitcher_days_since_prev_game",
    "arm_angle",
]

REQUIRED_COLUMNS = [
    "pitcher",
    "game_pk",
    "game_date",
    "at_bat_number",
    "pitch_number",
    "pitch_type",
    "release_speed",
]


def clean_pitches(df):
    """Clean raw Statcast pitch data by filtering, normalizing types, and deduplicating."""
    df = df.copy()

    if "player_name" in df.columns and "pitcher_name" not in df.columns:
        df = df.rename(columns={"player_name": "pitcher_name"})

    missing_req = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_req:
        raise ValueError(f"Missing required columns: {missing_req}")

    has_game_type = "game_type" in df.columns
    for c in KEEP_COLUMNS:
        if c not in df.columns:
            df[c] = pd.NA

    # Filter regular season (only when the input actually has game_type)
    if has_game_type:
        before = len(df)
        df = df[df["game_type"] == "R"]
        dropped = before - len(df)
        if dropped > 0:
            logger.info("Dropped %d rows: non-regular season (game_type != 'R')", dropped)

    # Filter null pitch_type
    before = len(df)
    df = df[df["pitch_type"].notna()]
    dropped = before - len(df)
    if dropped > 0:
        logger.info("Dropped %d rows: null pitch_type", dropped)

    # Filter non-pitch pitch_types
    non_pitch_types = {"PO", "IN", "AB", "UN"}
    before = len(df)
    df = df[~df["pitch_type"].astype(str).str.upper().isin(non_pitch_types)]
    dropped = before - len(df)
    if dropped > 0:
        logger.info("Dropped %d rows: non-pitch pitch_type (PO, IN, AB, UN)", dropped)

    # Filter non-pitch descriptions
    non_pitch_desc = {"pickoff_1b", "pickoff_2b", "pickoff_3b", "automatic_ball", "automatic_strike"}
    if "description" in df.columns:
        before = len(df)
        df = df[~df["description"].isin(non_pitch_desc)]
        dropped = before - len(df)
        if dropped > 0:
            logger.info("Dropped %d rows: non-pitch description", dropped)

    # Filter nulls in required columns
    before = len(df)
    df = df.dropna(subset=REQUIRED_COLUMNS)
    dropped = before - len(df)
    if dropped > 0:
        logger.info("Dropped %d rows: null values in required columns", dropped)

    # Range checks
    rs = pd.to_numeric(df["release_speed"], errors="coerce")
    before = len(df)
    valid_rs = (rs >= 30) & (rs <= 110)
    df = df[valid_rs]
    dropped = before - len(df)
    if dropped > 0:
        logger.info("Dropped %d rows: release_speed outside 30-110 mph", dropped)

    if "release_spin_rate" in df.columns:
        spin = pd.to_numeric(df["release_spin_rate"], errors="coerce")
        before = len(df)
        valid_spin = spin.isna() | ((spin >= 0) & (spin <= 4000))
        df = df[valid_spin]
        dropped = before - len(df)
        if dropped > 0:
            logger.info("Dropped %d rows: release_spin_rate outside 0-4000", dropped)

    if "balls" in df.columns:
        b = pd.to_numeric(df["balls"], errors="coerce")
        before = len(df)
        valid_b = b.isna() | ((b >= 0) & (b <= 3))
        df = df[valid_b]
        dropped = before - len(df)
        if dropped > 0:
            logger.info("Dropped %d rows: balls outside 0-3", dropped)

    if "strikes" in df.columns:
        s = pd.to_numeric(df["strikes"], errors="coerce")
        before = len(df)
        valid_s = s.isna() | ((s >= 0) & (s <= 2))
        df = df[valid_s]
        dropped = before - len(df)
        if dropped > 0:
            logger.info("Dropped %d rows: strikes outside 0-2", dropped)

    if "pitch_number" in df.columns:
        pn = pd.to_numeric(df["pitch_number"], errors="coerce")
        before = len(df)
        valid_pn = pn.isna() | (pn >= 1)
        df = df[valid_pn]
        dropped = before - len(df)
        if dropped > 0:
            logger.info("Dropped %d rows: pitch_number < 1", dropped)

    # Normalize types
    df["game_date"] = pd.to_datetime(df["game_date"]).dt.normalize()
    df["game_year"] = df["game_year"].fillna(df["game_date"].dt.year)

    int_cols = ["pitcher", "game_pk", "game_year", "at_bat_number", "pitch_number", "balls", "strikes", "outs_when_up", "inning", "zone"]
    for col in int_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    float_cols = ["release_speed", "effective_speed", "release_spin_rate", "spin_axis", "release_pos_x", "release_pos_y", "release_pos_z", "release_extension", "pfx_x", "pfx_z", "plate_x", "plate_z", "arm_angle", "n_thruorder_pitcher", "pitcher_days_since_prev_game"]
    for col in float_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("float64")

    for col in df.columns:
        if col not in int_cols and col not in float_cols and col != "game_date":
            df[col] = df[col].astype("string").str.strip()

    if "pitch_type" in df.columns:
        df["pitch_type"] = df["pitch_type"].str.upper()

    # Deduplicate
    df = df.drop_duplicates(subset=["game_pk", "at_bat_number", "pitch_number"], keep="first")

    # Sort
    df = df.sort_values(["game_date", "game_pk", "at_bat_number", "pitch_number"]).reset_index(drop=True)

    # Keep only KEEP_COLUMNS in correct order
    cols_to_keep = [c for c in KEEP_COLUMNS if c in df.columns]
    df = df[cols_to_keep]

    return df


def validate_pitches(df):
    """Validate cleaned pitch data against schema and business rules."""
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            raise ValueError(f"Required column '{col}' is missing.")
        if df[col].isna().any():
            raise ValueError(f"Required column '{col}' contains null values.")

    if df.duplicated(subset=["game_pk", "at_bat_number", "pitch_number"]).any():
        raise ValueError("Duplicate keys found for (game_pk, at_bat_number, pitch_number).")

    if "release_speed" in df.columns:
        rs = pd.to_numeric(df["release_speed"], errors="coerce")
        if ((rs < 30) | (rs > 110)).any():
            raise ValueError("release_speed outside valid range [30, 110].")

    if "release_spin_rate" in df.columns:
        spin = pd.to_numeric(df["release_spin_rate"], errors="coerce")
        valid = spin.isna() | ((spin >= 0) & (spin <= 4000))
        if not valid.all():
            raise ValueError("release_spin_rate outside valid range [0, 4000].")

    if "balls" in df.columns:
        b = pd.to_numeric(df["balls"], errors="coerce")
        valid_b = b.isna() | ((b >= 0) & (b <= 3))
        if not valid_b.all():
            raise ValueError("balls outside valid range [0, 3].")

    if "strikes" in df.columns:
        s = pd.to_numeric(df["strikes"], errors="coerce")
        valid_s = s.isna() | ((s >= 0) & (s <= 2))
        if not valid_s.all():
            raise ValueError("strikes outside valid range [0, 2].")

    if "pitch_number" in df.columns:
        pn = pd.to_numeric(df["pitch_number"], errors="coerce")
        if (pn < 1).any():
            raise ValueError("pitch_number must be >= 1.")


OUTING_COLUMNS = [
    "pitcher", "pitcher_name", "game_pk", "game_date", "game_year", "p_throws",
    "pitch_count", "batters_faced", "innings_pitched_approx", "avg_velo", "max_velo",
    "min_velo", "velo_std", "avg_spin", "max_spin", "avg_extension", "avg_release_pos_x",
    "avg_release_pos_z", "fastball_pct", "avg_fastball_velo", "max_fastball_velo", "days_rest",
]

FASTBALL_TYPES = ["FF", "SI", "FC"]


def aggregate_outings(df):
    """Aggregate pitch-level data into one row per pitcher per game."""
    if df.empty:
        return pd.DataFrame(columns=OUTING_COLUMNS)

    df = df.copy()
    for col in ["release_spin_rate", "release_extension", "release_pos_x", "release_pos_z"]:
        if col not in df.columns:
            df[col] = float("nan")
    for col in ["pitcher_name", "p_throws", "game_year"]:
        if col not in df.columns:
            df[col] = pd.NA

    is_fb = df["pitch_type"].isin(FASTBALL_TYPES).fillna(False).astype(bool)
    df["_is_fb"] = is_fb.astype("int64")
    df["_fb_velo"] = df["release_speed"].where(is_fb)

    grouped = df.groupby(["pitcher", "game_pk"], sort=False)
    outings = grouped.agg(
        pitcher_name=("pitcher_name", "first"),
        game_date=("game_date", "first"),
        game_year=("game_year", "first"),
        p_throws=("p_throws", "first"),
        pitch_count=("pitch_number", "size"),
        batters_faced=("at_bat_number", "nunique"),
        innings_pitched_approx=("inning", "nunique"),
        avg_velo=("release_speed", "mean"),
        max_velo=("release_speed", "max"),
        min_velo=("release_speed", "min"),
        velo_std=("release_speed", "std"),
        avg_spin=("release_spin_rate", "mean"),
        max_spin=("release_spin_rate", "max"),
        avg_extension=("release_extension", "mean"),
        avg_release_pos_x=("release_pos_x", "mean"),
        avg_release_pos_z=("release_pos_z", "mean"),
        fb_count=("_is_fb", "sum"),
        avg_fastball_velo=("_fb_velo", "mean"),
        max_fastball_velo=("_fb_velo", "max"),
    ).reset_index()

    # A single pitch has no spread; report 0 instead of NaN
    single = outings["pitch_count"] == 1
    outings.loc[single, "velo_std"] = 0.0

    outings["fastball_pct"] = outings["fb_count"] / outings["pitch_count"]
    outings = outings.drop(columns="fb_count")

    missing_year = outings["game_year"].isna()
    if missing_year.any():
        outings.loc[missing_year, "game_year"] = outings.loc[missing_year, "game_date"].dt.year

    outings = outings.sort_values(["pitcher", "game_date", "game_pk"]).reset_index(drop=True)

    # Days since the pitcher's previous outing in the same season.
    # The first outing of each season is NaN so the offseason gap is not counted as rest.
    outings["days_rest"] = (
        outings.groupby(["pitcher", "game_year"])["game_date"].diff().dt.days.astype("float64")
    )

    for col in ["pitcher", "game_pk", "game_year", "pitch_count", "batters_faced", "innings_pitched_approx"]:
        outings[col] = outings[col].astype("int64")
    for col in ["avg_velo", "max_velo", "min_velo", "velo_std", "avg_spin", "max_spin",
                "avg_extension", "avg_release_pos_x", "avg_release_pos_z", "fastball_pct",
                "avg_fastball_velo", "max_fastball_velo"]:
        outings[col] = outings[col].astype("float64")

    return outings[OUTING_COLUMNS]


def _is_combined_file(path):
    return "_combined" in path.name or re.match(r"statcast_\d{4}\.parquet$", path.name) is not None


def raw_chunk_files(raw_dir):
    """List raw Statcast chunk files, skipping combined files that repeat chunk rows."""
    raw_dir = Path(raw_dir)
    if not raw_dir.exists():
        return []
    return [f for f in sorted(raw_dir.glob("statcast_*.parquet")) if not _is_combined_file(f)]


def read_raw_file(path):
    """Read one raw file, keeping only the columns the cleaner uses."""
    path = Path(path)
    wanted = set(KEEP_COLUMNS) | {"player_name"}
    if path.suffix == ".csv":
        return pd.read_csv(path, usecols=lambda c: c in wanted, low_memory=False)
    import pyarrow.parquet as pq

    available = pq.read_schema(path).names
    return pd.read_parquet(path, columns=[c for c in available if c in wanted])


def load_raw(raw_dir):
    """Load all raw Statcast chunk files from a directory (only the needed columns).

    Combined files (statcast_<year>.parquet and *_combined.parquet) are skipped
    because they repeat the rows already in the chunk files.
    """
    chunk_files = raw_chunk_files(raw_dir)
    if not chunk_files:
        logger.warning("No raw Statcast chunk files found in %s", raw_dir)
        return pd.DataFrame()

    logger.info("Loading %d raw chunk files from %s", len(chunk_files), raw_dir)
    return pd.concat([read_raw_file(f) for f in chunk_files], ignore_index=True)


def clean_files(paths):
    """Clean raw files one at a time so memory stays close to the size of the cleaned output."""
    cleaned = []
    raw_rows = 0
    for path in paths:
        raw = read_raw_file(path)
        raw_rows += len(raw)
        if raw.empty:
            continue
        cleaned.append(clean_pitches(raw))
        del raw

    if not cleaned:
        return pd.DataFrame(), raw_rows

    df = pd.concat(cleaned, ignore_index=True)
    # Chunks can overlap if different date ranges were collected, so dedupe across files too
    df = df.drop_duplicates(subset=["game_pk", "at_bat_number", "pitch_number"], keep="first")
    df = df.sort_values(["game_date", "game_pk", "at_bat_number", "pitch_number"]).reset_index(drop=True)
    return df, raw_rows


def main(argv=None):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description="Clean historical Statcast pitch data.")
    parser.add_argument("--input", nargs="+", help="Input files (Parquet or CSV)")
    parser.add_argument("--data-dir", type=str, default=str(Path(__file__).parent / "data"), help="Data directory")
    parser.add_argument("--format", choices=["parquet", "csv"], default="parquet", help="Output format")

    args = parser.parse_args(argv)
    data_dir = Path(args.data_dir)
    raw_dir = data_dir / "raw"
    clean_dir = data_dir / "clean"

    if args.input:
        paths = [Path(p) for p in args.input]
        for p in paths:
            if not p.exists():
                logger.error("Input file not found: %s", p)
                sys.exit(1)
    else:
        paths = raw_chunk_files(raw_dir)
        if not paths:
            logger.warning("No raw Statcast chunk files found in %s", raw_dir)

    logger.info("Cleaning %d raw files", len(paths))
    cleaned_df, raw_rows = clean_files(paths)

    if cleaned_df.empty:
        logger.error("No input data found to clean.")
        sys.exit(1)

    logger.info("Loaded raw data with %d rows", raw_rows)
    validate_pitches(cleaned_df)
    logger.info("Cleaned pitches: %d rows", len(cleaned_df))

    pitcher_games_df = aggregate_outings(cleaned_df)
    logger.info("Aggregated pitcher games: %d rows", len(pitcher_games_df))

    clean_dir.mkdir(parents=True, exist_ok=True)
    ext = "parquet" if args.format == "parquet" else "csv"
    pitches_path = clean_dir / f"pitches.{ext}"
    outings_path = clean_dir / f"pitcher_games.{ext}"

    if ext == "parquet":
        cleaned_df.to_parquet(pitches_path, index=False)
        pitcher_games_df.to_parquet(outings_path, index=False)
    else:
        cleaned_df.to_csv(pitches_path, index=False)
        pitcher_games_df.to_csv(outings_path, index=False)

    logger.info("Wrote cleaned pitches to %s and pitcher games to %s", pitches_path, outings_path)


if __name__ == "__main__":
    main()
