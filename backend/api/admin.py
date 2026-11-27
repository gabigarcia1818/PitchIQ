from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import HighRiskAlert, PitcherDailyCheckIn, PitcherOuting, Team, User, PitcherRiskAssessment


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")
    search_fields = ("name",)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("username", "email", "role", "team", "throws_left", "is_staff")
    list_filter = ("role", "team", "is_staff", "is_active")
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("PitchIQ", {"fields": ("role", "team", "throws_left")}),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        ("PitchIQ", {"fields": ("role", "team", "throws_left")}),
    )


@admin.register(PitcherOuting)
class PitcherOutingAdmin(admin.ModelAdmin):
    list_display = (
        "pitcher",
        "outing_type",
        "date",
        "pitch_count",
        "avg_velocity",
        "rest_days",
    )
    list_filter = ("outing_type", "date", "pitcher__team")
    search_fields = ("pitcher__username",)
    date_hierarchy = "date"


@admin.register(PitcherDailyCheckIn)
class PitcherDailyCheckInAdmin(admin.ModelAdmin):
    list_display = (
        "pitcher",
        "date",
        "soreness",
        "fatigue",
        "sleep_hours",
        "sleep_quality",
    )
    list_filter = ("date", "pitcher__team")
    search_fields = ("pitcher__username",)
    date_hierarchy = "date"

@admin.register(PitcherRiskAssessment)
class PitcherRiskAssessmentAdmin(admin.ModelAdmin):
    list_display = ("outing", "probability", "model_name", "calculated_at")
    list_select_related = ("outing", "outing__pitcher")
    search_fields = ("outing__pitcher__username",)
    ordering = ("-calculated_at",)


@admin.register(HighRiskAlert)
class HighRiskAlertAdmin(admin.ModelAdmin):
    list_display = ("pitcher", "risk_score", "created_at")
    list_select_related = ("pitcher", "risk_assessment", "risk_assessment__outing")
    search_fields = ("pitcher__username",)
    ordering = ("-created_at",)
