import os
import tempfile

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from airport.models import AirplaneType
from airport.serializers import AirplaneTypeSerializer


AIRPLANE_TYPE_URL = reverse("airport:airplanetype-list")


def sample_airplane_type(**params) -> AirplaneType:
    """Sample airplane type object."""

    defaults = {
        "name": "Boeing",
        "manufacturer": "Airplane Constructor",
    }
    defaults.update(params)
    return AirplaneType.objects.create(**defaults)


def detail_url(airplane_type_id: int):
    """Return the detail URL"""
    return reverse(
        "airport:airplanetype-detail",
        args=[airplane_type_id]
    )


def image_upload_url(airplane_type_id):
    """Return URL for recipe image upload"""
    return reverse(
        "airport:airplanetype-upload-image",
        args=[airplane_type_id]
    )


class AirplaneTypeImageUploadTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.test",
            password="testpassword12345",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user)
        self.airplane_type = sample_airplane_type()

    def tearDown(self):
        self.airplane_type.image.delete()

    def test_upload_image_to_airplane_type(self):
        """Test uploading an image to airplane type"""

        url = image_upload_url(self.airplane_type.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")
        self.airplane_type.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)
        self.assertTrue(os.path.exists(self.airplane_type.image.path))

    def test_upload_image_bad_request(self):
        """Test uploading an invalid image"""

        url = image_upload_url(self.airplane_type.id)
        res = self.client.post(url, {"image": "not image"}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_image_to_airplane_type_list(self):
        """Test posting an image to airplane type object but not list"""

        url = AIRPLANE_TYPE_URL
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(
                url,
                {
                    "name": "AirBus",
                    "manufacturer": "Airbus Constructor",
                    "image": ntf,
                },
                format="multipart",
            )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        airplane_type = AirplaneType.objects.get(name="Boeing")
        self.assertFalse(airplane_type.image)

    def test_image_url_is_shown_on_airplane_type_detail(self):
        """Test image URL is shown on airplane type detail"""

        url = image_upload_url(self.airplane_type.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(detail_url(self.airplane_type.id))

        self.assertIn("image", res.data)

    def test_image_url_is_shown_on_airplane_type_list(self):
        """Test NOT SHOW in airline list"""

        url = image_upload_url(self.airplane_type.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(AIRPLANE_TYPE_URL)

        self.assertIn("image", res.data["results"][0])


class UnauthenticatedAirplaneTypeApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(AIRPLANE_TYPE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedAirplaneTypeApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.test",
            password="testpassword12345",
        )
        self.client.force_authenticate(user=self.user)

    def test_airlines_list(self):
        sample_airplane_type()

        res = self.client.get(AIRPLANE_TYPE_URL)

        airplane_type = AirplaneType.objects.all()
        serializer = AirplaneTypeSerializer(airplane_type, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"], serializer.data)

    def test_airplane_type_detail(self):
        airplane_type = sample_airplane_type()

        url = detail_url(airplane_type.id)
        res = self.client.get(url)

        serializer = AirplaneTypeSerializer(airplane_type)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_airplane_type_forbidden(self):
        payload = {
            "name": "Boeing",
            "manufacturer": "Airplane Constructor",
        }
        res = self.client.post(AIRPLANE_TYPE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_filter_airplane_type_by_name(self):
        boeing = sample_airplane_type(
            name="Boeing 777",
            manufacturer="Airplane Boeing Constructor"
        )
        airbus = sample_airplane_type(
            name="Airbus",
            manufacturer="Airbus Constructor",

        )
        boeing2 = sample_airplane_type()

        res = self.client.get(AIRPLANE_TYPE_URL, {"name": "boein"})

        serializer_1 = AirplaneTypeSerializer(boeing)
        serializer_2 = AirplaneTypeSerializer(boeing2)
        serializer_unrelated = AirplaneTypeSerializer(airbus)

        self.assertIn(serializer_1.data, res.data["results"])
        self.assertIn(serializer_2.data, res.data["results"])
        self.assertNotIn(serializer_unrelated.data, res.data["results"])


class AdminAirplaneTypeApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin.test@test",
            password="admin_test_password123",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user)

    def test_create_airport(self):
        payload = {
            "name": "Boeing 777",
            "manufacturer": "Airplane Boeing Constructor"
        }
        res = self.client.post(AIRPLANE_TYPE_URL, payload)
        airplane_type = AirplaneType.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        for key in payload:
            self.assertEqual(payload[key], getattr(airplane_type, key))

    def test_delete_airport(self):
        airplane_type = sample_airplane_type()
        url = detail_url(airplane_type.id)

        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
