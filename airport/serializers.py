import json

from django.utils.functional import cached_property
from rest_framework.exceptions import ValidationError
from django.db import transaction
from geopy import Nominatim
from geopy.exc import GeocoderTimedOut
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
from airport.custom_fields import (
    RepresentationChoiceField,
    OptimizedRelatedField,
    BulkManyPrimaryKeyRelatedField,
    CustomPrimaryKeyRelatedField,
)

from airport.models import (
    Country,
    City,
    Airline,
    Airport,
    AirplaneType,
    Airplane,
    Terminal,
    Gate,
    Route,
    FlightStatus,
    Flight,
    Crew,
    Ticket,
    Order,
)


class CountrySerializer(serializers.ModelSerializer):
    """Country model serializer"""

    class Meta:
        model = Country
        fields = ("id", "name", "currency", "timezone")


class CitySerializer(serializers.ModelSerializer):
    """City model serializer"""

    country = serializers.SlugRelatedField(
        queryset=Country.objects.all(),
        slug_field="name",
    )

    class Meta:
        model = City
        fields = (
            "id",
            "name",
            "country",
            "population",
            "latitude",
            "longitude",
        )
        read_only_fields = ("id", "latitude", "longitude",)
        validators = [
            UniqueTogetherValidator(
                queryset=City.objects.all(),
                fields=["name", "country"],
                message="This city already exists in this country.",
            )
        ]

    def validate(self, data):
        """
        This method is called when serializer.is_valid() is run.
        It tries to find coordinates for the given city and country.
        """

        geolocator = Nominatim(user_agent="city_validator_airport", timeout=10)
        name = data.get("name")
        country = data.get("country")

        try:
            query = f"{name}, {country.name}"
            location = geolocator.geocode(query)

            if location:
                data["latitude"] = location.latitude
                data["longitude"] = location.longitude
                return data
            else:
                raise serializers.ValidationError(
                    f"Could not find coordinates for '{name}, {country}'. "
                    f"Please check the spelling or try a different name."
                )

        except GeocoderTimedOut:
            raise serializers.ValidationError("The geocoding service timed out. Please try again.")
        except Exception as e:
            raise serializers.ValidationError(f"An error occurred during geocoding: {e}")


class CityDetailSerializer(CitySerializer):
    """City list model serializer"""

    country = CountrySerializer(read_only=True)


class AirlineSerializer(serializers.ModelSerializer):
    """Airline Base Serializer"""

    country = serializers.SlugRelatedField(
        slug_field="name", queryset=Country.objects.all()
    )

    class Meta:
        model = Airline
        fields = ("id", "name", "code", "country", "founded_year", "logo", "is_active")


class AirlineListSerializer(AirlineSerializer):
    """Airline list serializer"""

    class Meta:
        model = Airline
        fields = ("id", "name", "country", "is_active")


class AirlineDetailSerializer(AirlineSerializer):
    """Airline detail serializer"""

    airplanes_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Airline
        fields = (
            "id",
            "name",
            "code",
            "country",
            "founded_year",
            "logo",
            "is_active",
            "airplanes_count",
        )

    def get_airplanes_count(self, obj):
        """Count the number of airplanes on the airline"""

        return obj.airplanes.count() if hasattr(obj, "airplanes") else 0


class AirlineLogoSerializer(serializers.ModelSerializer):
    """Serializer for upload logo-image for Airline"""

    class Meta:
        model = Airline
        fields = ("id", "logo")


class AirportSerializer(serializers.ModelSerializer):
    """Airport base serializer"""

    closest_big_city = serializers.PrimaryKeyRelatedField(
        queryset=City.objects.select_related("country")
    )

    class Meta:
        model = Airport
        fields = ("id", "name", "closest_big_city", "iata_code", "icao_code")


class AirportListSerializer(AirportSerializer):
    """Airport list serializer"""

    closest_city_name = serializers.CharField(
        source="closest_big_city.name", read_only=True
    )
    country_name = serializers.CharField(
        source="closest_big_city.country.name", read_only=True
    )

    class Meta:
        model = Airport
        fields = ("id", "name", "closest_city_name", "country_name")


class AirportDetailSerializer(AirportSerializer):
    """Airport detail serializer"""

    closest_big_city = CityDetailSerializer(read_only=True)
    terminals_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Airport
        fields = (
            "id",
            "name",
            "closest_big_city",
            "iata_code",
            "icao_code",
            "terminals_count",
        )


class AirplaneTypeSerializer(serializers.ModelSerializer):
    """Airplane type serializer"""

    class Meta:
        model = AirplaneType
        fields = ("id", "name", "image", "manufacturer")


class AirplaneTypeImageSerializer(serializers.ModelSerializer):
    """Airplane type image serializer"""

    class Meta:
        model = AirplaneType
        fields = ("id", "image")


class AirplaneSerializer(serializers.ModelSerializer):
    """Airplane serializer"""

    num_seats = serializers.IntegerField(read_only=True)

    class Meta:
        model = Airplane
        fields = (
            "id",
            "name",
            "rows",
            "seats_in_row",
            "airplane_type",
            "airline",
            "registration_number",
            "is_active",
            "num_seats",
        )


class AirplaneListSerializer(AirplaneSerializer):
    """Airplane list serializer"""

    airplane_type = serializers.CharField(
        source="airplane_type.name",
        read_only=True
    )
    airline = serializers.CharField(
        source="airline.name",
        read_only=True
    )
    num_seats = serializers.IntegerField(read_only=True)

    class Meta:
        model = Airplane
        fields = (
            "id",
            "name",
            "airplane_type",
            "airline",
            "num_seats",
            "is_active"
        )


class AirplaneDetailSerializer(AirplaneSerializer):
    """Airplane retrieve serializer"""

    airplane_type = AirplaneTypeSerializer(read_only=True)
    airline = AirlineListSerializer(read_only=True)

    class Meta:
        model = Airplane
        fields = (
            "id",
            "name",
            "rows",
            "seats_in_row",
            "airplane_type",
            "airline",
            "registration_number",
            "is_active",
        )


class TerminalSerializer(serializers.ModelSerializer):
    """Base Terminal serializer"""

    airport = serializers.PrimaryKeyRelatedField(
        queryset=Airport.objects.select_related("closest_big_city")
    )

    class Meta:
        model = Terminal
        fields = (
            "id",
            "name",
            "airport",
            "capacity",
            "is_international",
            "opened_date",
        )
        validators = [
            UniqueTogetherValidator(
                queryset=Terminal.objects.all(),
                fields=["name", "airport"],
                message="This terminal name already exists for this airport.",
            )
        ]


class TerminalListSerializer(TerminalSerializer):
    """Terminal list serializer"""

    airport_name = serializers.CharField(
        source="airport.name",
        read_only=True
    )

    class Meta:
        model = Terminal
        fields = (
            "id",
            "name",
            "airport",
            "airport_name",
            "capacity",
            "is_international",
        )


class TerminalDetailSerializer(TerminalSerializer):
    """Terminal detail serializer"""

    gates_count = serializers.IntegerField(read_only=True)
    airport = AirportListSerializer(read_only=True)

    class Meta:
        model = Terminal
        fields = (
            "id",
            "name",
            "airport",
            "capacity",
            "is_international",
            "opened_date",
            "gates_count",
        )


class GateSerializer(serializers.ModelSerializer):
    """Gate serializer"""

    terminal = serializers.PrimaryKeyRelatedField(
        queryset=Terminal.objects.select_related("airport")
    )

    class Meta:
        model = Gate
        fields = ("id", "number", "terminal", "gate_type", "is_active")
        validators = [
            UniqueTogetherValidator(
                queryset=Gate.objects.select_related("terminal__airport"),
                fields=["number", "terminal"],
                message="This gate already exists in this terminal.",
            )
        ]

    def validate(self, attrs):
        """Validate gate type based on terminal's international status."""
        Gate.validate_gate_type(
            terminal=attrs["terminal"],
            gate_type=attrs["gate_type"]
        )
        return super().validate(attrs)


class GateListSerializer(GateSerializer):
    """Gate list serializer"""

    terminal_name = serializers.CharField(source="terminal.name", read_only=True)
    airport_name = serializers.CharField(source="terminal.airport.name", read_only=True)

    class Meta:
        model = Gate
        fields = (
            "id",
            "number",
            "terminal_name",
            "airport_name",
            "gate_type",
            "is_active",
        )


class GateDetailSerializer(GateSerializer):
    """Gate detail serializer"""

    terminal = TerminalListSerializer(read_only=True)
    airport = AirportListSerializer(
        source="terminal.airport",
        read_only=True
    )

    class Meta:
        model = Gate
        fields = (
            "id",
            "number",
            "terminal",
            "airport",
            "gate_type",
            "is_active"
        )


AIRPORT_QUERYSET = Airport.objects.select_related(
    "closest_big_city__country"
)

class RouteSerializer(serializers.ModelSerializer):
    """
    Base Route serializer with fields:
    source and destination (custom RepresentationChoiceField),
    that dynamic creates in __init__
    """

    source = RepresentationChoiceField(choices=[])
    destination = RepresentationChoiceField(choices=[])

    class Meta:
        model = Route
        fields = ("id", "source", "destination", "distance")
        read_only_fields = ("distance",)
        validators = [
            UniqueTogetherValidator(
                queryset=Route.objects.all(),
                fields=["source", "destination"],
                message="This route already exists.",
            )
        ]

    def __init__(self, *args, **kwargs):
        """
        Initial method for RouteSerializer.
        Generate dynamic data and pass actual choices for dields

        """
        super().__init__(*args, **kwargs)

        airport_choices = [
            (str(airport.pk), str(airport))
            for airport in AIRPORT_QUERYSET
        ]

        self.fields["source"].choices = airport_choices
        self.fields["destination"].choices = airport_choices

    def validate(self, attrs):
        """
        Validate that source and destination names are unique
        """
        if attrs["source"] == attrs["destination"]:
            raise serializers.ValidationError(
                "Source and destination airports must differ."
            )
        return attrs

    def create(self, validated_data):
        """
        Convert airport IDs obtained from fields into full-fledged Airport model objects.
        Uses optimized constant queryset for efficient searching.
        Create a Route object with already correct data.
        """

        source_pk = validated_data.pop("source")
        destination_pk = validated_data.pop("destination")

        airports = {
            str(airport.pk): airport
            for airport in AIRPORT_QUERYSET
            if str(airport.pk) in [source_pk, destination_pk]
        }

        validated_data["source"] = airports.get(source_pk)
        validated_data["destination"] = airports.get(destination_pk)

        return super().create(validated_data)

    def update(self, instance, validated_data):

        src_id = validated_data.pop("source", None)
        dst_id = validated_data.pop("destination", None)

        if src_id is not None or dst_id is not None:
            airports = {
                str(airport.pk): airport
                for airport in AIRPORT_QUERYSET
                if str(airport.pk) in [src_id, dst_id]
            }
            if src_id:
                instance.source = airports.get(src_id, Airport.objects.get(pk=int(src_id)))
            if dst_id:
                instance.destination = airports.get(dst_id, Airport.objects.get(pk=int(dst_id)))

        for attr, val in validated_data.items():
            setattr(instance, attr, val)

        instance.save()
        return instance


class RouteListSerializer(serializers.ModelSerializer):
    """Route list serializer"""

    source_name = serializers.CharField(source="source.name", read_only=True)
    destination_name = serializers.CharField(source="destination.name", read_only=True)
    read_only_fields = ("distance",)

    class Meta:
        model = Route
        fields = (
            "id",
            "source_name",
            "destination_name",
            "distance",
        )


class RouteDetailSerializer(RouteSerializer):
    """Route detail serializer"""

    source = AirportListSerializer(read_only=True)
    destination = AirportListSerializer(read_only=True)

    class Meta:
        model = Route
        fields = ("id", "distance", "source", "destination")


class FlightStatusSerializer(serializers.ModelSerializer):
    """Flight status serializer"""

    display_name = serializers.CharField(
        source="get_name_display",
        read_only=True
    )

    class Meta:
        model = FlightStatus
        fields = ("id", "name", "display_name", "description", "color_code")


class FlightStatusCreateSerializer(FlightStatusSerializer):
    """Nested FlightStatus serializer for create"""

    class Meta:
        model = FlightStatus
        fields = ("name", "description", "color_code")

    def validate_name(self, value):
        """Validate that name is in STATUS_CHOICES"""

        valid_choices = [choice[0] for choice in FlightStatus.STATUS_CHOICES]
        if value not in valid_choices:
            raise serializers.ValidationError(
                f"Invalid status. Must be one of: {valid_choices}"
            )
        return value


# This creates an optimized queryset to avoid N+1 queries later
GATE_QUERYSET = Gate.objects.select_related("terminal__airport")
# This creates a static list of choices for the create form dropdowns
GATE_CHOICES = [(str(gate.pk), str(gate)) for gate in GATE_QUERYSET]


class FlightSerializer(serializers.ModelSerializer):
    """
    Base serializer for CREATING flights. Uses RepresentationChoiceField
    for optimized query to Gate model by BrowsableAPIRenderer.
    Validation unique fields ('flight_number', 'departure_time')
    """
    route = serializers.PrimaryKeyRelatedField(
        queryset=Route.objects.select_related("source", "destination")
    )
    airplane = serializers.PrimaryKeyRelatedField(
        queryset=Airplane.objects.select_related("airplane_type", "airline")
    )
    departure_gate = RepresentationChoiceField(
        choices=GATE_CHOICES,
        allow_null=True,
        required=False
    )
    arrival_gate = RepresentationChoiceField(
        choices=GATE_CHOICES,
        allow_null=True,
        required=False
    )
    status_data = FlightStatusCreateSerializer(
        write_only=True,
        required=False
    )
    status = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Flight
        fields = (
            "id",
            "flight_number",
            "route",
            "airplane",
            "departure_time",
            "arrival_time",
            "price",
            "status",
            "status_data",
            "departure_gate",
            "arrival_gate",
        )
        validators = [
            UniqueTogetherValidator(
                queryset=Flight.objects.all(),
                fields=["flight_number", "departure_time"],
                message="This flight already exists in this time.",
            )
        ]

    def validate(self, attrs):
        """Validate that departure time < arrival time"""

        if attrs.get("departure_time") >= attrs.get("arrival_time"):
            raise serializers.ValidationError(
                {"arrival_time": "Arrival time must be after departure time."}
            )
        return attrs

    def create(self, validated_data):
        """
        Create and return a new `Flight` instance,
        given the validated data.
        """

        status_data = validated_data.pop("status_data", None)
        departure_gate_id = validated_data.pop("departure_gate", None)
        arrival_gate_id = validated_data.pop("arrival_gate", None)

        gates = {str(gate.pk): gate for gate in GATE_QUERYSET}
        if departure_gate_id:
            validated_data["departure_gate"] = gates.get(departure_gate_id, Gate.objects.get(pk=departure_gate_id))
        if arrival_gate_id:
            validated_data["arrival_gate"] = gates.get(arrival_gate_id, Gate.objects.get(pk=arrival_gate_id))

        flight = super().create(validated_data)

        if status_data:
            with transaction.atomic():
                flight_status, created = FlightStatus.objects.select_for_update().get_or_create(
                    name=status_data["name"],
                    defaults=status_data
                )
                flight.status = flight_status

        return flight


class FlightListSerializer(serializers.ModelSerializer):
    """
    Flight list serializer with flight create
    and flight status create logic.
    """

    route = serializers.StringRelatedField(read_only=True)
    airplane = serializers.StringRelatedField(read_only=True)
    status = serializers.CharField(source="get_status_display", read_only=True)
    tickets_available = serializers.IntegerField(read_only=True)
    flight_time = serializers.FloatField(read_only=True)
    airplane_capacity = serializers.IntegerField(read_only=True)

    class Meta:
        model = Flight
        fields = (
            "id",
            "flight_number",
            "route",
            "airplane",
            "departure_time",
            "arrival_time",
            "status",
            "price",
            "flight_time",
            "tickets_available",
            "airplane_capacity",
        )


class FlightUpdateSerializer(serializers.ModelSerializer):
    """
    A dedicated serializer for UPDATING flights.
    It uses standard fields to correctly populate the HTML form from instance
    """
    route = serializers.PrimaryKeyRelatedField(
        queryset=Route.objects.select_related("source", "destination")
    )
    airplane = serializers.PrimaryKeyRelatedField(
        queryset=Airplane.objects.select_related("airplane_type", "airline")
    )
    departure_gate = OptimizedRelatedField(
        queryset=GATE_QUERYSET,
        choices=GATE_CHOICES,
        allow_null=True,
        required=False
    )
    arrival_gate = OptimizedRelatedField(
        queryset=GATE_QUERYSET,
        choices=GATE_CHOICES,
        allow_null=True,
        required=False
    )

    status = FlightStatusCreateSerializer(required=False)


    class Meta:
        model = Flight
        fields = (
            "id",
            "flight_number",
            "price",
            "departure_time",
            "arrival_time",
            "route",
            "airplane",
            "departure_gate",
            "arrival_gate",
            "status",
        )

    def update(self, instance, validated_data):
        """
        Handle updates for nested status and convert gate IDs to objects.
        """

        status_data = validated_data.pop("status", None)
        if status_data:
            with transaction.atomic():
                flight_status, created = FlightStatus.objects.select_for_update().get_or_create(
                    name=status_data.get("name"),
                    defaults=status_data
                )
                instance.status = flight_status

        return super().update(instance, validated_data)


class TicketSerializer(serializers.ModelSerializer):
    """Base Ticket Serializer for validating a single ticket's data"""

    price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Ticket
        fields = ("id", "row", "seat", "price")

    def validate(self, attrs):
        """
        Method takes row/seat data from attributes or instance and
        flight from CustomTicketField context.
        Validation row/seat data, and passed price from flight
        """

        row = attrs.get("row", getattr(self.instance, "row", None))
        seat = attrs.get("seat", getattr(self.instance, "seat", None))

        flight = self.context.get("flight")
        if not flight:

            raise Exception("Error: 'flight' not passed tp context TicketSerializer.")

        Ticket.validate_row(row, flight.airplane.rows, serializers.ValidationError)
        Ticket.validate_seat(seat, flight.airplane.seats_in_row, serializers.ValidationError)

        attrs["price"] = flight.price
        return attrs


class FlightDetailSerializer(serializers.ModelSerializer):
    """
    A dedicated serializer for DISPLAYING flight details (read-only).
    It uses nested serializers for rich representation.
    """
    route = RouteListSerializer(read_only=True)
    airplane = AirplaneListSerializer(read_only=True)
    status = FlightStatusSerializer(read_only=True)
    departure_gate = GateListSerializer(read_only=True)
    arrival_gate = GateListSerializer(read_only=True)
    flight_time = serializers.CharField(read_only=True)
    tickets_available = serializers.IntegerField(read_only=True)
    taken_seats = serializers.SerializerMethodField()

    class Meta:
        model = Flight
        fields = (
            "id",
            "flight_number",
            "price",
            "departure_time",
            "arrival_time",
            "route",
            "airplane",
            "status",
            "departure_gate",
            "arrival_gate",
            "flight_time",
            "tickets_available",
            "taken_seats",
        )

    def get_taken_seats(self, obj):
        """Return a list of tuples (row, seat) for all taken seats in the flight."""
        taken = obj.tickets.values_list("row", "seat")
        return list(taken)


class CrewSerializer(serializers.ModelSerializer):
    """Crew serializer with bulk-validation for update crew instance"""

    flight_ids = BulkManyPrimaryKeyRelatedField(
        child_relation=CustomPrimaryKeyRelatedField(),
        source="flights",
        required=False,
        help_text="Choose flights for this Crew",
        style={"base_template": "checkbox_multiple.html"}
    )

    class Meta:
        model = Crew
        fields = (
            "id",
            "first_name",
            "last_name",
            "flight_ids",
        )

    def to_representation(self, instance):
        """For update return flight_ids (list with IDs)"""

        return super().to_representation(instance)

    def create(self, validated_data):
        """Override create with bulk M2M queries"""
        flights = validated_data.pop("flights", [])
        crew = super().create(validated_data)
        if flights:
            crew.flights.add(*flights)
        return crew

    def update(self, instance, validated_data):
        """
        Update Crew instance with valid data
        (first_name, last_name) and delete M2M relation
        from list of flights, in 1 SQL query,
        taken from BulkManyPrimaryKeyRelatedField.to_internal_value
        """
        flights = validated_data.pop("flights", None)
        instance = super().update(instance, validated_data)
        if flights is not None:
            instance.flights.clear()
            instance.flights.add(*flights)
        return instance


class FlightMiniSerializer(serializers.ModelSerializer):
    """MINI serializer for Crew List (without double-query DB)"""
    route = serializers.CharField(source="route.source.name", read_only=True)
    airplane = serializers.CharField(source="airplane.name", read_only=True)
    status = serializers.CharField(source="status.name", read_only=True)

    class Meta:
        model = Flight
        fields = ("id", "flight_number", "route", "airplane", "status")


class CrewListSerializer(serializers.ModelSerializer):
    """Crew list serializer"""

    flights = FlightMiniSerializer(many=True, read_only=True)

    class Meta(CrewSerializer.Meta):
        model = Crew
        fields = (
            "id",
            "first_name",
            "last_name",
            "flights",
        )


class CrewDetailSerializer(serializers.ModelSerializer):
    """Crew detail serializer"""

    flights = FlightListSerializer(many=True, read_only=True)
    class Meta:
        model = Crew
        fields = (
            "id",
            "first_name",
            "last_name",
            "flights",
        )


class CustomTicketField(serializers.ListField):
    """
    Custom field for handling a list of tickets.
    Takes into account that list items can also be JSON strings.
    Use TicketSerializer like child for pass ticket data and flight
    """
    child = TicketSerializer()

    def __init__(self, *args, **kwargs):
        """Pass default style for browsable API"""

        kwargs["style"] = kwargs.get("style", {"base_template": "textarea.html"})
        kwargs["allow_empty"] = kwargs.get("allow_empty", False)
        super().__init__(*args, **kwargs)

    def to_internal_value(self, data):
        """
        Parse JSON list and validate every ticket in child serializer
        """

        json_string = None
        if isinstance(data, list) and len(data) == 1 and isinstance(data[0], str):
            json_string = data[0]
        else:
            raise serializers.ValidationError(
                "Unexpected data format. Try sending tickets as a list JSON."
            )

        try:
            ticket_list = json.loads(json_string)
        except json.JSONDecodeError:
            raise serializers.ValidationError(
                "The string is not valid JSON. Check that all quotes are double quotes. (\")."
            )

        if not isinstance(ticket_list, list):
            raise serializers.ValidationError("The JSON should contain a list of tickets.")

        validated_data = []
        for ticket_item in ticket_list:
            if not isinstance(ticket_item, dict):
                raise serializers.ValidationError(f"Element '{ticket_item}' in list is not a dict.")

            child_serializer = self.child.__class__(data=ticket_item, context=self.context)
            child_serializer.is_valid(raise_exception=True)
            validated_data.append(child_serializer.validated_data)

        return validated_data

    def to_representation(self, value):
        """Converts a queryset of Ticket instances into a simple list of dictionaries for output.
        `value` here is the associated manager (e.g. order.tickets)."""
        return [{"row": item.row, "seat": item.seat} for item in value.all()]


class OrderSerializer(serializers.ModelSerializer):
    """
    Serializer for creating an order.
    Handles nested tickets using a custom field.
    """
    tickets = CustomTicketField(
        child=TicketSerializer(),
        allow_empty=False,
        help_text="Введіть квитки як JSON-список з подвійними лапками: "
                  "[{\"row\": 5, \"seat\": 2}, {\"row\": 5, \"seat\": 3}]"
    )
    flight_name = serializers.CharField(source="flight.route", read_only=True)
    flight = CustomPrimaryKeyRelatedField(
        queryset=Flight.objects.all(),
        write_only=True,
        help_text="Choose flight ID for this order"
    )

    class Meta:
        model = Order
        fields = (
            "id",
            "created_at",
            "flight",
            "flight_name",
            "tickets",
            "total_price"
        )
        read_only_fields = ("id", "created_at", "total_price")

    def validate(self, attrs):
        """
        Validation on the order instance level:
        Does not allow duplication of space in one order.
        """

        tickets_data = attrs.get("tickets", [])
        seen_seats = set()
        for ticket_data in tickets_data:
            seat_key = (ticket_data["row"], ticket_data["seat"])
            if seat_key in seen_seats:
                raise ValidationError({
                    "tickets": f"Duplication of space in one order: Row {seat_key[0]}, Seat {seat_key[1]}."
                })
            seen_seats.add(seat_key)

        return attrs

    def create(self, validated_data):
        """
        Create order and tickets in one atomic transaction.
        - takes user from ViewSet context
        - block choosed tickets
        - create order
        - bulk creat tickets

        """
        with transaction.atomic():
            tickets_data = validated_data.pop("tickets")
            flight = validated_data["flight"]

            request = self.context.get("request")
            if not request or not hasattr(request, "user"):
                raise Exception("Error: 'request' not pass in serializer context.")
            user = request.user

            requested_seats = {(ticket["row"], ticket["seat"]) for ticket in tickets_data}

            taken_seats = set(
                Ticket.objects.select_for_update()
                .filter(flight=flight, row__in=[f_row for f_row, f_seat in requested_seats],
                        seat__in=[f_seat for f_row, f_seat in requested_seats])
                .values_list("row", "seat")
            )

            conflicting_seats = requested_seats.intersection(taken_seats)
            if conflicting_seats:
                raise ValidationError(
                    {
                    "tickets": [
                        f"This place already taken: row={row}, seat={seat}" for row, seat in conflicting_seats
                    ]
                }
                )

            order = Order.objects.create(
                flight=flight,
                user=user,
                total_price=flight.price * len(tickets_data)
            )

            tickets_to_create = [
                Ticket(
                    order=order,
                    flight=flight,
                    row=f_ticket["row"],
                    seat=f_ticket["seat"],
                    price=flight.price
                )
                for f_ticket in tickets_data
            ]
            Ticket.objects.bulk_create(tickets_to_create)

            response_order = Order.objects.select_related(
                "flight__route__source",
                "flight__route__destination"
            ).prefetch_related("tickets").get(pk=order.pk)

            return response_order


class OrderUpdateSerializer(serializers.ModelSerializer):
    """
    Order serializer for UPDATE order.
    - user can't change the flight
    - user can change row and seats
    Method delete old ticket and create the new one.
    Update price
    Update order with optimisation
    """
    flight = serializers.StringRelatedField(read_only=True)

    tickets = CustomTicketField(allow_empty=False)

    class Meta:
        model = Order
        fields = ("id", "flight", "tickets", "total_price")
        read_only_fields = ("id", "total_price")

    def update(self, instance, validated_data):
        with transaction.atomic():
            tickets_data = validated_data.pop("tickets")
            flight = instance.flight

            instance.tickets.all().delete()

            new_tickets = [
                Ticket(
                    order=instance,
                    flight=flight,
                    row=ord_ticket["row"],
                    seat=ord_ticket["seat"],
                    price=flight.price
                )
                for ord_ticket in tickets_data
            ]

            requested_seats = {(o_ticket.row, o_ticket.seat) for o_ticket in new_tickets}
            taken_seats = set(
                Ticket.objects.select_for_update()
                .filter(flight=flight, row__in=[f_row for f_row, f_seat in requested_seats],
                        seat__in=[f_seat for f_row, f_seat in requested_seats])
                .values_list("row", "seat")
            )

            if requested_seats.intersection(taken_seats):
                raise serializers.ValidationError({"tickets": "One or more tickets already taken."})

            Ticket.objects.bulk_create(new_tickets)

            instance.total_price = flight.price * len(new_tickets)
            instance.save()

            final_instance = Order.objects.prefetch_related("tickets").get(pk=instance.pk)

            return final_instance


class OrderListSerializer(OrderSerializer):
    """Order list serializer"""
    tickets = TicketSerializer(many=True, read_only=True)


class OrderDetailSerializer(OrderSerializer):
    """Order detail serializer"""
    tickets = TicketSerializer(many=True, read_only=True)
    flight_number = serializers.CharField(
        source="flight.flight_number",
        read_only=True
    )
    airline = serializers.CharField(
        source="flight.airplane.airline.name",
        read_only=True
    )
    status = serializers.CharField(
        source="flight.status.get_name_display",
        read_only=True
    )
    departure_airport = serializers.CharField(
        source="flight.route.source.name",
        read_only=True
    )
    arrival_airport = serializers.CharField(
        source="flight.route.destination.name",
        read_only=True
    )
    class Meta:
        model = Order
        fields = (
            "id",
            "created_at",
            "airline",
            "flight_number",
            "departure_airport",
            "arrival_airport",
            "status",
            "tickets",
            "total_price",
        )
