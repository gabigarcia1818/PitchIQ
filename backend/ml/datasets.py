"""
Load the cleaned Statcast datasets as pandas DataFrames ready for scikit-learn.

Run the pipeline first (from backend/):
    python -m ml.collect_statcast --seasons 2024 --combine && python -m ml.clean_statcast
"""

from pathlib import Path

import pandas as pd

DEFAULT_DATA_DIR = Path(__file__).parent / "data"
SAMPLE_PITCHER_GAMES = Path(__file__).parent / "sample" / "pitcher_games_sample.csv"

SETUP_HINT = (
    "Run `python -m ml.collect_statcast --seasons 2024 --combine && python -m ml.clean_statcast` "
    "from backend/ first."
)

# Identifier columns: useful for joins and splits, not as model inputs
PITCHER_GAME_ID_COLUMNS = ["pitcher", "pitcher_name", "game_pk", "game_date", "game_year"]

# Numeric columns that can go straight into a model. NaNs remain where Statcast had no
# reading (e.g. spin) and in days_rest for a pitcher's first outing of each season.
PITCHER_GAME_FEATURES = [
    "pitch_count",
    "batters_faced",
    "innings_pitched_approx",
    "avg_velo",
    "max_velo",
    "min_velo",
    "velo_std",
    "avg_spin",
    "max_spin",
    "avg_extension",
    "avg_release_pos_x",
    "avg_release_pos_z",
    "fastball_pct",
    "avg_fastball_velo",
    "max_fastball_velo",
    "days_rest",
    "throws_left",
]

PITCH_CATEGORICAL_COLUMNS = [
    "game_type",
    "home_team",
    "away_team",
    "inning_topbot",
    "p_throws",
    "stand",
    "pitch_type",
    "pitch_name",
    "description",
    "events",
]


def _find(data_dir, name):
    clean_dir = Path(data_dir) / "clean"
    for ext in ("parquet", "csv"):
        path = clean_dir / f"{name}.{ext}"
        if path.exists():
            return path
    raise FileNotFoundError(f"No cleaned {name} file in {clean_dir}. {SETUP_HINT}")


def _read(path, seasons=None, columns=None):
    path = Path(path)
    if path.suffix == ".csv":
        df = pd.read_csv(path, usecols=columns, parse_dates=["game_date"])
        if seasons is not None:
            df = df[df["game_year"].isin(list(seasons))].reset_index(drop=True)
        return df

    if columns is not None and seasons is not None and "game_year" not in columns:
        columns = list(columns) + ["game_year"]
    filters = [("game_year", "in", list(seasons))] if seasons is not None else None
    return pd.read_parquet(path, columns=columns, filters=filters)


def _model_friendly(df, categorical_columns):
    """Use plain numpy dtypes: whole numbers as int64 (float64 if they have gaps), text as category."""
    df = df.copy()
    for col in df.columns:
        dtype = df[col].dtype
        if col in categorical_columns:
            df[col] = df[col].astype("category")
        elif pd.api.types.is_integer_dtype(dtype) or pd.api.types.is_float_dtype(dtype):
            if df[col].isna().any() or pd.api.types.is_float_dtype(dtype):
                df[col] = df[col].astype("float64")
            else:
                df[col] = df[col].astype("int64")
        elif pd.api.types.is_bool_dtype(dtype):
            df[col] = df[col].astype("int64")
    return df


def load_pitches(seasons=None, columns=None, data_dir=DEFAULT_DATA_DIR):
    """Return cleaned pitch-level data (one row per pitch).

    seasons: optional list of years, e.g. [2024]. columns: optional subset of columns to read,
    which keeps memory down for multi-season loads.
    """
    df = _read(_find(data_dir, "pitches"), seasons=seasons, columns=columns)
    return _model_friendly(df, PITCH_CATEGORICAL_COLUMNS)


def load_pitcher_games(seasons=None, data_dir=DEFAULT_DATA_DIR, sample=False):
    """Return one row per pitcher per game with numeric features in PITCHER_GAME_FEATURES.

    sample=True loads the small committed sample (2024 season) so code can be tried
    without downloading anything.
    """
    path = SAMPLE_PITCHER_GAMES if sample else _find(data_dir, "pitcher_games")
    df = _read(path, seasons=seasons)
    df = _model_friendly(df, ["p_throws"])
    df["throws_left"] = (df["p_throws"] == "L").astype("int64")
    return df
