import numpy as np
import pandas as pd

from ml.train_baseline import FEATURES, add_features, make_models, make_risk_label, split_by_date


def test_velo_drop_uses_only_earlier_games():
    df = pd.DataFrame({
        "pitcher": [1, 1, 1, 2],
        "game_date": pd.to_datetime(["2024-04-01", "2024-04-06", "2024-04-11", "2024-04-02"]),
        "avg_fastball_velo": [95.0, 95.0, 92.0, 90.0],
    })
    out = add_features(df)
    p1 = out[out["pitcher"] == 1].reset_index(drop=True)
    assert np.isnan(p1.loc[0, "velo_drop"])  # no earlier game
    assert p1.loc[1, "velo_drop"] == 0.0
    assert p1.loc[2, "velo_drop"] == 3.0  # 95 - 92
    assert np.isnan(out[out["pitcher"] == 2].iloc[0]["velo_drop"])


def test_risk_label_needs_two_of_three_flags():
    df = pd.DataFrame({
        "pitch_count": [100, 100, 80, 80, 100],
        "days_rest": [2, 5, 2, 5, np.nan],
        "velo_drop": [0.0, 0.0, 2.0, 0.0, 2.0],
    })
    assert make_risk_label(df).tolist() == [1, 0, 1, 0, 1]


def test_split_by_date_trains_on_earlier_games():
    df = pd.DataFrame({"game_date": pd.date_range("2024-04-01", periods=10)})
    train, test = split_by_date(df)
    assert len(train) == 8 and len(test) == 2
    assert train["game_date"].max() < test["game_date"].min()


def test_models_fit_and_predict_with_missing_values():
    rng = np.random.default_rng(0)
    X = pd.DataFrame(rng.normal(size=(200, len(FEATURES))), columns=FEATURES)
    X.iloc[::10, 0] = np.nan  # missing values are imputed
    y = pd.Series(rng.integers(0, 2, size=200))
    for model in make_models().values():
        model.fit(X, y)
        assert len(model.predict(X)) == 200