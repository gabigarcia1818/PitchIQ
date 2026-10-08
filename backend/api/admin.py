from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import PitcherDailyCheckIn, PitcherOuting, Team, User


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")
    search_fields = ("name",)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("username", "email", "role", "team", "is_staff")
    list_filter = ("role", "team", "is_staff", "is_active")
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("PitchIQ", {"fields": ("role", "team")}),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        ("PitchIQ", {"fields": ("role", "team")}),
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
