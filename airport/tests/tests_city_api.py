from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from types import SimpleNamespace
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient
from typing import Optional

from airport.models import Country, City
from airport.serializers import CitySerializer, CityDetailSerializer

CITY_URL = reverse("airport:city-list")


def sample_country(**params) -> Country:
    defaults = {
        "name": "Testland",
        "currency": "QWE",
        "timezone": "America/New_York",
    }
    defaults.update(params)
    return Country.objects.create(**defaults)


def sample_city(*, country: Optional[Country] = None, **params) -> City:
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


def detail_url(city_id: int):
    return reverse("airport:city-detail", args=[city_id])


class UnauthenticatedCityApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(CITY_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedAirportApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.test",
            password="testpassword12345",
        )
        self.client.force_authenticate(user=self.user)

    def test_cities_list(self):
        sample_city()

        res = self.client.get(CITY_URL)

        cities = City.objects.all()
        serializer = CitySerializer(cities, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"], serializer.data)

    def test_airports_detail(self):
        city = sample_city()

        url = detail_url(city.id)
        res = self.client.get(url)

        serializer = CityDetailSerializer(city)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_airport_forbidden(self):
        country = sample_country()
        payload = {
            "name": "Test City",
            "country": country,
            "population": 1000,
            "latitude": 0.888,
            "longitude": 0.888
        }
        res = self.client.post(CITY_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminCityApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin.test@test",
            password="admin_test_password123",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user)

    @patch("airport.serializers.Nominatim.geocode")
    def test_create_city(self, geocode_mock):
        country = sample_country()
        geocode_mock.return_value = SimpleNamespace(
            latitude=0.888,
            longitude=0.888
        )
        payload = {
            "name": "Test City",
            "country": country.name,
            "population": 1000,
        }
        res = self.client.post(CITY_URL, payload)
        city = City.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(city.name, payload["name"])
        self.assertEqual(city.country_id, country.id)

    def test_delete_airport(self):
        city = sample_city()
        url = detail_url(city.id)

        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
