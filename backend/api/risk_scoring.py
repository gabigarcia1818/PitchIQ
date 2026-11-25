from decimal import Decimal
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from django.conf import settings
from django.db.models import Avg

from .models import PitcherOuting, PitcherRiskAssessment

@lru_cache(maxsize=1)
def load_baseline():
    model_path = Path(settings.BASE_DIR) / "ml" / "models" / "baseline_risk.joblib"
    return joblib.load(model_path)

def recalculate_risk(outing):
    bundle = load_baseline()
    prior_fastball_mean = (
        PitcherOuting.objects.filter(
            pitcher=outing.pitcher,
            outing_type="game",
            date__lt=outing.date,
        )
        .exclude(avg_fastball_velo__isnull=True)
        .aggregate(mean=Avg("avg_fastball_velo"))["mean"]
    )

    values = {
        "pitch_count": outing.pitch_count,
        "batters_faced": outing.batters_faced,
        "innings_pitched_approx": outing.innings_pitched_approx,
        "avg_velo": outing.avg_velocity,
        "max_velo": outing.max_velo,
        "min_velo": outing.min_velo,
        "velo_std": outing.velo_std,
        "avg_spin": outing.avg_spin,
        "max_spin": outing.max_spin,
        "avg_extension": outing.avg_extension,
        "avg_release_pos_x": outing.avg_release_pos_x,
        "avg_release_pos_z": outing.avg_release_pos_z,
        "fastball_pct": outing.fastball_pct,
        "avg_fastball_velo": outing.avg_fastball_velo,
        "max_fastball_velo": outing.max_fastball_velo,
        "days_rest": outing.rest_days,
        "throws_left": (
            int(outing.pitcher.throws_left)
            if outing.pitcher.throws_left is not None
            else np.nan
        ),
        "velo_drop": (
            float(prior_fastball_mean - outing.avg_fastball_velo)
            if prior_fastball_mean is not None and outing.avg_fastball_velo is not None
            else np.nan
        ),
    }

    features = bundle["features"]
    model_input = pd.DataFrame(
        [{feature: values.get(feature, np.nan) for feature in features}],
        columns=features,
    )

    model = bundle["model"]
    positive_class_index = list(model.classes_).index(1)
    probability = model.predict_proba(model_input)[0][positive_class_index]

    assessment, _ = PitcherRiskAssessment.objects.update_or_create(
        outing=outing,
        defaults={
            "probability": Decimal(str(probability)),
            "model_name": bundle["name"],
        },
    )
    return assessment