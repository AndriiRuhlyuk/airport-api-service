import json
import random
import string
from uuid import uuid4
from datetime import date

from decimal import Decimal
from datetime import timedelta

from django.db.models import Prefetch
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient
from typing import Optional

from airport.models import (
    Order,
    Ticket,
    Flight,
    Country,
    City,
    Airport,
    Airline,
    AirplaneType,
    Airplane,
    Route,
    Terminal,
    Gate,
    FlightStatus
)
from airport.serializers import (
    OrderListSerializer,
    OrderDetailSerializer
)


ORDER_URL = reverse("airport:order-list")


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
        "latitude": params.pop(
            "latitude",
            50.0 + random.uniform(-1, 1)
        ),
        "longitude": params.pop(
            "longitude",
            30.0 + random.uniform(-1, 1)
        )
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

    departure = params.pop("departure_time", timezone.now())
    arrival = params.pop("arrival_time", departure + timedelta(days=1))

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


def order_detail_url(pk: int):
    return reverse("airport:order-detail", args=[pk])


class UnauthenticatedOrderApiTests(TestCase):
    """Unauthenticated order API tests."""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(ORDER_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedOrderApiTests(TestCase):
    """Authenticated order API tests."""
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user@test.test",
            password="testpass123",
        )
        self.client.force_authenticate(self.user)

        dep = timezone.now() + timedelta(hours=1)
        arr = dep + timedelta(hours=2)
        self.flight = sample_flight(
            departure_time=dep,
            arrival_time=arr,
            price=Decimal("250.00"),
        )

    def _make_order_payload(self, flight: Flight, tickets_list):
        return {
            "flight": flight.id,
            "tickets": [json.dumps(tickets_list)],
        }

    def test_create_order_success(self):
        payload = self._make_order_payload(
            self.flight,
            [{"row": 1, "seat": 1}, {"row": 1, "seat": 2}]
        )

        res = self.client.post(ORDER_URL, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        order_id = res.data["id"]

        order = Order.objects.select_related(
            "flight"
        ).prefetch_related("tickets").get(pk=order_id)
        self.assertEqual(order.user_id, self.user.id)
        self.assertEqual(order.total_price, self.flight.price * 2)
        self.assertEqual(
            sorted(
                (
                    ticket_o.row,
                    ticket_o.seat
                ) for ticket_o in order.tickets.all()
                   ),
            [(1, 1), (1, 2)])

    def test_create_order_conflict_with_taken_seat(self):
        first = self.client.post(
            ORDER_URL,
            self._make_order_payload(
                self.flight,
                [{"row": 2, "seat": 1}]),
            format="json",
        )
        self.assertEqual(
            first.status_code,
            status.HTTP_201_CREATED,
            first.data
        )

        res = self.client.post(
            ORDER_URL,
            self._make_order_payload(
                self.flight,
                [{"row": 2, "seat": 1}]),
            format="json",
        )
        self.assertEqual(
            res.status_code,
            status.HTTP_400_BAD_REQUEST,
            res.data
        )
        self.assertIn("tickets", res.data)

    def test_list_shows_only_own_orders(self):
        mine = self.client.post(
            ORDER_URL,
            self._make_order_payload(
                self.flight,
                [{"row": 1, "seat": 1}]
            ),
            format="json",
        )
        self.assertEqual(mine.status_code, status.HTTP_201_CREATED, mine.data)

        other_user = get_user_model().objects.create_user(
            email="other@test.test", password="pass12345"
        )
        other_order = Order.objects.create(
            user=other_user,
            flight=self.flight,
            total_price=self.flight.price
        )
        Ticket.objects.create(
            order=other_order,
            flight=self.flight,
            row=5,
            seat=5,
            price=self.flight.price
        )

        res = self.client.get(ORDER_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        ids = {item["id"] for item in res.data["results"]}
        self.assertIn(mine.data["id"], ids)
        self.assertNotIn(other_order.id, ids)

        expected_qs = (
            Order.objects
            .select_related(
                "flight__route__source",
                "flight__route__destination",
                "user"
            )
            .prefetch_related("tickets")
            .filter(user=self.user)
            .order_by("id")
        )
        expected = OrderListSerializer(expected_qs, many=True).data
        self.assertEqual(res.data["results"], expected)

    def test_retrieve_own_order(self):
        res_create = self.client.post(
            ORDER_URL,
            self._make_order_payload(self.flight, [{"row": 7, "seat": 7}]),
            format="json",
        )
        order_id = res_create.data["id"]

        res = self.client.get(order_detail_url(order_id))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        expected_obj = (
            Order.objects
            .select_related(
                "flight__route__source",
                "flight__route__destination",
                "user")
            .prefetch_related(
                Prefetch(
                    "tickets",
                    queryset=Ticket.objects.select_related(
                        "flight",
                        "flight__route",
                        "flight__route__source",
                        "flight__route__destination"
                    )
                    .order_by(
                        "row",
                        "seat"
                    )
                )
            )
            .get(pk=order_id)
        )
        self.assertEqual(res.data, OrderDetailSerializer(expected_obj).data)

    def test_retrieve_other_users_order_forbidden(self):
        other_user = get_user_model().objects.create_user(
            email="other2@test.test", password="pass12345"
        )
        order = Order.objects.create(
            user=other_user,
            flight=self.flight,
            total_price=self.flight.price
        )
        Ticket.objects.create(
            order=order,
            flight=self.flight,
            row=9,
            seat=9,
            price=self.flight.price
        )

        res = self.client.get(order_detail_url(order.id))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_tickets_conflict_fails(self):
        other_user = get_user_model().objects.create_user(
            email="other3@test.test",
            password="pass12345"
        )
        foreign_order = Order.objects.create(
            user=other_user,
            flight=self.flight,
            total_price=self.flight.price
        )
        Ticket.objects.create(
            order=foreign_order,
            flight=self.flight,
            row=4,
            seat=4,
            price=self.flight.price
        )

        res_create = self.client.post(
            ORDER_URL,
            self._make_order_payload(
                self.flight,
                [{"row": 3, "seat": 3}]
            ),
            format="json",
        )
        oid = res_create.data["id"]

        res = self.client.patch(
            order_detail_url(oid),
            {"tickets": json.dumps([{"row": 4, "seat": 4}])},
            format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("tickets", res.data)


class AdminOrderApiTests(TestCase):
    """Tests Admin work with orders"""

    def setUp(self):
        self.client = APIClient()
        self.admin = get_user_model().objects.create_user(
            email="admin@test.test",
            password="adminpass123",
            is_staff=True,
        )
        self.client.force_authenticate(self.admin)

        self.user1 = get_user_model().objects.create_user(
            email="u1@test.test", password="pass123"
        )
        self.user2 = get_user_model().objects.create_user(
            email="u2@test.test", password="pass123"
        )
        dep = timezone.now() + timedelta(hours=1)
        arr = dep + timedelta(hours=2)
        self.flight = sample_flight(
            departure_time=dep,
            arrival_time=arr,
            price=Decimal("99.00")
        )

        self.order1 = Order.objects.create(
            user=self.user1,
            flight=self.flight,
            total_price=self.flight.price
        )
        Ticket.objects.create(
            order=self.order1,
            flight=self.flight,
            row=1,
            seat=1,
            price=self.flight.price
        )

        self.order2 = Order.objects.create(
            user=self.user2,
            flight=self.flight,
            total_price=self.flight.price
        )
        Ticket.objects.create(
            order=self.order2,
            flight=self.flight,
            row=2,
            seat=2,
            price=self.flight.price
        )

    def test_admin_can_list_all_orders(self):
        """Test that admin can see list all orders"""

        res = self.client.get(ORDER_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        expected_qs = (
            Order.objects
            .select_related(
                "flight__route__source",
                "flight__route__destination",
                "user"
            )
            .prefetch_related("tickets")
            .order_by("id")
        )
        self.assertEqual(
            res.data["results"],
            OrderListSerializer(expected_qs, many=True).data
        )

    def test_admin_can_retrieve_any_order(self):
        """Test that admin can see detail a specific any order"""

        res = self.client.get(order_detail_url(self.order1.id))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        expected_obj = (
            Order.objects
            .select_related(
                "flight__route__source",
                "flight__route__destination",
                "user"
            )
            .prefetch_related(
                Prefetch(
                    "tickets",
                    queryset=Ticket.objects.select_related(
                        "flight",
                        "flight__route",
                        "flight__route__source",
                        "flight__route__destination",
                    ).order_by("row", "seat")
                )
            )
            .get(pk=self.order1.id)
        )
        self.assertEqual(res.data, OrderDetailSerializer(expected_obj).data)
