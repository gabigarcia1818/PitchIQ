import numpy as np
from rest_framework.test import APITestCase
from api.models import PitcherRiskAssessment, Role, User
from ml.train_baseline import FEATURES
from api.risk_scoring import load_baseline

class RiskAssessmentApiTests(APITestCase):
    def setUp(self):
        manager = User.objects.create_user(
            username="manager_test",
            password="test-password",
            role=Role.MANAGER,
        )
        self.pitcher = User.objects.create_user(
            username="pitcher_test",
            password="test-password",
            role=Role.PITCHER,
            throws_left=True,
        )
        self.client.force_authenticate(user=manager)

    def test_risk_on_new_outing(self):
        bundle = load_baseline()

        payload = {
            "pitcher": self.pitcher.id,
            "outing_type": "game",
            "date": "2026-11-25",
            "pitch_count": 85,
            "avg_velocity": "92.40",
            "rest_days": 5,
            "avg_fastball_velo": "94.10",
        }

        response = self.client.post("/api/outings/", payload, format="json")

        self.assertEqual(response.status_code, 201)
        assessment_data = response.data["risk_assessment"]
        self.assertIsNotNone(assessment_data)

        probability = float(assessment_data["probability"])
        self.assertGreaterEqual(probability, 0)
        self.assertLessEqual(probability, 1)
        self.assertEqual(assessment_data["model_name"], bundle["name"])

        assessment = PitcherRiskAssessment.objects.get(outing_id=response.data["id"])

        self.assertAlmostEqual(float(assessment.probability), probability, places=6)