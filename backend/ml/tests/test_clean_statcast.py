import pytest
import pandas as pd
from pathlib import Path
from ml.clean_statcast import (
    clean_pitches,
    validate_pitches,
    aggregate_outings,
    main,
)


@pytest.fixture
def sample_raw_df():
    data = {
        "pitcher": [123, 123, 123, 123, 123, 123, 456, 456, 123, 123],
        "player_name": ["Pitcher A", "Pitcher A", "Pitcher A", "Pitcher A", "Pitcher A", "Pitcher A", "Pitcher B", "Pitcher B", "Pitcher A", "Pitcher A"],
        "game_pk": [101, 101, 101, 101, 101, 101, 102, 102, 103, 103],
        "game_date": ["2024-04-01", "2024-04-01", "2024-04-01", "2024-04-01", "2024-04-01", "2024-04-01", "2024-04-02", "2024-04-02", "2024-04-05", "2024-04-05"],
        "game_type": ["R", "R", "R", "R", "P", "R", "R", "R", "R", "R"],
        "at_bat_number": [1, 1, 1, 2, 2, 2, 1, 1, 1, 1],
        "pitch_number": [1, 1, 2, 1, 1, 1, 1, 1, 1, 1],
        "pitch_type": ["FF", "FF", "PO", "SL", "FF", None, "SI", "IN", "FF", "CH"],
        "release_speed": [95.0, 95.0, 85.0, 82.0, 94.0, 90.0, 92.0, 0.0, 96.0, 88.0],
        "release_spin_rate": [2200, 2200, 2100, 2400, 2300, 2150, 2100, 2000, 2250, 1900],
        "balls": ["1", "1", "0", "2", "0", "0", "3", "1", "0", "2"],
        "strikes": ["0", "0", "0", "1", "0", "0", "2", "0", "1", "1"],
        "inning": [1, 1, 1, 1, 1, 1, 2, 2, 1, 1],
        "p_throws": ["R", "R", "R", "R", "R", "R", "L", "L", "R", "R"],
    }
    return pd.DataFrame(data)


def test_clean_pitches_removes_bad_rows(sample_raw_df):
    cleaned = clean_pitches(sample_raw_df)
    assert not (cleaned["game_type"] == "P").any()
    assert not cleaned["pitch_type"].isin(["PO", "IN", "AB", "UN"]).any()
    assert cleaned["pitch_type"].notna().all()
    assert (cleaned["release_speed"] >= 30).all()


def test_clean_pitches_normalizes_dtypes(sample_raw_df):
    cleaned = clean_pitches(sample_raw_df)
    assert pd.api.types.is_datetime64_any_dtype(cleaned["game_date"])
    assert cleaned["balls"].dtype == "Int64"
    assert cleaned["strikes"].dtype == "Int64"
    assert cleaned["pitch_number"].dtype == "Int64"
    assert cleaned["release_speed"].dtype == "float64"
    assert cleaned["pitcher_name"].dtype == "string"


def test_clean_pitches_deduplicates(sample_raw_df):
    cleaned = clean_pitches(sample_raw_df)
    dups = cleaned.duplicated(subset=["game_pk", "at_bat_number", "pitch_number"])
    assert not dups.any()


def test_validate_pitches_success_and_raise(sample_raw_df):
    cleaned = clean_pitches(sample_raw_df)
    validate_pitches(cleaned)

    bad_df = cleaned.copy()
    bad_df.loc[0, "release_speed"] = None
    with pytest.raises(ValueError):
        validate_pitches(bad_df)


def test_missing_required_column_raises():
    df = pd.DataFrame({"pitcher": [123], "game_pk": [101]})
    with pytest.raises(ValueError):
        clean_pitches(df)


def test_aggregate_outings(sample_raw_df):
    cleaned = clean_pitches(sample_raw_df)
    outings = aggregate_outings(cleaned)
    assert not outings.empty
    assert "pitch_count" in outings.columns
    assert "avg_velo" in outings.columns
    assert "fastball_pct" in outings.columns
    assert "days_rest" in outings.columns

    p123_outings = outings[outings["pitcher"] == 123]
    assert len(p123_outings) == 2
    assert pd.isna(p123_outings.iloc[0]["days_rest"])
    assert p123_outings.iloc[1]["days_rest"] == 4.0


def test_main_end_to_end(tmp_path, sample_raw_df):
    data_dir = tmp_path / "data"
    raw_dir = data_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    parquet_path = raw_dir / "statcast_test.parquet"
    sample_raw_df.to_parquet(parquet_path, index=False)

    main(["--data-dir", str(data_dir)])

    clean_dir = data_dir / "clean"
    assert (clean_dir / "pitches.parquet").exists()
    assert (clean_dir / "pitcher_games.parquet").exists()

    pitches_loaded = pd.read_parquet(clean_dir / "pitches.parquet")
    outings_loaded = pd.read_parquet(clean_dir / "pitcher_games.parquet")
    assert len(pitches_loaded) > 0
    assert len(outings_loaded) > 0


def test_clean_pitches_keeps_rows_without_game_type(sample_raw_df):
    df = sample_raw_df.drop(columns=["game_type"])
    cleaned = clean_pitches(df)
    assert len(cleaned) > 0


def test_aggregate_single_pitch_and_season_rest():
    df = pd.DataFrame({
        "pitcher": [1, 1, 1, 1],
        "pitcher_name": ["A"] * 4,
        "game_pk": [10, 11, 11, 12],
        "game_date": pd.to_datetime(["2023-09-25", "2023-09-30", "2023-09-30", "2024-03-28"]),
        "game_year": [2023, 2023, 2023, 2024],
        "p_throws": ["L"] * 4,
        "at_bat_number": [1, 1, 2, 1],
        "pitch_number": [1, 1, 1, 1],
        "inning": [1, 1, 2, 1],
        "pitch_type": ["FF", "SL", "FF", "CH"],
        "release_speed": [95.0, 85.0, 96.0, 84.0],
    })
    outings = aggregate_outings(df)
    assert list(outings["game_pk"]) == [10, 11, 12]
    assert outings.loc[0, "velo_std"] == 0.0
    assert outings.loc[1, "fastball_pct"] == 0.5
    assert outings.loc[1, "avg_fastball_velo"] == 96.0
    assert outings.loc[1, "days_rest"] == 5.0
    # First outing of a new season does not count the offseason as rest
    assert pd.isna(outings.loc[2, "days_rest"])
    assert pd.isna(outings.loc[2, "avg_fastball_velo"])


def test_main_dedupes_overlapping_chunks(tmp_path, sample_raw_df):
    raw_dir = tmp_path / "data" / "raw"
    raw_dir.mkdir(parents=True)
    sample_raw_df.to_parquet(raw_dir / "statcast_2024-04-01_2024-04-07.parquet", index=False)
    sample_raw_df.to_parquet(raw_dir / "statcast_2024-04-01_2024-04-02.parquet", index=False)
    sample_raw_df.to_parquet(raw_dir / "statcast_2024.parquet", index=False)

    main(["--data-dir", str(tmp_path / "data")])

    once = clean_pitches(sample_raw_df)
    pitches = pd.read_parquet(tmp_path / "data" / "clean" / "pitches.parquet")
    assert len(pitches) == len(once)
