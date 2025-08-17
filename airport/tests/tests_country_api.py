from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from airport.models import Country
from airport.serializers import CountrySerializer


COUNTRY_URL = reverse("airport:country-list")


def sample_country(**params) -> Country:
    defaults = {
        "name": "Testland",
        "currency": "QWE",
        "timezone": "America/New_York",
    }
    defaults.update(params)
    return Country.objects.create(**defaults)


def detail_url(country_id: int):
    return reverse("airport:country-detail", args=[country_id])


class UnauthenticatedCountryApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(COUNTRY_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedCountryApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.test",
            password="testpassword12345",
        )
        self.client.force_authenticate(user=self.user)

    def test_country_list(self):
        sample_country()

        res = self.client.get(COUNTRY_URL)

        country = Country.objects.all()
        serializer = CountrySerializer(country, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"], serializer.data)

    def test_country_detail(self):
        country = sample_country()

        url = detail_url(country.id)
        res = self.client.get(url)

        serializer = CountrySerializer(country)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_country_forbidden(self):
        payload = {
            "name": "Testland",
            "currency": "QWE",
            "timezone": "America/New_York",
        }
        res = self.client.post(COUNTRY_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminCountryApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin.test@test",
            password="admin_test_password123",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user)

    def test_create_country(self):
        payload = {
            "name": "Testland",
            "currency": "QWE",
            "timezone": "America/New_York",
        }
        res = self.client.post(COUNTRY_URL, payload)
        country = Country.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        for key in payload:
            self.assertEqual(payload[key], getattr(country, key))

    def test_delete_country(self):
        country = sample_country()
        url = detail_url(country.id)

        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
