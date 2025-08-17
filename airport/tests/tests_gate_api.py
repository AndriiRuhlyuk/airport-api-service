from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient
from typing import Optional

from airport.models import (
    Airport,
    Country,
    City,
    Terminal,
    Gate
)
from airport.serializers import (
    GateListSerializer,
    GateDetailSerializer
)


GATE_URL = reverse("airport:gate-list")


def sample_country(**params) -> Country:
    defaults = {
        "name": "Testland",
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
    if country is None:
        country = sample_country()
    defaults = {
        "name": "Test City",
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
    if city is None:
        city = sample_city()
    defaults = {
        "name": "Test Airport",
        "closest_big_city": city,
        "iata_code": "EWQ",
        "icao_code": "QWER",
    }
    defaults.update(params)
    return Airport.objects.create(**defaults)


def sample_terminal(
        *,
        airport: Optional[Airport] = None,
        **params
) -> Terminal:
    if airport is None:
        airport = sample_airport()
    defaults = {
        "name": "Test Terminal",
        "airport": airport,
        "capacity": 1000,
        "is_international": True,
        "opened_date": timezone.now(),
    }
    defaults.update(params)
    return Terminal.objects.create(**defaults)


def sample_gate(*, terminal: Optional[Terminal] = None, **params) -> Terminal:
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


def detail_url(gate_id: int):
    return reverse("airport:gate-detail", args=[gate_id])


class UnauthenticatedGateApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(GATE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedGateApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.test",
            password="testpassword12345",
        )
        self.client.force_authenticate(user=self.user)

    def test_gates_list(self):
        sample_gate()

        res = self.client.get(GATE_URL)

        airports = Gate.objects.all()
        serializer = GateListSerializer(airports, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"], serializer.data)

    def test_gate_detail(self):
        gate = sample_gate()

        url = detail_url(gate.id)
        res = self.client.get(url)

        serializer = GateDetailSerializer(gate)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_gate_forbidden(self):
        terminal = sample_terminal()
        payload = {
            "number": "A2",
            "terminal": terminal,
            "gate_type": "MIXED",
            "is_active": True,
        }
        res = self.client.post(GATE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminAirportApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin.test@test",
            password="admin_test_password123",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user)

    def test_create_airport(self):
        terminal = sample_terminal()
        payload = {
            "number": "A2",
            "terminal": terminal.id,
            "gate_type": "MIXED",
            "is_active": True,
        }
        res = self.client.post(GATE_URL, payload)
        gate = Gate.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        fk_map = {"terminal": "terminal_id"}
        for key, val in payload.items():
            model_attr = fk_map.get(key, key)
            self.assertEqual(getattr(gate, model_attr), val)

    def test_delete_airport(self):
        gate = sample_gate()
        url = detail_url(gate.id)

        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
