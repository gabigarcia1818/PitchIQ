from django.utils import timezone
from rest_framework.test import APITestCase

from .models import PitcherDailyCheckIn, Role, User

CHECKINS = "/api/daily-check-ins/"


class PitcherDataIsolationTests(APITestCase):
    def setUp(self):
        self.a = User.objects.create_user("pitcher_a", role=Role.PITCHER)
        self.b = User.objects.create_user("pitcher_b", role=Role.PITCHER)
        self.checkin_a = self.make_checkin(self.a)
        self.checkin_b = self.make_checkin(self.b)

    def make_checkin(self, pitcher):
        return PitcherDailyCheckIn.objects.create(
            pitcher=pitcher,
            date=timezone.localdate(),
            soreness=3,
            fatigue=4,
            sleep_hours="7.50",
            sleep_quality=6,
        )

    def test_list_returns_only_own_check_ins(self):
        self.client.force_authenticate(self.a)
        res = self.client.get(CHECKINS)
        self.assertEqual(res.status_code, 200)
        self.assertEqual([row["id"] for row in res.data], [self.checkin_a.id])

    def test_other_pitchers_check_in_is_not_accessible(self):
        self.client.force_authenticate(self.a)
        res = self.client.get(f"{CHECKINS}{self.checkin_b.id}/")
        self.assertEqual(res.status_code, 404)

    def test_cannot_create_check_in_for_another_pitcher(self):
        PitcherDailyCheckIn.objects.filter(pitcher=self.a).delete()
        self.client.force_authenticate(self.a)
        res = self.client.post(
            CHECKINS,
            {
                "pitcher": self.b.id,
                "soreness": 2,
                "fatigue": 2,
                "sleep_hours": "8.00",
                "sleep_quality": 7,
            },
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["pitcher"], self.a.id)

    def test_cannot_update_or_delete_other_pitchers_check_in(self):
        self.client.force_authenticate(self.a)
        url = f"{CHECKINS}{self.checkin_b.id}/"

        patch_res = self.client.patch(url, {"soreness": 9}, format="json")
        self.assertEqual(patch_res.status_code, 404)

        delete_res = self.client.delete(url)
        self.assertEqual(delete_res.status_code, 404)

        self.checkin_b.refresh_from_db()
        self.assertEqual(self.checkin_b.soreness, 3)

    def test_pitcher_cannot_access_outings(self):
        self.client.force_authenticate(self.a)
        res = self.client.get("/api/outings/")
        self.assertEqual(res.status_code, 403)