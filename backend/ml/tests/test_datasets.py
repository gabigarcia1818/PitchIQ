import pandas as pd
import pytest

from ml.clean_statcast import main
from ml.datasets import PITCHER_GAME_FEATURES, load_pitcher_games, load_pitches
from ml.tests.test_clean_statcast import sample_raw_df  # noqa: F401


@pytest.fixture
def data_dir(tmp_path, sample_raw_df):  # noqa: F811
    raw_dir = tmp_path / "data" / "raw"
    raw_dir.mkdir(parents=True)
    df = sample_raw_df.copy()
    df["game_year"] = 2024
    df.to_parquet(raw_dir / "statcast_2024-04-01_2024-04-07.parquet", index=False)
    main(["--data-dir", str(tmp_path / "data")])
    return tmp_path / "data"


def test_load_pitcher_games_is_numeric(data_dir):
    games = load_pitcher_games(data_dir=data_dir)
    assert len(games) > 0
    X = games[PITCHER_GAME_FEATURES]
    assert all(pd.api.types.is_numeric_dtype(t) for t in X.dtypes)
    assert set(games["throws_left"]) <= {0, 1}


def test_load_pitches_filters_and_types(data_dir):
    pitches = load_pitches(seasons=[2024], columns=["pitcher", "pitch_type", "balls"], data_dir=data_dir)
    assert len(pitches) > 0
    assert isinstance(pitches["pitch_type"].dtype, pd.CategoricalDtype)
    assert pitches["balls"].dtype == "int64"
    assert len(load_pitches(seasons=[2023], data_dir=data_dir)) == 0


def test_missing_data_has_setup_hint(tmp_path):
    with pytest.raises(FileNotFoundError, match="collect_statcast"):
        load_pitcher_games(data_dir=tmp_path)


def test_sample_fits_sklearn():
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    games = load_pitcher_games(sample=True)
    assert len(games) == 500
    y = (games["pitch_count"] >= 80).astype(int)
    model = make_pipeline(SimpleImputer(), StandardScaler(), LogisticRegression(max_iter=500))
    model.fit(games[PITCHER_GAME_FEATURES], y)
