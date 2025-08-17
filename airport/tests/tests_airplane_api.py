import tempfile

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient
from typing import Optional
from django.db.models import F

from airport.models import (
    AirplaneType,
    Airline,
    Airplane,
    Country
)
from airport.serializers import (
    AirplaneDetailSerializer,
    AirplaneListSerializer
)


AIRPLANE_URL = reverse("airport:airplane-list")


def sample_country(**params) -> Country:
    """Sample country object."""

    defaults = {
        "name": "Testland",
        "currency": "QWE",
        "timezone": "America/New_York",
    }
    defaults.update(params)
    return Country.objects.create(**defaults)


def sample_airline(
        *,
        country: Optional[Country] = None,
        **params
) -> Airline:
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


def sample_airplane_type(**params) -> AirplaneType:
    """Sample airplane type object."""

    defaults = {
        "name": "Boeing",
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
        "registration_number": "QWERTY",
        "is_active": True,
    }
    defaults.update(params)
    return Airplane.objects.create(**defaults)


def detail_url(airline_id: int):
    """Return the detail URL"""
    return reverse(
        "airport:airplane-detail",
        args=[airline_id]
    )


def image_upload_url(airplane_type_id: int):
    """Return URL for recipe image upload"""
    return reverse(
        "airport:airplanetype-upload-image",
        args=[airplane_type_id]
    )


class AirplaneImageShowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.test",
            password="testpassword12345",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user)
        self.airplane: Airplane = sample_airplane()
        self.airplane_type = self.airplane.airplane_type

    def _upload_type_logo_via_endpoint(self):
        url = image_upload_url(self.airplane_type.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(
                url,
                {"image": ntf},
                format="multipart"
            )
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.airplane_type.refresh_from_db()

    def test_image_url_is_shown_on_airplane_detail_from_airplane_type(self):
        """У деталі літака всередині airplane_type є поле image (URL)."""
        self._upload_type_logo_via_endpoint()

        res = self.client.get(detail_url(self.airplane.id))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertIn("airplane_type", res.data)
        self.assertIsInstance(res.data["airplane_type"], dict)
        self.assertIn("image", res.data["airplane_type"])
        self.assertTrue(res.data["airplane_type"]["image"])

    def test_image_not_shown_in_airplane_list(self):
        """In airplane list image field not show"""

        res = self.client.get(AIRPLANE_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        results = res.data["results"] if isinstance(
            res.data,
            dict
        ) else res.data
        item = next(x for x in results if x["id"] == self.airplane.id)

        self.assertIsInstance(item["airplane_type"], str)
        self.assertNotIn("image", item)


class UnauthenticatedAirlineApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(AIRPLANE_URL)
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
        sample_airplane()

        res = self.client.get(AIRPLANE_URL)

        annot_airplane = Airplane.objects.select_related(
            "airplane_type",
            "airline"
        ).annotate(
            num_seats=F("rows") * F("seats_in_row")
        )

        serializer = AirplaneListSerializer(annot_airplane, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"], serializer.data)

    def test_airplane_detail(self):
        airplane = sample_airplane()

        url = detail_url(airplane.id)
        res = self.client.get(url)

        serializer = AirplaneDetailSerializer(airplane)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_airline_forbidden(self):
        airline = sample_airline(country=sample_country())
        airplane_type = sample_airplane_type()
        payload = {
            "name": "Airplane101",
            "rows": 10,
            "seats_in_row": 10,
            "airplane_type": airplane_type,
            "airline": airline,
            "registration_number": "QWERTY",
            "is_active": True,
        }
        res = self.client.post(AIRPLANE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


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
        airline = sample_airline(country=sample_country())
        airplane_type = sample_airplane_type()
        payload = {
            "name": "Airplane101",
            "rows": 10,
            "seats_in_row": 10,
            "airplane_type": airplane_type.id,
            "airline": airline.id,
            "registration_number": "QWERTY",
            "is_active": True,
        }

        res = self.client.post(AIRPLANE_URL, payload)
        airplane = Airplane.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        fk_map = {
            "airline": "airline_id",
            "airplane_type": "airplane_type_id"
        }
        for key, val in payload.items():
            model_attr = fk_map.get(key, key)
            self.assertEqual(getattr(airplane, model_attr), val)

    def test_delete_airport(self):
        airplane = sample_airplane()
        url = detail_url(airplane.id)

        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
