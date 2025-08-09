from decimal import Decimal

from django.db.models import Prefetch
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet
from rest_framework import viewsets, mixins, status
from airport.permissions import IsAdminOrIfAuthenticatedReadOnly, IsAdminOrOwner

from airport.models import (
    Country,
    City,
    Airline,
    Airport,
    AirplaneType,
    Airplane,
    Gate,
    Terminal,
    Route,
    Flight,
    Crew,
    Ticket,
    Order,
)
from airport.serializers import (
    CountrySerializer,
    CitySerializer,
    AirlineSerializer,
    AirlineListSerializer,
    AirlineDetailSerializer,
    AirlineLogoSerializer,
    AirportSerializer,
    AirportListSerializer,
    AirportDetailSerializer,
    CityDetailSerializer,
    AirplaneTypeSerializer,
    AirplaneTypeImageSerializer,
    AirplaneSerializer,
    AirplaneListSerializer,
    AirplaneDetailSerializer,
    GateSerializer,
    GateListSerializer,
    GateDetailSerializer,
    TerminalSerializer,
    TerminalListSerializer,
    TerminalDetailSerializer,
    RouteSerializer,
    RouteListSerializer,
    RouteDetailSerializer,
    FlightSerializer,
    FlightListSerializer,
    FlightDetailSerializer,
    CrewSerializer,
    CrewListSerializer,
    CrewDetailSerializer,
    OrderListSerializer,
    OrderSerializer,
)


class CountryViewSet(viewsets.ModelViewSet):
    """Endpoint for viewing countries and country objects."""

    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)


class CityViewSet(viewsets.ModelViewSet):
    """Endpoint for viewing cities and city objects."""

    queryset = City.objects.select_related("country")
    serializer_class = CitySerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    def get_serializer_class(self):

        if self.action == "retrieve":
            return CityDetailSerializer

        return CitySerializer


class AirlineViewSet(viewsets.ModelViewSet):
    """Endpoint for viewing airlines and airline objects."""

    queryset = Airline.objects.select_related("country")
    serializer_class = AirlineSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    def get_queryset(self):
        """Retrieve the Airlines with filters by country"""

        country = self.request.query_params.get("country", None)
        queryset = self.queryset

        if country:
            queryset = queryset.filter(country__name__icontains=country)

        return queryset.distinct()

    def get_serializer_class(self):
        if self.action == "list":
            return AirlineListSerializer

        if self.action == "retrieve":
            return AirlineDetailSerializer

        if self.action == "upload_image":
            return AirlineLogoSerializer

        return AirlineSerializer

    @action(
        methods=["POST"],
        detail=True,
        url_path="upload-image",
        permission_classes=[IsAdminUser],
    )
    def upload_image(self, request, pk=None):
        """Endpoint for uploading logo to specific airline"""
        airline = self.get_object()
        serializer = self.get_serializer(airline, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "country",
                type=OpenApiTypes.STR,
                description="Filter by country (ex. ?country=USA)",
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class AirportViewSet(viewsets.ModelViewSet):
    """Endpoint for viewing Airports and Airport objects."""

    queryset = Airport.objects.select_related(
        "closest_big_city__country",
    )
    serializer_class = AirportListSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    def get_serializer_class(self):
        if self.action == "list":
            return AirportListSerializer
        elif self.action == "retrieve":
            return AirportDetailSerializer
        return AirportSerializer


class AirplaneTypeViewSet(viewsets.ModelViewSet):
    """Endpoint for viewing airplane types and airplane type objects."""

    queryset = AirplaneType.objects.all()
    serializer_class = AirplaneTypeSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    def get_queryset(self):
        """Retrieve the Airplanes Type with filters by name"""

        name = self.request.query_params.get("name", None)
        queryset = self.queryset

        if name:
            queryset = queryset.filter(name__icontains=name)

        return queryset.distinct()

    def get_serializer_class(self):
        if self.action == "upload_image":
            return AirplaneTypeImageSerializer

        return AirplaneTypeSerializer

    @action(
        methods=["POST"],
        detail=True,
        url_path="upload-image",
        permission_classes=[IsAdminUser],
    )
    def upload_image(self, request, pk=None):
        """Endpoint for uploading image to specific airplane type"""

        airplane = self.get_object()
        serializer = self.get_serializer(airplane, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "airplane_type",
                type=OpenApiTypes.STR,
                description="Filter by name (ex. ?name=Boeing)",
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class AirplaneViewSet(viewsets.ModelViewSet):
    """Endpoint for viewing airplanes and airplane objects."""

    queryset = Airplane.objects.select_related("airplane_type", "airline")
    serializer_class = AirplaneSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    def get_serializer_class(self):
        if self.action == "list":
            return AirplaneListSerializer
        elif self.action == "retrieve":
            return AirplaneDetailSerializer
        return AirplaneSerializer


class GateViewSet(viewsets.ModelViewSet):
    """Endpoint for viewing gates and gate objects."""

    serializer_class = GateSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)
    queryset = Gate.objects.select_related("terminal__airport")

    def get_serializer_class(self):
        if self.action == "list":
            return GateListSerializer
        elif self.action == "retrieve":
            return GateDetailSerializer
        return GateSerializer

    def get_queryset(self):
        queryset = super().get_queryset().order_by("number")

        if self.action in ["list", "retrieve"]:
            queryset = queryset.select_related("terminal", "terminal__airport")

        airport_name = self.request.query_params.get("airport_name")
        if airport_name:
            queryset = queryset.filter(terminal__airport__name__icontains=airport_name)

        terminal_suffix = self.request.query_params.get("terminal_suffix")
        if terminal_suffix:
            queryset = queryset.filter(terminal__name__iendswith=terminal_suffix)

        return queryset.distinct()

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "airport_name",
                type=OpenApiTypes.STR,
                description="Filter by airports name (ex. ?airport_name=Boryspil)",
            ),
            OpenApiParameter(
                "terminal_suffix",
                type=OpenApiTypes.STR,
                description="Filter by and of terminals name (ex. ?terminal_suffix=A)",
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class TerminalViewSet(viewsets.ModelViewSet):
    """Endpoint for viewing terminals and terminal objects."""

    serializer_class = TerminalSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)
    queryset = Terminal.objects.all()

    def get_serializer_class(self):
        if self.action == "list":
            return TerminalListSerializer
        elif self.action == "retrieve":
            return TerminalDetailSerializer
        return TerminalSerializer

    def get_queryset(self):
        queryset = super().get_queryset().order_by("name")

        if self.action in ["list", "retrieve"]:
            queryset = queryset.select_related(
                "airport",
                "airport__closest_big_city",
                "airport__closest_big_city__country",
            )

        airport_name = self.request.query_params.get("airport_name")
        if airport_name:
            queryset = queryset.filter(airport__name__icontains=airport_name)

        return queryset.distinct()

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "airport_name",
                type=OpenApiTypes.STR,
                description="Filter by airports name (ex. ?airport_name=Boryspil)",
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class RouteViewSet(viewsets.ModelViewSet):
    """Endpoint for viewing routes and route objects."""

    serializer_class = RouteSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)
    queryset = Route.objects.select_related(
        "source",
        "destination",
        "source__closest_big_city",
        "destination__closest_big_city",
        "source__closest_big_city__country",
        "destination__closest_big_city__country",
    )

    def get_serializer_class(self):
        if self.action == "list":
            return RouteListSerializer
        elif self.action == "retrieve":
            return RouteDetailSerializer
        return RouteSerializer

    def get_queryset(self):
        """Retrieve the Route with filters by source and destination."""

        source_name = self.request.query_params.get("source_name")
        destination_name = self.request.query_params.get("destination_name")
        queryset = self.queryset

        if source_name:
            queryset = queryset.filter(source__name__icontains=source_name)

        if destination_name:
            queryset = queryset.filter(destination__name__icontains=destination_name)

        return queryset.distinct()

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "source_name",
                type=OpenApiTypes.STR,
                description="Filter by source name (ex. ?source_name=Boryspil)",
            ),
            OpenApiParameter(
                "destination_name",
                type=OpenApiTypes.STR,
                description="Filter by destination name (ex. ?destination_name=Berlin Brandenburg Airport)",
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class FlightViewSet(viewsets.ModelViewSet):
    """Endpoint for viewing flights, flight status and flight objects."""

    serializer_class = FlightSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)
    queryset = Flight.objects.select_related(
        "route__source",
        "route__destination",
        "airplane__airplane_type",
        "airplane__airline",
        "status",
        "departure_gate__terminal__airport",
        "arrival_gate__terminal__airport",
    )

    def get_serializer_class(self):

        if self.action == "list":
            return FlightListSerializer
        elif self.action in ["retrieve", "update", "partial_update"]:
            return FlightDetailSerializer

        return FlightSerializer

    def get_queryset(self):

        departure = self.request.query_params.get("departure")
        arrival = self.request.query_params.get("arrival")
        min_price = self.request.query_params.get("min_price")
        flight_num = self.request.query_params.get("flight_num")
        queryset = self.queryset

        if departure:
            queryset = queryset.filter(route__source__name__icontains=departure)

        if arrival:
            queryset = queryset.filter(route__destination__name__icontains=arrival)

        if min_price:
            price_val = Decimal(min_price)
            queryset = queryset.filter(price__gte=price_val)

        if flight_num:
            queryset = queryset.filter(flight_number__iexact=flight_num)

        return queryset.distinct()

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "departure",
                type=OpenApiTypes.STR,
                description="Filter by departure airport name (ex. ?departure=Boryspil)",
            ),
            OpenApiParameter(
                "arrival",
                type=OpenApiTypes.STR,
                description="Filter by arrival airport name (ex. ?airport=Zhuliany)",
            ),
            OpenApiParameter(
                "min_price",
                type=OpenApiTypes.STR,
                description="Filter by destination name (ex. ?min_price=4000)",
            ),
            OpenApiParameter(
                "flight_num",
                type=OpenApiTypes.STR,
                description="Filter by destination name (ex. ?flight_num=101)",
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class CrewViewSet(viewsets.ModelViewSet):
    """Endpoint for viewing crews for flights."""

    serializer_class = CrewSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)
    queryset = Crew.objects.prefetch_related(
        Prefetch(
            "flights",
            queryset=Flight.objects.select_related(
                "route__source",
                "route__destination",
                "airplane__airplane_type",
                "airplane__airline",
                "status"
            )
        )
    )

    @staticmethod
    def _params_to_ints(qs):
        """Converts a list of string IDs to a list of integers"""
        return [int(str_id) for str_id in qs.split(",")]

    def get_serializer_class(self):
        if self.action == "list":
            return CrewListSerializer
        if self.action in ["retrieve"]:
            return CrewDetailSerializer
        return CrewSerializer

    def get_queryset(self):

        flights = self.request.query_params.get("flights")
        queryset = self.queryset

        if flights:
            flight_ids = self._params_to_ints(flights)
            queryset = queryset.filter(flights__id__in=flight_ids)

        return queryset.distinct()

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "flights",
                type={"type": "list", "items": {"type": "number"}},
                description="Filter by flights id (ex. ?flights=2,5)",
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class OrderPagination(PageNumberPagination):
    page_size = 10
    max_page_size = 100


class OrderViewSet(ModelViewSet):
    permission_classes = (IsAdminOrOwner,)
    pagination_class = OrderPagination
    queryset = Order.objects.prefetch_related("tickets")
    serializer_class = OrderSerializer

    def get_queryset(self):
        order_queryset = Order.objects.select_related(
            "flight__route__source",
            "flight__route__destination",
            "user")

        tickets_queryset = (
            Ticket.objects
            .select_related(
                "flight",
                "flight__route",
                "flight__route__source",
                "flight__route__destination",
            )
            .order_by("row", "seat")
        )

        order_queryset = order_queryset.prefetch_related(
            Prefetch("tickets", queryset=tickets_queryset)
        )

        user = self.request.user
        if user.is_staff:
            return order_queryset

        return order_queryset.filter(user=user)

    def get_serializer_class(self):
        if self.action == "list":
            return OrderListSerializer
        return OrderSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

