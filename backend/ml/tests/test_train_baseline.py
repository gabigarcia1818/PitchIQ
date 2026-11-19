import numpy as np
import pandas as pd

from ml.train_baseline import (
    FEATURES,
    add_features,
    make_models,
    make_risk_label,
    rule_baseline,
    split_by_date,
    split_by_season,
)


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


def test_risk_label_looks_at_next_outing():
    df = pd.DataFrame({
        "pitcher": [1, 1, 1, 1, 2, 2],
        "game_date": pd.to_datetime([
            "2024-04-01", "2024-04-06", "2024-04-11", "2024-04-30", "2024-04-02", "2024-04-07",
        ]),
        "avg_fastball_velo": [95.0, 95.0, 93.0, 95.0, 90.0, 90.0],
    })
    label = make_risk_label(df)
    # game 2 is high risk because game 3 is 2 mph below his average so far,
    # game 3 is high risk because his next outing is 19 days later
    assert label.iloc[:3].tolist() == [0.0, 1.0, 1.0]
    assert label.iloc[4] == 0.0


def test_risk_label_drops_last_outing_of_each_season():
    df = pd.DataFrame({
        "pitcher": [1, 1, 1, 2],
        "game_date": pd.to_datetime(["2024-09-25", "2024-09-30", "2025-03-28", "2024-09-29"]),
        "avg_fastball_velo": [95.0, 95.0, 90.0, 92.0],
    })
    label = make_risk_label(df)
    assert label.iloc[0] == 0.0
    assert np.isnan(label.iloc[1])  # next game is a different season
    assert np.isnan(label.iloc[2])
    assert np.isnan(label.iloc[3])


def test_risk_label_does_not_use_same_game_risk_columns():
    df = pd.DataFrame({
        "pitcher": [1, 1, 1],
        "game_date": pd.to_datetime(["2024-04-01", "2024-04-05", "2024-04-10"]),
        "avg_fastball_velo": [95.0, 95.0, 95.0],
        "pitch_count": [120, 120, 120],
        "days_rest": [np.nan, 2, 2],
        "velo_drop": [np.nan, 3.0, 3.0],
    })
    assert make_risk_label(df).iloc[:2].tolist() == [0.0, 0.0]


def test_rule_baseline_flags_high_pitch_counts():
    pred, _ = rule_baseline(pd.DataFrame({"pitch_count": [80, 95, 110]}))
    assert pred.tolist() == [0, 1, 1]


def test_split_by_season_tests_on_latest_season():
    df = pd.DataFrame({"game_date": pd.to_datetime(["2024-05-01", "2024-09-01", "2025-04-01"])})
    train, test = split_by_season(df)
    assert len(train) == 2 and len(test) == 1
    assert test["game_date"].dt.year.unique().tolist() == [2025]


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