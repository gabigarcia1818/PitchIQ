from decimal import Decimal
from unittest.mock import patch

from rest_framework.test import APITestCase

from api.alerts import HIGH_RISK_THRESHOLD, maybe_create_high_risk_alert
from api.models import HighRiskAlert, OutingType, PitcherOuting, PitcherRiskAssessment, Role, User


def _make_assessment(pitcher, date, probability, outing_kwargs=None):
    payload = {
        "pitcher": pitcher,
        "outing_type": OutingType.GAME,
        "date": date,
        "pitch_count": 80,
        "avg_velocity": "92.00",
        "rest_days": 4,
    }
    if outing_kwargs:
        payload.update(outing_kwargs)
    outing = PitcherOuting.objects.create(**payload)
    assessment = PitcherRiskAssessment.objects.create(
        outing=outing,
        probability=Decimal(str(probability)),
        model_name="logistic_regression",
    )
    return outing, assessment


class HighRiskAlertLogicTests(APITestCase):
    def setUp(self):
        self.pitcher = User.objects.create_user(
            username="alert_pitcher",
            password="test-password",
            role=Role.PITCHER,
        )

    def test_crossing_threshold_creates_alert_tied_to_pitcher_and_score(self):
        _outing, assessment = _make_assessment(self.pitcher, "2026-11-01", "0.81")

        alert = maybe_create_high_risk_alert(assessment)

        self.assertIsNotNone(alert)
        self.assertEqual(HighRiskAlert.objects.count(), 1)
        self.assertEqual(alert.pitcher, self.pitcher)
        self.assertEqual(alert.risk_assessment, assessment)
        self.assertEqual(alert.risk_score, Decimal("0.81"))

    def test_score_below_threshold_does_not_create_alert(self):
        _outing, assessment = _make_assessment(self.pitcher, "2026-11-01", "0.49")

        alert = maybe_create_high_risk_alert(assessment)

        self.assertIsNone(alert)
        self.assertEqual(HighRiskAlert.objects.count(), 0)

    def test_staying_above_threshold_does_not_create_another_alert(self):
        _outing, first = _make_assessment(self.pitcher, "2026-11-01", "0.72")
        first_alert = maybe_create_high_risk_alert(first)
        self.assertIsNotNone(first_alert)

        first.probability = Decimal("0.90")
        first.save()
        second_alert = maybe_create_high_risk_alert(
            first,
            previous_probability=Decimal("0.72"),
        )

        self.assertIsNone(second_alert)
        self.assertEqual(HighRiskAlert.objects.count(), 1)

    def test_later_high_score_does_not_alert_if_pitcher_already_high(self):
        _outing, first = _make_assessment(self.pitcher, "2026-11-01", "0.70")
        maybe_create_high_risk_alert(first)

        _outing, second = _make_assessment(self.pitcher, "2026-11-08", "0.88")
        later_alert = maybe_create_high_risk_alert(second)

        self.assertIsNone(later_alert)
        self.assertEqual(HighRiskAlert.objects.count(), 1)

    def test_crossing_again_after_dropping_below_creates_new_alert(self):
        _outing, first = _make_assessment(self.pitcher, "2026-11-01", "0.70")
        maybe_create_high_risk_alert(first)

        _outing, low = _make_assessment(self.pitcher, "2026-11-08", "0.20")
        self.assertIsNone(maybe_create_high_risk_alert(low))

        _outing, high_again = _make_assessment(self.pitcher, "2026-11-15", "0.66")
        alert = maybe_create_high_risk_alert(high_again)

        self.assertIsNotNone(alert)
        self.assertEqual(HighRiskAlert.objects.count(), 2)
        self.assertEqual(alert.risk_score, Decimal("0.66"))

    def test_threshold_constant_is_one_half(self):
        self.assertEqual(HIGH_RISK_THRESHOLD, Decimal("0.5"))


class FakeRiskModel:
    def __init__(self, probability):
        self.classes_ = [0, 1]
        self.probability = probability

    def predict_proba(self, _model_input):
        return [[1 - self.probability, self.probability]]


class HighRiskAlertApiTests(APITestCase):
    def setUp(self):
        self.manager = User.objects.create_user(
            username="alert_manager",
            password="test-password",
            role=Role.MANAGER,
        )
        self.pitcher = User.objects.create_user(
            username="alert_pitcher_api",
            password="test-password",
            role=Role.PITCHER,
            throws_left=True,
        )
        self.client.force_authenticate(user=self.manager)

    def _bundle(self, probability):
        return {
            "model": FakeRiskModel(probability),
            "features": ["pitch_count", "avg_velo"],
            "name": "logistic_regression",
        }

    def test_posting_high_risk_outing_creates_alert_and_staff_can_list_it(self):
        with patch("api.risk_scoring.load_baseline", return_value=self._bundle(0.81)):
            response = self.client.post(
                "/api/outings/",
                {
                    "pitcher": self.pitcher.id,
                    "outing_type": "game",
                    "date": "2026-11-25",
                    "pitch_count": 85,
                    "avg_velocity": "92.40",
                    "rest_days": 5,
                },
                format="json",
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(HighRiskAlert.objects.count(), 1)

        listing = self.client.get("/api/high-risk-alerts/")
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(len(listing.data), 1)
        alert = listing.data[0]
        self.assertEqual(alert["pitcher"], self.pitcher.id)
        self.assertEqual(alert["pitcher_username"], "alert_pitcher_api")
        self.assertAlmostEqual(float(alert["risk_score"]), 0.81, places=6)
        self.assertEqual(alert["outing"], response.data["id"])
        self.assertEqual(alert["outing_date"], "2026-11-25")

    def test_posting_low_risk_outing_does_not_create_alert(self):
        with patch("api.risk_scoring.load_baseline", return_value=self._bundle(0.22)):
            response = self.client.post(
                "/api/outings/",
                {
                    "pitcher": self.pitcher.id,
                    "outing_type": "game",
                    "date": "2026-11-25",
                    "pitch_count": 60,
                    "avg_velocity": "93.10",
                    "rest_days": 5,
                },
                format="json",
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(HighRiskAlert.objects.count(), 0)
        listing = self.client.get("/api/high-risk-alerts/")
        self.assertEqual(listing.data, [])

    def test_pitcher_cannot_list_alerts(self):
        _outing, assessment = _make_assessment(self.pitcher, "2026-11-01", "0.81")
        maybe_create_high_risk_alert(assessment)
        self.client.force_authenticate(user=self.pitcher)

        listing = self.client.get("/api/high-risk-alerts/")
        self.assertEqual(listing.status_code, 403)
