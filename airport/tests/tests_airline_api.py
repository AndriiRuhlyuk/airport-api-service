import os
import tempfile

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient
from typing import Optional

from airport.models import Country, Airline
from airport.serializers import AirlineDetailSerializer, AirlineListSerializer


AIRLINE_URL = reverse("airport:airline-list")

def sample_country(**params) -> Country:
    """Sample country object."""

    defaults = {
        "name": "Testland",
        "currency": "QWE",
        "timezone": "America/New_York",
    }
    defaults.update(params)
    return Country.objects.create(**defaults)

def sample_airline(*, country: Optional[Country] = None, **params) -> Airline:
    """Sample airline object."""

    if country is None:
        country = sample_country()
    defaults = {
        "name": "Test Airline",
        "code": "POI",
        "country": country,
        "founded_year": 1900,
        "is_active": True,
    }
    defaults.update(params)
    return Airline.objects.create(**defaults)

def detail_url(airline_id: int):
    """Return the detail URL"""
    return reverse("airport:airline-detail", args=[airline_id])

def image_upload_url(airline_id):
    """Return URL for recipe image upload"""
    return reverse("airport:airline-upload-image", args=[airline_id])


class AirlineImageUploadTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.test",
            password="testpassword12345",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user)
        self.country = sample_country()
        self.airline = sample_airline(country=self.country)

    def tearDown(self):
        self.airline.logo.delete()

    def test_upload_image_to_airline(self):
        """Test uploading an image to airline"""

        url = image_upload_url(self.airline.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"logo": ntf}, format="multipart")
        self.airline.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("logo", res.data)
        self.assertTrue(os.path.exists(self.airline.logo.path))

    def test_upload_image_bad_request(self):
        """Test uploading an invalid image"""

        url = image_upload_url(self.airline.id)
        res = self.client.post(url, {"logo": "not image"}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_image_to_airline_list(self):
        """Test posting an image to airline object but not list"""

        url = AIRLINE_URL
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(
                url,
                {
                    "name": "Test1 Airline",
                    "code": "IOP",
                    "country": sample_country(name="Test1land"),
                    "founded_year": 1900,
                    "is_active": True,
                    "logo": ntf,
                },
                format="multipart",
            )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        airline = Airline.objects.get(name="Test Airline")
        self.assertFalse(airline.logo)

    def test_image_url_is_shown_on_airline_detail(self):
        """Test image URL is shown on airline detail"""

        url = image_upload_url(self.airline.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"logo": ntf}, format="multipart")
        res = self.client.get(detail_url(self.airline.id))

        self.assertIn("logo", res.data)

    def test_image_url_not_is_shown_on_airline_list(self):
        """Test NOT SHOW in airline list"""

        url = image_upload_url(self.airline.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"logo": ntf}, format="multipart")
        res = self.client.get(AIRLINE_URL)

        self.assertNotIn("logo", res.data["results"])


class UnauthenticatedAirlineApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(AIRLINE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedAirlineApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.test",
            password="testpassword12345",
        )
        self.client.force_authenticate(user=self.user)

    def test_airlines_list(self):
        sample_airline()

        res = self.client.get(AIRLINE_URL)

        airline = Airline.objects.all()
        serializer = AirlineListSerializer(airline, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"], serializer.data)

    def test_airline_detail(self):
        airline = sample_airline()

        url = detail_url(airline.id)
        res = self.client.get(url)

        serializer = AirlineDetailSerializer(airline)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_airline_forbidden(self):
        country = sample_country(name="Test land")
        payload = {
            "name": "Test1 Airline",
            "code": "POI",
            "country": country,
            "founded_year": 1900,
            "is_active": True,
        }
        res = self.client.post(AIRLINE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_filter_airline_by_country(self):
        country1 = sample_country(name="Ukraine")
        airline1 = sample_airline(
            name="MAU",
            code="HGJ",
            country=country1,
            founded_year=1800,
            is_active=True,
        )
        country2 = sample_country(name="UK")
        airline2 = sample_airline(
            name="England Airline",
            code="LDU",
            country=country2,
            founded_year=1700,
            is_active=True,
        )
        airline_3 = sample_airline()

        res = self.client.get(AIRLINE_URL, {"country": "uk"})

        serializer_1 = AirlineListSerializer(airline1)
        serializer_2 = AirlineListSerializer(airline2)
        serializer_unrelated = AirlineListSerializer(airline_3)

        self.assertIn(serializer_1.data, res.data["results"])
        self.assertIn(serializer_2.data, res.data["results"])
        self.assertNotIn(serializer_unrelated.data, res.data["results"])


class AdminAirlineApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin.test@test",
            password="admin_test_password123",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user)

    def test_create_airport(self):
        country = sample_country(name="Test land")
        payload = {
            "name": "Test1 Airline",
            "code": "POI",
            "country": country,
            "founded_year": 1900,
            "is_active": True,
        }
        res = self.client.post(AIRLINE_URL, payload)
        airline = Airline.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        for key in payload:
            self.assertEqual(payload[key], getattr(airline, key))

    def test_delete_airport(self):
        airline = sample_airline()
        url = detail_url(airline.id)

        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
