import random, string
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient
from typing import Optional

from airport.models import (
    Country,
    City,
    Airport,
    Route,
)
from airport.serializers import  RouteListSerializer, RouteDetailSerializer
from airport.views import  RouteViewSet

ROUTE_URL = reverse("airport:route-list")

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
    """Sample airport object."""

    if city is None:
        city = sample_city()
    defaults = {
        "name": "Test Airport",
        "closest_big_city": city,
        "iata_code": params.pop("iata_code", _unique_code(Airport, "iata_code", 3)),
        "icao_code": params.pop("icao_code", _unique_code(Airport, "icao_code", 4)),
    }
    defaults.update(params)
    return Airport.objects.create(**defaults)

def sample_route(
        *,
        source: Optional[Airport] = None,
        destination: Optional[Airport] = None,
        **params
) -> Route:
    """Sample route object."""

    if source is None:
        city_a = sample_city(name="City A",)
        source = sample_airport(city=city_a, name="Airport A")

    if destination is None:
        city_b = sample_city(name="City B",)
        destination = sample_airport(city=city_b, name="Airport B")
    defaults = {
        "source": source,
        "destination": destination,
    }
    defaults.update(params)
    return Route.objects.create(**defaults)

def detail_url(route_id: int):
    """Return the detail URL"""

    return reverse("airport:route-detail", args=[route_id])


class UnauthenticatedRouteApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(ROUTE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedRouteApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.test",
            password="testpassword12345",
        )
        self.client.force_authenticate(user=self.user)

    def test_routes_list(self):
        """Test routes list."""

        sample_route()

        res = self.client.get(ROUTE_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        expected_qs = RouteViewSet.queryset.order_by("id")
        serializer = RouteListSerializer(expected_qs, many=True)

        self.assertEqual(res.data["results"], serializer.data)

    def test_route_detail(self):
        route = sample_route()

        url = detail_url(route.id)
        res = self.client.get(url)

        expected_obj = RouteViewSet.queryset.get(pk=route.id)
        serializer = RouteDetailSerializer(expected_obj)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_route_forbidden(self):
        """Test route creation forbidden."""

        country1 = sample_country(name="United Kingdom")
        country2 = sample_country(name="Brazil")
        city1 = sample_city(country=country1, name="City A1")
        city2 = sample_city(country=country2, name="City B1")
        airport1 = sample_airport(closest_big_city=city1, name="Airport A1")
        airport2 = sample_airport(closest_big_city=city2, name="Airport B1")

        payload = {
            "source": airport1,
            "destination": airport2,

        }
        res = self.client.post(ROUTE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_filter_route_by_source_and_destination(self):
        """Test filtering routes by source & destination."""

        country1 = sample_country(name="United Kingdom")
        country2 = sample_country(name="Brazil")
        city1 = sample_city(country=country1, name="London")
        city2 = sample_city(country=country2, name="Rio")
        airport1 = sample_airport(closest_big_city=city1, name="London International Airport")
        airport2 = sample_airport(closest_big_city=city2, name="Rio Great Airport")

        route_uk_br = sample_route(
            source=airport1,
            destination=airport2,

        )
        country3 = sample_country(name="Germany")
        country4 = sample_country(name="Italy")
        city3 = sample_city(country=country3, name="Berlin")
        city4 = sample_city(country=country4, name="Rome")
        airport3 = sample_airport(closest_big_city=city3, name="Berlin International Airport")
        airport4 = sample_airport(closest_big_city=city4, name="Rome Great Airport")

        route_gr_it = sample_route(
            source=airport3,
            destination=airport4,
        )

        route_3 = sample_route()

        res_source = self.client.get(ROUTE_URL, {"source_name": "International"})
        res_destination = self.client.get(ROUTE_URL, {"destination_name": "Great"})

        serializer_1 = RouteListSerializer(route_uk_br)
        serializer_2 = RouteListSerializer(route_gr_it)
        serializer_unrelated = RouteListSerializer(route_3)

        self.assertIn(serializer_1.data, res_source.data["results"])
        self.assertIn(serializer_2.data, res_source.data["results"])
        self.assertNotIn(serializer_unrelated.data, res_source.data["results"])
        self.assertIn(serializer_1.data, res_destination.data["results"])
        self.assertIn(serializer_2.data, res_destination.data["results"])
        self.assertNotIn(serializer_unrelated.data, res_destination.data["results"])


class AdminRouteApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin.test@test",
            password="admin_test_password123",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user)

    def test_create_route(self):
        """Test create route by admin"""

        country1 = sample_country(name="United Kingdom")
        country2 = sample_country(name="Brazil")
        city1 = sample_city(country=country1, name="London")
        city2 = sample_city(country=country2, name="Rio")
        airport1 = sample_airport(closest_big_city=city1, name="London Airport")
        airport2 = sample_airport(closest_big_city=city2, name="Rio Airport")

        payload = {
            "source": str(airport1.id),
            "destination": str(airport2.id),
        }
        res = self.client.post(ROUTE_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        route = Route.objects.get(id=res.data["id"])
        self.assertEqual(route.source, airport1)
        self.assertEqual(route.destination, airport2)

    def test_delete_airport(self):
        """Test delete airport by admin"""
        route = sample_route()
        url = detail_url(route.id)

        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
