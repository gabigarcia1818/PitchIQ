from rest_framework import serializers

from .models import PitcherOuting


class PitcherOutingSerializer(serializers.ModelSerializer):
    pitcher_username = serializers.CharField(source="pitcher.username", read_only=True)

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
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]