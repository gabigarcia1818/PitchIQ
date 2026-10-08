# PitchIQ models

Source: `backend/api/models.py`

## Team

| Field | Type |
|-------|------|
| name | string (unique) |
| created_at | datetime |

## User

| Field | Type |
|-------|------|
| username | string |
| password | string |
| email | string |
| first_name | string |
| last_name | string |
| role | pitcher \| manager \| admin |
| team | Team (optional) |

## PitcherOuting

One row per game or training.

| Field | Type |
|-------|------|
| pitcher | User |
| outing_type | game \| training |
| date | date |
| pitch_count | int |
| avg_velocity | decimal |
| rest_days | int |
| created_at | datetime |
| updated_at | datetime |

## PitcherDailyCheckIn

One per pitcher per day.

| Field | Type |
|-------|------|
| pitcher | User |
| date | date |
| soreness | int (1–10) |
| fatigue | int (1–10) |
| sleep_hours | decimal (0–24) |
| sleep_quality | int (1–10) |
| created_at | datetime |
| updated_at | datetime |
