from rest_framework import routers
from django.urls import path, include

from airport.views import (
    CountryViewSet,
    CityViewSet,
    AirlineViewSet,
    AirportViewSet,
    AirplaneTypeViewSet,
    AirplaneViewSet,
    GateViewSet,
    TerminalViewSet,
    RouteViewSet,
    FlightViewSet,
    CrewViewSet,
    OrderViewSet,
)

app_name = "airport"

router = routers.DefaultRouter()
router.register("countries", CountryViewSet)
router.register("cities", CityViewSet)
router.register("airlines", AirlineViewSet)
router.register("airports", AirportViewSet)
router.register("airplane_types", AirplaneTypeViewSet)
router.register("airplanes", AirplaneViewSet)
router.register("gates", GateViewSet)
router.register("terminals", TerminalViewSet)
router.register("routs", RouteViewSet)
router.register("flights", FlightViewSet)
router.register("crews", CrewViewSet)
router.register("orders", OrderViewSet)

urlpatterns = [path("", include(router.urls))]
