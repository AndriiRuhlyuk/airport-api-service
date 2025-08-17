from datetime import timedelta, date
import random
import string
from decimal import Decimal
from uuid import uuid4

from django.utils import timezone

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient
from typing import Optional

from airport.models import (
    Country,
    Airline,
    City,
    Airport,
    Flight,
    Route,
    Airplane,
    AirplaneType,
    Gate,
    Terminal,
    FlightStatus
)
from airport.serializers import FlightDetailSerializer, FlightListSerializer
from airport.views import FlightViewSet


FLIGHT_URL = reverse("airport:flight-list")


def _rand_letters(k: int) -> str:
    """Generate a random string of length k"""
    return "".join(random.choices(string.ascii_uppercase, k=k))


def _unique_code(model, field: str, k: int) -> str:
    """Generate a random string of length k"""
    while True:
        code = _rand_letters(k)
        if not model.objects.filter(**{field: code}).exists():
            return code


def uniq(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:6].upper()}"


def sample_country(**params) -> Country:
    """Sample country object."""
    name = params.pop("name", None) or uniq("Testland")
    defaults = {
        "name": name,
        "currency": "QWE",
        "timezone": "America/New_York",
    }
    defaults.update(params)
    return Country.objects.create(**defaults)


def sample_city(
        *,
        country: Optional[Country] = None,
        **params
) -> City:
    """Sample city object."""

    if country is None:
        country = sample_country()
    defaults = {
        "name": params.pop("name", uniq("City")),
        "country": country,
        "population": 1000,
        "latitude": params.pop("latitude", 50.0 + random.uniform(-1, 1)),
        "longitude": params.pop("longitude", 30.0 + random.uniform(-1, 1))
    }
    defaults.update(params)
    return City.objects.create(**defaults)


def sample_airport(
        *,
        city: Optional[City] = None,
        **params
) -> Airport:
    if city is None:
        city = sample_city()
    defaults = {
        "name": "Test Airport",
        "closest_big_city": city,
        "iata_code": params.pop(
            "iata_code",
            _unique_code(Airport, "iata_code", 3)
        ),
        "icao_code": params.pop(
            "icao_code",
            _unique_code(Airport, "icao_code", 4)
        ),
    }
    defaults.update(params)
    return Airport.objects.create(**defaults)


def sample_airline(
        *,
        country: Optional[Country] = None,
        **params
) -> Airline:
    """Sample airline object."""

    if country is None:
        country = sample_country()
    defaults = {
        "name": params.pop("name", uniq("MAU")),
        "code": params.pop("code", _unique_code(Airline, "code", 3)),
        "country": country,
        "founded_year": 1900,
        "is_active": True,
    }
    defaults.update(params)
    return Airline.objects.create(**defaults)


def sample_airplane_type(**params) -> AirplaneType:
    """Sample airplane type object."""

    defaults = {
        "name": params.pop("name", uniq("Boeing")),
        "manufacturer": "Airplane Constructor",
    }
    defaults.update(params)
    return AirplaneType.objects.create(**defaults)


def sample_airplane(
        *,
        airplane_type: Optional[AirplaneType] = None,
        airline: Optional[Airline] = None,
        **params
) -> Airplane:
    """Sample airplane object."""
    if airplane_type is None:
        airplane_type = sample_airplane_type()
    if airline is None:
        airline = sample_airline()
    defaults = {
        "name": "TestAirplane",
        "rows": 10,
        "seats_in_row": 10,
        "airplane_type": airplane_type,
        "airline": airline,
        "registration_number": params.pop("name", uniq("QWERTY")),
        "is_active": True,
    }
    defaults.update(params)
    return Airplane.objects.create(**defaults)


def sample_route(
        *,
        source: Optional[Airport] = None,
        destination: Optional[Airport] = None,
        **params
) -> Route:
    """Sample route object."""

    if source is None:
        city_a = sample_city(name="City A")
        source = sample_airport(city=city_a, name="Airport A")

    if destination is None:
        city_b = sample_city(name="City B")
        destination = sample_airport(city=city_b, name="Airport B")
    defaults = {
        "source": source,
        "destination": destination,
    }
    defaults.update(params)
    return Route.objects.create(**defaults)


def sample_terminal(
        *,
        airport: Optional[Airport] = None,
        **params
) -> Terminal:
    """Sample terminal object."""
    if airport is None:
        airport = sample_airport()
    defaults = {
        "name": "Test Terminal",
        "airport": airport,
        "capacity": 1000,
        "is_international": True,
        "opened_date": date.today(),
    }
    defaults.update(params)
    return Terminal.objects.create(**defaults)


def sample_gate(
        *,
        terminal: Optional[Terminal] = None,
        **params
) -> Gate:
    """Sample gate object."""
    if terminal is None:
        terminal = sample_terminal()
    defaults = {
        "number": "A1",
        "terminal": terminal,
        "gate_type": "MIXED",
        "is_active": True,
    }
    defaults.update(params)
    return Gate.objects.create(**defaults)


def sample_flight_status(**params) -> FlightStatus:
    """Sample flight status object."""
    defaults = {
        "name": "SCHEDULED",
        "description": "Scheduled",
        "color_code": "#00000"
    }
    defaults.update(params)
    return FlightStatus.objects.create(**defaults)


def sample_flight(
        *,
        route: Optional[Route] = None,
        airplane: Optional[Airplane] = None,
        departure_gate: Optional[Gate] = None,
        arrival_gate: Optional[Gate] = None,
        status_f: Optional[FlightStatus] = None,
        **params
) -> Flight:
    """Sample flight object."""

    if route is None:
        route = sample_route()
    if airplane is None:
        airplane = sample_airplane()
    if departure_gate is None:
        departure_gate = sample_gate(number=uniq("A"))
    if arrival_gate is None:
        arrival_gate = sample_gate(number=uniq("B"))
    if status_f is None:
        status_f = sample_flight_status()

    departure = params.pop(
        "departure_time",
        timezone.now()
    )
    arrival = params.pop(
        "arrival_time", departure + timedelta(days=1)
    )

    defaults = {
        "route": route,
        "airplane": airplane,
        "flight_number": "10001",
        "departure_time": departure,
        "arrival_time": arrival,
        "price": 10000,
        "departure_gate": departure_gate,
        "arrival_gate": arrival_gate,
        "status": status_f
    }
    defaults.update(params)
    return Flight.objects.create(**defaults)


def detail_url(airline_id: int):
    """Return the detail URL"""

    return reverse("airport:flight-detail", args=[airline_id])


class UnauthenticatedFlightApiTests(TestCase):
    """Flight tests by unauthenticated user."""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(FLIGHT_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedFlightApiTests(TestCase):
    """Tests flights by authenticated user"""

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.test",
            password="testpassword12345",
        )
        self.client.force_authenticate(user=self.user)

    def test_flight_list(self):
        """Test flight list."""
        sample_flight()

        res = self.client.get(FLIGHT_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        expected_qs = FlightViewSet.queryset.order_by("id")
        serializer = FlightListSerializer(expected_qs, many=True)

        self.assertEqual(res.data["results"], serializer.data)

    def test_flight_detail(self):
        """Test the flight detail endpoint."""

        flight = sample_flight()

        url = detail_url(flight.id)
        res = self.client.get(url)

        expected_obj = FlightViewSet.queryset.get(pk=flight.id)
        serializer = FlightDetailSerializer(expected_obj)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_flight_forbidden(self):
        """Test create flight object forbidden."""

        country1 = sample_country(name="United Kingdom")
        country2 = sample_country(name="Brazil")
        city1 = sample_city(country=country1, name="City A1")
        city2 = sample_city(country=country2, name="City B1")
        airport1 = sample_airport(closest_big_city=city1, name="Airport A1")
        airport2 = sample_airport(closest_big_city=city2, name="Airport B1")
        route = sample_route(source=airport1, destination=airport2)
        airplane = sample_airplane()
        departure = timezone.now()
        arrival = departure + timedelta(days=1)
        status_f = sample_flight_status()
        gate1 = sample_gate(number="A1")
        gate2 = sample_gate(number="A2")
        payload = {
            "flight_number": "10001",
            "route": route,
            "airplane": airplane,
            "departure_time": departure,
            "arrival_time": arrival,
            "price": 10000,
            "status": status_f,
            "departure_gate": gate1,
            "arrival_gate": gate2,

        }
        res = self.client.post(FLIGHT_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class FlightFiltersApiTests(TestCase):
    """Tests filters flight list."""

    def setUp(self):
        self.client = APIClient()
        user = get_user_model().objects.create_user(
            email="test@test.test", password="testpassword12345"
        )
        self.client.force_authenticate(user=user)

        country_uk = sample_country(name="United Kingdom")
        country_br = sample_country(name="Brazil")
        city_london = sample_city(
            country=country_uk,
            name="London"
        )
        city_rio = sample_city(
            country=country_br,
            name="Rio"
        )
        airport_lon = sample_airport(
            closest_big_city=city_london,
            name="London Airport"
        )
        airport_rio = sample_airport(
            closest_big_city=city_rio,
            name="Rio Airport"
        )
        route_london_rio = sample_route(
            source=airport_lon,
            destination=airport_rio
        )
        plane1 = sample_airplane(name="Boeing LON-RIO")
        self.flight1 = sample_flight(
            flight_number="UK100",
            route=route_london_rio,
            airplane=plane1,
            price=Decimal("10000.00"),
            departure_time=timezone.now(),
            arrival_time=timezone.now() + timezone.timedelta(hours=24),
        )

        country_usa = sample_country(name="USA")
        country_ua = sample_country(name="Ukraine")
        city_new_york = sample_city(
            country=country_usa,
            name="New York"
        )
        city_kyiv = sample_city(
            country=country_ua,
            name="Kyiv"
        )
        airport_new_york = sample_airport(
            closest_big_city=city_new_york,
            name="NewYork Airport"
        )
        airport_kyiv = sample_airport(
            closest_big_city=city_kyiv,
            name="Kyiv Airport"
        )
        route_new_york_kyiv = sample_route(
            source=airport_new_york,
            destination=airport_kyiv
        )
        plane2 = sample_airplane(name="Airbus NY-KY")
        self.flight2 = sample_flight(
            flight_number="US500",
            route=route_new_york_kyiv,
            airplane=plane2,
            price=Decimal("5000.00"),
            departure_time=timezone.now(),
            arrival_time=timezone.now() + timezone.timedelta(hours=24),
        )

        country_kenya = sample_country(name="Kenya")
        country_norway = sample_country(name="Norway")
        city_nairobi = sample_city(
            country=country_kenya,
            name="Nairobi"
        )
        city_oslo = sample_city(country=country_norway, name="Oslo")
        airport_nb = sample_airport(
            closest_big_city=city_nairobi,
            name="Nairobi Airport"
        )
        airport_os = sample_airport(
            closest_big_city=city_oslo,
            name="Oslo Airport"
        )
        route_nairobi_oslo = sample_route(
            source=airport_nb,
            destination=airport_os
        )
        plane3 = sample_airplane(name="Boeing NB-OS")
        self.flight3 = sample_flight(
            flight_number="KE150",
            route=route_nairobi_oslo,
            airplane=plane3,
            price=Decimal("15000.00"),
            departure_time=timezone.now(),
            arrival_time=timezone.now() + timezone.timedelta(hours=24),
        )

    def _expected(self, **filters):
        qs = FlightViewSet.queryset
        if "departure" in filters:
            qs = qs.filter(
                route__source__name__icontains=filters["departure"]
            )
        if "arrival" in filters:
            qs = qs.filter(
                route__destination__name__icontains=filters["arrival"]
            )
        if "min_price" in filters:
            qs = qs.filter(price__gte=Decimal(filters["min_price"]))
        if "flight_num" in filters:
            qs = qs.filter(
                flight_number__iexact=filters["flight_num"]
            )
        qs = qs.order_by("id").distinct()
        return FlightListSerializer(qs, many=True).data

    def test_filter_by_departure(self):
        res = self.client.get(FLIGHT_URL, {"departure": "on"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        expected = self._expected(departure="on")
        self.assertEqual(res.data["results"], expected)

    def test_filter_by_arrival(self):
        res = self.client.get(FLIGHT_URL, {"arrival": "Kyiv"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        expected = self._expected(arrival="Kyiv")
        self.assertEqual(res.data["results"], expected)

    def test_filter_by_min_price(self):
        res = self.client.get(FLIGHT_URL, {"min_price": "9000"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        expected = self._expected(min_price="9000")
        self.assertEqual(res.data["results"], expected)

    def test_filter_by_flight_num_case_insensitive(self):
        res = self.client.get(
            FLIGHT_URL,
            {"flight_num": "uk100"}
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        expected = self._expected(flight_num="uk100")
        self.assertEqual(res.data["results"], expected)

    def test_filter_combined(self):
        res = self.client.get(
            FLIGHT_URL,
            {"departure": "new", "min_price": "4000"}
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        expected = self._expected(departure="new", min_price="4000")
        self.assertEqual(res.data["results"], expected)


class AdminFlightApiTests(TestCase):
    """Tests flights by admin user"""

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin.test@test",
            password="admin_test_password123",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user)

    def test_create_flight(self):
        """Test create flight by admin"""

        country1 = sample_country(name="United Kingdom")
        country2 = sample_country(name="Brazil")
        city1 = sample_city(country=country1, name="London")
        city2 = sample_city(country=country2, name="Rio")
        airport1 = sample_airport(
            closest_big_city=city1,
            name="London Airport"
        )
        airport2 = sample_airport(
            closest_big_city=city2,
            name="Rio Airport"
        )
        route = sample_route(
            source=airport1,
            destination=airport2
        )
        airplane = sample_airplane(name="boeing777")
        departure = timezone.now()
        arrival = departure + timedelta(days=1)
        status_f = sample_flight_status()
        gate1 = sample_gate(number="A1")
        gate2 = sample_gate(number="A2")
        payload = {
            "flight_number": "10001",
            "route": route.id,
            "airplane": airplane.id,
            "departure_time": departure.isoformat(),
            "arrival_time": arrival.isoformat(),
            "price": "10000.00",
            "status": status_f.id,
            "departure_gate": gate1.id,
            "arrival_gate": gate2.id,
        }
        res = self.client.post(FLIGHT_URL, payload)
        flight = Flight.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(flight.flight_number, payload["flight_number"])
        self.assertEqual(flight.route_id, payload["route"])
        self.assertEqual(flight.airplane_id, payload["airplane"])
        self.assertEqual(flight.status_id, payload["status"])
        self.assertEqual(flight.departure_gate_id, payload["departure_gate"])
        self.assertEqual(flight.arrival_gate_id, payload["arrival_gate"])
        self.assertEqual(str(flight.price), payload["price"])

    def test_delete_flight(self):
        """Test delete flight by admin"""
        flight = sample_flight()
        url = detail_url(flight.id)

        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
