import argparse
import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ml.datasets import PITCHER_GAME_FEATURES, load_pitcher_games

MODEL_DIR = Path(__file__).parent / "models"

# A game is high risk if at least 2 of these 3 conditions are true
PITCH_COUNT_LIMIT = 95
REST_DAYS_LIMIT = 3
VELO_DROP_LIMIT = 1.5  # mph below the pitcher's own earlier average fastball velo

# the model learns from the original game stats and velo drop
FEATURES = PITCHER_GAME_FEATURES + ["velo_drop"]


def add_features(df):
    # velo_drop = how much slower this game's fastball was than the pitcher's average
    df = df.sort_values(["pitcher", "game_date"]).reset_index(drop=True)
    prior_mean = df.groupby("pitcher")["avg_fastball_velo"].transform(
        lambda s: s.shift(1).expanding().mean()
    )
    df["velo_drop"] = prior_mean - df["avg_fastball_velo"]
    return df


def make_risk_label(df):
    # Count how many of the 3 risk conditions are true if 2 or more = high risk 
    flags = (
        (df["pitch_count"] >= PITCH_COUNT_LIMIT).astype(int)
        + (df["days_rest"] <= REST_DAYS_LIMIT).astype(int)
        + (df["velo_drop"] >= VELO_DROP_LIMIT).astype(int)
    )
    return (flags >= 2).astype(int)


def split_by_date(df, train_fraction=0.8):

    cutoff = df["game_date"].sort_values().iloc[int(len(df) * train_fraction)]
    return df[df["game_date"] < cutoff], df[df["game_date"] >= cutoff]


def make_models():
    def pipe(clf):
        return Pipeline([
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
            ("clf", clf),
        ])

    return {
        "dummy_majority": pipe(DummyClassifier(strategy="most_frequent")), # dummy = always predicts "low risk" (the minimum to beat)
        "logistic_regression": pipe(LogisticRegression(max_iter=1000, class_weight="balanced")),
        "random_forest": pipe(
            RandomForestClassifier(n_estimators=200, class_weight="balanced", random_state=42)
        ),
    }


def evaluate(model, X_test, y_test):
    pred = model.predict(X_test)
    result = {
        "accuracy": accuracy_score(y_test, pred),
        "precision": precision_score(y_test, pred, zero_division=0),
        "recall": recall_score(y_test, pred, zero_division=0),
        "f1": f1_score(y_test, pred, zero_division=0),
    }
    if y_test.nunique() == 2:
        result["roc_auc"] = roc_auc_score(y_test, model.predict_proba(X_test)[:, 1])
    return {k: round(float(v), 4) for k, v in result.items()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", action="store_true", help="use the 500-row committed sample")
    parser.add_argument("--seasons", nargs="+", type=int, default=None)
    args = parser.parse_args()

    games = load_pitcher_games(seasons=args.seasons, sample=args.sample)
    games = games[games["avg_velo"] >= 75]  # drop position players pitching
    games = add_features(games)
    games["high_risk"] = make_risk_label(games)

    print(f"Rows: {len(games)}  high-risk share: {games['high_risk'].mean():.1%}")
    train, test = split_by_date(games)
    X_train, y_train = train[FEATURES], train["high_risk"]
    X_test, y_test = test[FEATURES], test["high_risk"]
    if y_train.nunique() < 2:
        raise SystemExit("Training data has one class only; lower the rule thresholds or load more seasons.")

    results, fitted = {}, {}
    for name, model in make_models().items():
        model.fit(X_train, y_train)
        fitted[name] = model
        results[name] = evaluate(model, X_test, y_test)
        print(name, results[name])

    best = max((n for n in results if n != "dummy_majority"), key=lambda n: results[n]["f1"])
    MODEL_DIR.mkdir(exist_ok=True)
    # Save the best model so Django can load it later
    joblib.dump(
        {"model": fitted[best], "features": FEATURES, "name": best},
        MODEL_DIR / "baseline_risk.joblib",
    )
    with open(MODEL_DIR / "baseline_metrics.json", "w") as f:
        json.dump({"best": best, "train_rows": len(train), "test_rows": len(test),
                   "results": results}, f, indent=2)
    print(f"Saved {best} to {MODEL_DIR / 'baseline_risk.joblib'}")


if __name__ == "__main__":
    main()