from decimal import Decimal

from .models import HighRiskAlert, PitcherRiskAssessment

HIGH_RISK_THRESHOLD = Decimal("0.5")


def _as_decimal(value):
    if value is None:
        return None
    return Decimal(str(value))


def is_high_risk(probability):
    probability = _as_decimal(probability)
    return probability is not None and probability >= HIGH_RISK_THRESHOLD


def _latest_other_probability(assessment):
    prior = (
        PitcherRiskAssessment.objects.filter(outing__pitcher=assessment.outing.pitcher)
        .exclude(pk=assessment.pk)
        .order_by("-outing__date", "-calculated_at")
        .first()
    )
    return prior.probability if prior is not None else None


def maybe_create_high_risk_alert(assessment, previous_probability=None):
    """Create an alert only when a pitcher's risk score crosses the high-risk threshold."""
    if not is_high_risk(assessment.probability):
        return None

    if previous_probability is None:
        previous_probability = _latest_other_probability(assessment)

    if is_high_risk(previous_probability):
        return None

    return HighRiskAlert.objects.create(
        pitcher=assessment.outing.pitcher,
        risk_assessment=assessment,
        risk_score=assessment.probability,
    )
