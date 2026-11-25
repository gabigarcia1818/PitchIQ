from rest_framework import serializers
from .models import PitcherOuting, PitcherDailyCheckIn
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User
from .models import PitcherRiskAssessment

## For registering or creating a new user
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ["id", "username", "email", "password", "role"]
        read_only_fields = ["id", "role"]

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


## For getting an authenticated user's information
class MeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "role", "team"]
        read_only_fields = fields

## Generating a JWT token
class RoleTokenSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        return token

class PitcherRiskAssessmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PitcherRiskAssessment
        fields = ["probability", "model_name", "calculated_at"]

class PitcherOutingSerializer(serializers.ModelSerializer):
    pitcher_username = serializers.CharField(source="pitcher.username", read_only=True)
    risk_assessment = PitcherRiskAssessmentSerializer(read_only=True, allow_null=True)

    class Meta:
        model = PitcherOuting
        fields = [
            "id",
            "pitcher",
            "pitcher_username",
            "outing_type",
            "date",
            "pitch_count",
            "avg_velocity",
            "rest_days",
            "batters_faced",
            "innings_pitched_approx",
            "max_velo",
            "min_velo",
            "velo_std",
            "avg_spin",
            "max_spin",
            "avg_extension",
            "avg_release_pos_x",
            "avg_release_pos_z",
            "fastball_pct",
            "avg_fastball_velo",
            "max_fastball_velo",
            "risk_assessment",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "risk_assessment"]

class PitcherDailyCheckInSerializer(serializers.ModelSerializer):
    pitcher_username = serializers.CharField(source="pitcher.username", read_only=True)
    class Meta:
        model = PitcherDailyCheckIn
        fields = [
            "id",
            "pitcher",
            "pitcher_username",
            "date",
            "soreness",
            "fatigue",
            "sleep_hours",
            "sleep_quality",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "pitcher", "date", "created_at", "updated_at"]