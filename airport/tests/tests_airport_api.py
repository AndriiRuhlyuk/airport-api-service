from django.contrib.auth import get_user_model
from django.db.models import Count
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
    Terminal
)
from airport.serializers import (
    AirportListSerializer,
    AirportDetailSerializer
)


AIRPORT_URL = reverse("airport:airport-list")


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


def sample_terminals(
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


def detail_url(airport_id: int):
    return reverse(
        "airport:airport-detail",
        args=[airport_id]
    )


class UnauthenticatedAirportApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(AIRPORT_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedAirportApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.test",
            password="testpassword12345",
        )
        self.client.force_authenticate(user=self.user)

    def test_airports_list(self):
        sample_airport()

        res = self.client.get(AIRPORT_URL)

        airports = Airport.objects.all()
        serializer = AirportListSerializer(airports, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"], serializer.data)

    def test_airports_detail(self):
        airport = sample_airport()
        sample_terminals(airport=airport)
        sample_terminals(name="Test1 Name", airport=airport)

        url = detail_url(airport.id)
        res = self.client.get(url)

        airport_annot = (
            Airport.objects
            .select_related("closest_big_city__country")
            .annotate(terminals_count=Count("terminals"))
            .get(pk=airport.id)
        )

        serializer = AirportDetailSerializer(airport_annot)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)
        self.assertEqual(res.data["terminals_count"], 2)

    def test_create_airport_forbidden(self):
        city = sample_city()
        payload = {
            "name": "Test Airport",
            "closest_big_city": city,
            "iata_code": "EWQ",
            "icao_code": "QWER",
        }
        res = self.client.post(AIRPORT_URL, payload)

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
        city = sample_city()
        payload = {
            "name": "Test Airport",
            "closest_big_city": city.id,
            "iata_code": "EWQ",
            "icao_code": "QWER",
        }
        res = self.client.post(AIRPORT_URL, payload)
        airport = Airport.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        fk_map = {"closest_big_city": "closest_big_city_id"}
        for key, val in payload.items():
            model_attr = fk_map.get(key, key)
            self.assertEqual(getattr(airport, model_attr), val)

    def test_delete_airport(self):
        airport = sample_airport()
        url = detail_url(airport.id)

        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
