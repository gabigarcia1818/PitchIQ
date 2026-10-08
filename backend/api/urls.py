from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import PitcherOutingViewSet, health

router = DefaultRouter()
router.register(r"outings", PitcherOutingViewSet, basename="outing")

urlpatterns = [
    path("health/", health),
    path("", include(router.urls)),
]
