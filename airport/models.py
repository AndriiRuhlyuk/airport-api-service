import pathlib
import uuid

from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import ForeignKey
from django.utils.text import slugify
from geopy.distance import geodesic
from rest_framework.exceptions import ValidationError

from user.models import User



class Country(models.Model):
    """Country model"""

    name = models.CharField(max_length=100, unique=True)
    currency = models.CharField(max_length=3, blank=True)
    timezone = models.CharField(max_length=50, blank=True)

    class Meta:
        verbose_name_plural = "countries"
        ordering = ("id",)

    def __str__(self):
        return self.name


class City(models.Model):
    """City model"""

    name = models.CharField(max_length=100)
    country = models.ForeignKey(
        Country, on_delete=models.CASCADE, related_name="cities"
    )
    population = models.PositiveIntegerField(null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "cities"
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(
                fields=["name", "country"], name="unique_city_country"
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.country.name})"


def airline_logo_path(
        instance: "Airline",
        filename: str
) -> pathlib.Path:
    filename = (
        f"{slugify(instance.code)}-{uuid.uuid4()}" + pathlib.Path(filename).suffix
    )
    return pathlib.Path("upload/airline/") / pathlib.Path(filename)


class Airline(models.Model):
    """Airline model"""

    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)
    country = models.ForeignKey(
        Country, on_delete=models.CASCADE, related_name="airlines"
    )
    founded_year = models.PositiveIntegerField(
        validators=[MinValueValidator(1900), MaxValueValidator(2025)],
        null=True,
        blank=True,
    )
    logo = models.ImageField(null=True, upload_to=airline_logo_path)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("id",)

    def __str__(self):
        return f"{self.name} ({self.code})"


class Airport(models.Model):
    """Airport model"""

    name = models.CharField(max_length=100)
    closest_big_city = models.ForeignKey(
        City, on_delete=models.CASCADE, related_name="airports"
    )
    iata_code = models.CharField(max_length=3, unique=True, blank=True)
    icao_code = models.CharField(max_length=4, unique=True, blank=True)

    class Meta:
        verbose_name_plural = "airports"
        ordering = ("id",)

    def __str__(self):
        return f"{self.name} ({self.closest_big_city.name})"


class FlightStatus(models.Model):
    """Flight status"""

    STATUS_CHOICES = [
        ("SCHEDULED", "Scheduled"),
        ("BOARDING", "Boarding"),
        ("IN_FLIGHT", "In Flight"),
        ("LANDED", "Landed"),
        ("DELAYED", "Delayed"),
        ("CANCELLED", "Cancelled"),
        ("DIVERTED", "Diverted"),
    ]

    name = models.CharField(max_length=20, choices=STATUS_CHOICES)
    description = models.TextField(blank=True)
    color_code = models.CharField(max_length=7, blank=True)  # HEX color #FF0000

    class Meta:
        verbose_name_plural = "flight statuses"

    def __str__(self):
        return self.get_name_display()


class Terminal(models.Model):
    """Airports terminal"""

    name = models.CharField(max_length=50)
    airport = models.ForeignKey(
        "Airport", on_delete=models.CASCADE, related_name="terminals"
    )
    capacity = models.PositiveIntegerField(help_text="Max passengers q-ty per hour")
    is_international = models.BooleanField(default=False)
    opened_date = models.DateField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "airport"], name="unique_terminal_airport"
            ),
        ]
        ordering = ("name",)

    def __str__(self):
        """
        STR method for fix N+1 problem in POST Form
        """

        if hasattr(self, "_prefetched_objects_cache") or hasattr(self, "airport"):
            try:
                return f"{self.airport.name} – {self.name}"
            except:
                pass

        return f"Terminal {self.name} (Airport #{self.airport_id})"


class Gate(models.Model):
    """
    Boarding gates for flights
    """

    GATE_TYPES = [
        ("DOMESTIC", "Internal flights"),
        ("INTERNATIONAL", "International flights"),
        ("MIXED", "Mixed flights"),
    ]

    number = models.CharField(max_length=10)
    terminal = models.ForeignKey(
        Terminal,
        on_delete=models.CASCADE,
        related_name="gates"
    )
    gate_type = models.CharField(
        max_length=15,
        choices=GATE_TYPES,
        default="MIXED"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["number", "terminal"],
                name="unique_gate_terminal"
            ),
        ]
        ordering = ("number",)

    @staticmethod
    def validate_gate_type(terminal, gate_type):
        """Validate gate type based on terminal's international status"""

        if terminal.is_international and gate_type not in ["INTERNATIONAL", "MIXED"]:
            raise ValidationError(
                {
                    "gate_type": "International terminal can only have INTERNATIONAL or MIXED gates."
                }
            )

        if not terminal.is_international and gate_type not in ["DOMESTIC", "MIXED"]:
            raise ValidationError(
                {
                    "gate_type": "Domestic terminal can only have DOMESTIC or MIXED gates."
                }
            )

    def clean(self):
        """Run field-level validation and call external gate_type validation"""
        super().clean()

        if self.terminal and self.gate_type:
            self.validate_gate_type(self.terminal, self.gate_type)

    def save(self, *args, **kwargs):
        """
        Save without full_clean, as validation is handled
        by serializer's validate method.
        """

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.terminal.airport.name} - {self.terminal.name}"


class Route(models.Model):
    """Route model"""

    source = ForeignKey(
        Airport, on_delete=models.CASCADE, related_name="departure_routes"
    )
    destination = ForeignKey(
        Airport, on_delete=models.CASCADE, related_name="arrival_routes"
    )
    distance = models.PositiveIntegerField(editable=False)

    class Meta:
        indexes = [
            models.Index(fields=["source", "destination"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["source", "destination"], name="unique_route"
            ),
            models.CheckConstraint(
                check=~models.Q(source=models.F("destination")),
                name="different_airports",
            ),
        ]
        verbose_name_plural = "routes"
        ordering = ("id",)

    def save(self, *args, **kwargs):
        """
        Automatically calculate the distance based on the closest big city for each airport.
        """

        city_source = getattr(self.source, "closest_big_city", None)
        city_destination = getattr(self.destination, "closest_big_city", None)

        if (not city_source or not city_destination or not city_source.latitude
                or not city_source.longitude or not city_destination.latitude
                or not city_destination.longitude):
            raise ValueError(
                "Cannot calculate distance: missing coordinates for source or destination city."
            )

        coords_source = (city_source.latitude, city_source.longitude)
        coords_destination = (city_destination.latitude, city_destination.longitude)

        self.distance = round(geodesic(coords_source, coords_destination).km)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.source.name} -> {self.destination.name} ({self.distance}) km"


def airplane_type_image_path(
        instance: "AirplaneType",
        filename: str
) -> pathlib.Path:
    filename = (
        f"{slugify(instance.name)}-{uuid.uuid4()}" + pathlib.Path(filename).suffix
    )
    return pathlib.Path("upload/airplane_types/") / pathlib.Path(filename)


class AirplaneType(models.Model):
    """Airplane type model"""

    name = models.CharField(max_length=100, unique=True)
    manufacturer = models.CharField(max_length=100, blank=True)
    image = models.ImageField(null=True, upload_to=airplane_type_image_path)

    class Meta:
        verbose_name_plural = "airplane_types"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Airplane(models.Model):
    """Airplane model"""

    name = models.CharField(max_length=100)
    rows = models.IntegerField(validators=[MinValueValidator(1)])
    seats_in_row = models.IntegerField(validators=[MinValueValidator(1)])
    airplane_type = ForeignKey(
        AirplaneType, on_delete=models.CASCADE, related_name="airplanes"
    )
    airline = models.ForeignKey(
        Airline, on_delete=models.CASCADE, related_name="airplanes"
    )
    registration_number = models.CharField(max_length=20, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "airplanes"
        ordering = ["name"]

    def __str__(self):
        return f"Airplane: {self.name} ({self.airplane_type.name})"


class Flight(models.Model):
    """Flight model"""

    route = ForeignKey(Route, on_delete=models.CASCADE)
    airplane = models.ForeignKey(Airplane, on_delete=models.CASCADE)
    departure_time = models.DateTimeField()
    arrival_time = models.DateTimeField()
    status = models.ForeignKey(
        FlightStatus,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=1,  # SCHEDULED
    )
    departure_gate = models.ForeignKey(
        Gate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="departure_flights",
    )
    arrival_gate = models.ForeignKey(
        Gate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="arrival_flights",
    )
    flight_number = models.CharField(max_length=10)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True)

    @property
    def flight_time(self):
        if self.arrival_time and self.departure_time:
            flight_time = self.arrival_time - self.departure_time
            return round(flight_time.total_seconds() / 3600, 2)
        return None

    class Meta:
        verbose_name_plural = "flights"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["flight_number", "departure_time"],
                name="unique_flight_number_time",
            ),
            models.CheckConstraint(
                check=models.Q(departure_time__lt=models.F("arrival_time")),
                name="departure_before_arrival",
            ),
        ]

    def __str__(self):
        return f"{self.flight_number}: {self.route.source.name} -> {self.route.destination.name} ({self.flight_time}h)"


class Crew(models.Model):
    """Crew model"""

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    flights = models.ManyToManyField(Flight, blank=True)

    class Meta:
        verbose_name_plural = "crews"

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Order(models.Model):
    """Order model"""

    created_at = models.DateTimeField(auto_now_add=True)
    flight = models.ForeignKey(Flight, on_delete=models.CASCADE, related_name="orders")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.id} - {self.user.email} ({self.created_at.date()})"


class Ticket(models.Model):
    """Ticket model"""

    row = models.IntegerField(validators=[MinValueValidator(1)])
    seat = models.IntegerField(validators=[MinValueValidator(1)])
    flight = models.ForeignKey(Flight, on_delete=models.CASCADE, related_name="tickets")
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="tickets")
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["row", "seat", "flight"], name="unique_ticket_row_seat_flight"
            ),
        ]
        ordering = ["seat", "row"]
        verbose_name_plural = "tickets"

    @staticmethod
    def validate_seat(seat: int, num_seats: int, error_to_rise):
        if not (1 <= seat <= num_seats):
            raise error_to_rise(
                {"seat": f"seat must be in range [1, {num_seats}], not {seat}"}
            )

    @staticmethod
    def validate_row(row: int, num_rows: int, error_to_rise):
        if not (1 <= row <= num_rows):
            raise error_to_rise(
                {"row": f"row must be in range [1, {num_rows}], not {row}"}
            )

    def clean(self):
        super().clean()
        if not self.flight_id:
            return
        airplane = self.flight.airplane
        Ticket.validate_seat(self.seat, airplane.seats_in_row, ValidationError)
        Ticket.validate_row(self.row, airplane.rows, ValidationError)

        if hasattr(self.order, "flight_id") and self.order.flight_id and self.order.flight_id != self.flight_id:
            raise ValidationError({"order": "Order.flight should be equal Ticket.flight."})

    def save(
            self,
            *args,
            force_insert=False,
            force_update=False,
            using=None,
            update_fields=None
    ):
        self.full_clean()
        return super(Ticket, self).save(
            force_insert, force_update, using, update_fields
        )

    def __str__(self):
        return f"Ticket {self.flight.flight_number} - Row {self.row}, Seat {self.seat}"
