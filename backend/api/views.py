from django.utils import timezone
from django.db import transaction, IntegrityError

from rest_framework import viewsets, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView


from .models import PitcherOuting, PitcherDailyCheckIn
from .serializers import PitcherOutingSerializer, PitcherDailyCheckInSerializer, MeSerializer, RegisterSerializer, RoleTokenSerializer
from .permissions import IsStaffRole, IsPitcher

@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    return Response({"status": "ok"})

class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

class LoginView(TokenObtainPairView):
    serializer_class = RoleTokenSerializer

class MeView(generics.RetrieveAPIView):
    serializer_class = MeSerializer

    def get_object(self):
        return self.request.user

class PitcherOutingViewSet(viewsets.ModelViewSet):
    queryset = PitcherOuting.objects.select_related("pitcher")
    serializer_class = PitcherOutingSerializer
    permission_classes = [IsStaffRole]
    filterset_fields = ["pitcher", "outing_type", "date"]

class PitcherDailyCheckInViewSet(viewsets.ModelViewSet):
    serializer_class = PitcherDailyCheckInSerializer
    permission_classes = [IsPitcher]

    def get_queryset(self):
        return PitcherDailyCheckIn.objects.filter(pitcher=self.request.user)

    def perform_create(self, serializer):
        pitcher = self.request.user
        today = timezone.localdate()
        already_checked_in = PitcherDailyCheckIn.objects.filter(
            pitcher=pitcher,
            date=today,
        ).exists()

        if already_checked_in:
            raise ValidationError({"detail": "You have already checked in."})

        try:
            with transaction.atomic():
                serializer.save(
                    pitcher=pitcher,
                    date=today,
                )
        except IntegrityError:
            duplicate_exists = PitcherDailyCheckIn.objects.filter(
                pitcher=pitcher,
                date=today,
            ).exists()

            if duplicate_exists:
                raise ValidationError({"detail": "You have already checked in."})
            raise

    def perform_destroy(self, instance):
        if instance.date != timezone.localdate():
            raise ValidationError(
                {"detail": "Only today's check-in can be deleted and replaced."}
            )
        instance.delete()
