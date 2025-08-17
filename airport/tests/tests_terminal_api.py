import random
import string
from uuid import uuid4
from datetime import date

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
    Terminal,
)
from airport.serializers import (
    TerminalListSerializer,
    TerminalDetailSerializer
)
from airport.views import TerminalViewSet

TERMINAL_URL = reverse("airport:terminal-list")


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
        "latitude": 0.888,
        "longitude": 0.888
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
        "iata_code": params.pop(
            "iata_code", _unique_code(
                Airport, "iata_code", 3
            )
        ),
        "icao_code": params.pop(
            "icao_code", _unique_code(
                Airport, "icao_code", 4
            )
        ),
    }
    defaults.update(params)
    return Airport.objects.create(**defaults)


def sample_terminal(
        *,
        airport: Optional[Airport] = None,
        **params
) -> Airport:
    """Sample terminal object."""

    if airport is None:
        airport = sample_airport()

    defaults = {
        "name": "Terminal A",
        "airport": airport,
        "capacity": 1000,
        "is_international": True,
        "opened_date": date.today()
    }
    defaults.update(params)
    return Terminal.objects.create(**defaults)


def detail_url(terminal_id: int):
    """Return the detail URL"""

    return reverse("airport:terminal-detail", args=[terminal_id])


class UnauthenticatedTerminalApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(TERMINAL_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedTerminalApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.test",
            password="testpassword12345",
        )
        self.client.force_authenticate(user=self.user)

    def test_routes_list(self):
        """Test terminals list."""

        sample_terminal()

        res = self.client.get(TERMINAL_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        expected_qs = TerminalViewSet.queryset.order_by("id")
        serializer = TerminalListSerializer(expected_qs, many=True)

        self.assertEqual(res.data["results"], serializer.data)

    def test_route_detail(self):
        terminal = sample_terminal()

        url = detail_url(terminal.id)
        res = self.client.get(url)

        expected_obj = TerminalViewSet.queryset.get(pk=terminal.id)
        serializer = TerminalDetailSerializer(expected_obj)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_terminal_forbidden(self):
        """Test terminal creation forbidden."""

        airport = sample_airport()

        payload = {
            "name": "Terminal A",
            "airport": airport,
            "capacity": 1000,
            "is_international": True,
            "opened_date": date.today()
        }
        res = self.client.post(TERMINAL_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_filter_terminal_by_airport_name(self):
        """Test filtering terminals by airport name."""

        country1 = sample_country(name="United Kingdom")
        country2 = sample_country(name="Brazil")
        city1 = sample_city(country=country1, name="London")
        city2 = sample_city(country=country2, name="Rio")
        airport1 = sample_airport(
            closest_big_city=city1,
            name="London International Airport"
        )
        airport2 = sample_airport(
            closest_big_city=city2,
            name="Rio Great Airport"
        )

        terminal1 = sample_terminal(
            name="Terminal A",
            airport=airport1,
            capacity=1000,
            is_international=True,
            opened_date=date.today()
        )

        terminal2 = sample_terminal(
            name="Terminal B",
            airport=airport1,
            capacity=1000,
            is_international=True,
            opened_date=date.today()
        )

        terminal3 = sample_terminal(
            name="Terminal A",
            airport=airport2,
            capacity=1000,
            is_international=True,
            opened_date=date.today()
        )

        res = self.client.get(TERMINAL_URL, {"airport_name": "International"})

        serializer_1 = TerminalListSerializer(terminal1)
        serializer_2 = TerminalListSerializer(terminal2)
        serializer_unrelated = TerminalListSerializer(terminal3)

        self.assertIn(serializer_1.data, res.data["results"])
        self.assertIn(serializer_2.data, res.data["results"])
        self.assertNotIn(serializer_unrelated.data, res.data["results"])


class AdminTerminalApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin.test@test",
            password="admin_test_password123",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user)

    def test_create_terminal(self):
        """Test create terminal by admin"""

        airport = sample_airport()

        payload = {
            "name": "Terminal A",
            "airport": airport.id,
            "capacity": 1000,
            "is_international": True,
            "opened_date": date.today()
        }
        res = self.client.post(TERMINAL_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        terminal = Terminal.objects.get(id=res.data["id"])
        fk_map = {"airport": "airport_id"}
        for key, val in payload.items():
            model_attr = fk_map.get(key, key)
            self.assertEqual(getattr(terminal, model_attr), val)

    def test_delete_terminal(self):
        """Test delete terminal by admin"""
        terminal = sample_terminal()
        url = detail_url(terminal.id)

        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
