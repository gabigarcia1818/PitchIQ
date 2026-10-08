from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Role(models.TextChoices):
    PITCHER = "pitcher", "Pitcher"
    MANAGER = "manager", "Manager"
    ADMIN = "admin", "Admin"


class OutingType(models.TextChoices):
    GAME = "game", "Game"
    TRAINING = "training", "Training"


class Team(models.Model):
    name = models.CharField(max_length=120, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class User(AbstractUser):
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.PITCHER,
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="members",
    )

    class Meta:
        ordering = ["username"]

    def __str__(self) -> str:
        return f"{self.username} ({self.get_role_display()})"


rating_validator = [MinValueValidator(1), MaxValueValidator(10)]


class PitcherOuting(models.Model):
    """One row per game or training session."""

    pitcher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="outings",
        limit_choices_to={"role": Role.PITCHER},
    )
    outing_type = models.CharField(max_length=20, choices=OutingType.choices)
    date = models.DateField()
    pitch_count = models.PositiveIntegerField()
    avg_velocity = models.DecimalField(max_digits=5, decimal_places=2)
    rest_days = models.PositiveIntegerField(
        help_text="Days of rest before this outing.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-created_at"]
        indexes = [
            models.Index(fields=["pitcher", "-date"]),
            models.Index(fields=["date"]),
        ]

    def __str__(self) -> str:
        return f"{self.pitcher.username} {self.get_outing_type_display()} {self.date}"


class PitcherDailyCheckIn(models.Model):
    """One check-in per pitcher per calendar day."""

    pitcher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="daily_check_ins",
        limit_choices_to={"role": Role.PITCHER},
    )
    date = models.DateField()
    soreness = models.PositiveSmallIntegerField(validators=rating_validator)
    fatigue = models.PositiveSmallIntegerField(validators=rating_validator)
    sleep_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(24)],
    )
    sleep_quality = models.PositiveSmallIntegerField(validators=rating_validator)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["pitcher", "date"],
                name="unique_pitcher_daily_check_in",
            ),
        ]
        indexes = [
            models.Index(fields=["pitcher", "-date"]),
            models.Index(fields=["date"]),
        ]

    def __str__(self) -> str:
        return f"{self.pitcher.username} check-in {self.date}"
