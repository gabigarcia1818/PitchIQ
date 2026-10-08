from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import PitcherOuting
from .serializers import PitcherOutingSerializer


@api_view(["GET"])
def health(request):
    return Response({"status": "ok"})

class PitcherOutingViewSet(viewsets.ModelViewSet):
    queryset = PitcherOuting.objects.all()
    serializer_class = PitcherOutingSerializer
    filterset_fields = ["pitcher", "outing_type", "date"]
