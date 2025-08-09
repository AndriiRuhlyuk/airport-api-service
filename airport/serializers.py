from django.db import transaction
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

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
    Crew, Ticket, Order,
)


class CountrySerializer(serializers.ModelSerializer):
    """Country model serializer"""

    class Meta:
        model = Country
        fields = ("id", "name", "currency", "timezone")


class CitySerializer(serializers.ModelSerializer):
    """City model serializer"""

    country = serializers.PrimaryKeyRelatedField(
        queryset=Country.objects.all(),
        write_only=True,
    )
    country_name = serializers.CharField(source="country.name", read_only=True)

    class Meta:
        model = City
        fields = ("id", "name", "country", "country_name", "population")
        validators = [
            UniqueTogetherValidator(
                queryset=City.objects.all(),
                fields=["name", "country"],
                message="This city already exists in this country.",
            )
        ]


class CityDetailSerializer(CitySerializer):
    """City list model serializer"""

    country = CountrySerializer(read_only=True)

    class Meta:
        model = City
        fields = ("id", "name", "country", "population")


class AirlineSerializer(serializers.ModelSerializer):
    """Airline Base Serializer"""

    class Meta:
        model = Airline
        fields = ("id", "name", "code", "country", "founded_year", "logo", "is_active")


class AirlineListSerializer(AirlineSerializer):
    """Airline list serializer"""

    country = serializers.SlugRelatedField(
        slug_field="name", queryset=Country.objects.all()
    )

    class Meta:
        model = Airline
        fields = ("id", "name", "country", "logo", "is_active")


class AirlineDetailSerializer(serializers.ModelSerializer):
    """Airline detail serializer"""

    country = CountrySerializer(read_only=True)
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
    """Serializer for work with logo-image for Airline"""

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


class AirportListSerializer(serializers.ModelSerializer):
    """Airport list serializer"""

    closest_city_name = serializers.CharField(
        source="closest_big_city.name", read_only=True
    )
    county_name = serializers.CharField(
        source="closest_big_city.country.name", read_only=True
    )

    class Meta:
        model = Airport
        fields = ("id", "name", "closest_city_name", "county_name")


class AirportDetailSerializer(AirportSerializer):
    """Airport detail serializer"""

    closest_big_city = CityDetailSerializer(read_only=True)
    terminals_count = serializers.SerializerMethodField(read_only=True)

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

    def get_terminals_count(self, obj):
        """Count the number of terminals in the airport"""

        if (
            hasattr(obj, "_prefetched_objects_cache")
            and "terminals" in obj._prefetched_objects_cache
        ):
            return len(obj._prefetched_objects_cache["terminals"])
        return obj.terminals.count()


class AirplaneTypeSerializer(serializers.ModelSerializer):
    """Airline type serializer"""

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
    count_seats = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Airplane
        fields = (
            "id",
            "name",
            "airplane_type",
            "airline",
            "count_seats",
            "is_active"
        )

    def get_count_seats(self, obj):
        """Number of seats in the Airplane"""

        if obj.rows is not None and obj.seats_in_row is not None:
            return obj.rows * obj.seats_in_row
        return 0


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
                message="This airport already exists in this city.",
            )
        ]


class TerminalListSerializer(TerminalSerializer):
    """Terminal list serializer"""

    airport = serializers.SlugRelatedField(
        slug_field="name",
        queryset=Airport.objects.select_related("closest_big_city__country"),
        write_only=True,
    )
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

    gates_count = serializers.SerializerMethodField(read_only=True)
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

    def get_gates_count(self, obj):
        """Count the number of gates in the terminal"""

        return obj.gates.count()


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
                queryset=Gate.objects.all(),
                fields=["number", "terminal"],
                message="This gate already exists in this terminal.",
            )
        ]

    def validate(self, attrs):
        Gate.validate_gate_type(
            terminal=attrs["terminal"], gate_type=attrs["gate_type"]
        )
        return super().validate(attrs)


class GateListSerializer(GateSerializer):
    """Gate list serializer"""

    terminal_name = serializers.CharField(source="terminal.name", read_only=True)
    airport_name = serializers.CharField(source="terminal.airport.name", read_only=True)
    terminal = serializers.PrimaryKeyRelatedField(
        queryset=Terminal.objects.select_related("airport"), write_only=True
    )

    class Meta:
        model = Gate
        fields = (
            "id",
            "number",
            "terminal",
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


class RouteSerializer(serializers.ModelSerializer):
    """Base Route serializer"""

    source = serializers.PrimaryKeyRelatedField(
        queryset=Airport.objects.select_related("closest_big_city__country")
    )
    destination = serializers.PrimaryKeyRelatedField(
        queryset=Airport.objects.select_related("closest_big_city__country")
    )

    class Meta:
        model = Route
        fields = ("id", "source", "destination", "distance")


class RouteListSerializer(serializers.ModelSerializer):
    """Route list serializer"""

    source_name = serializers.CharField(source="source.name", read_only=True)
    destination_name = serializers.CharField(source="destination.name", read_only=True)

    class Meta:
        model = Route
        fields = (
            "id",
            "source_name",
            "destination_name",
            "distance",
        )
        validators = [
            UniqueTogetherValidator(
                queryset=Route.objects.all(),
                fields=["source", "destination"],
                message="This route already exists.",
            )
        ]

    def validate(self, attrs):
        """
        Validate that source and destination names are unique
        """
        if attrs["source"] == attrs["destination"]:
            raise serializers.ValidationError(
                "Source and destination airports must differ."
            )
        return attrs


class RouteDetailSerializer(RouteSerializer):
    """Route detail serializer"""

    source = AirportListSerializer(read_only=True)
    destination = AirportListSerializer(read_only=True)

    class Meta:
        model = Route
        fields = ("id", "source", "destination", "distance")


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


class FlightSerializer(serializers.ModelSerializer):
    """Base Flight serializer"""

    route = serializers.PrimaryKeyRelatedField(
        queryset=Route.objects.select_related("source", "destination")
    )
    airplane = serializers.PrimaryKeyRelatedField(
        queryset=Airplane.objects.select_related("airplane_type", "airline")
    )
    status = serializers.PrimaryKeyRelatedField(read_only=True)
    departure_gate = serializers.StringRelatedField(read_only=True)
    arrival_gate = serializers.StringRelatedField(read_only=True)


    departure_gate_id = serializers.PrimaryKeyRelatedField(
        source="departure_gate",
        queryset=Gate.objects.select_related("terminal", "terminal__airport"),
        write_only=True, allow_null=True, required=False,
    )
    arrival_gate_id = serializers.PrimaryKeyRelatedField(
        source="arrival_gate",
        queryset=Gate.objects.select_related("terminal", "terminal__airport"),
        write_only=True, allow_null=True, required=False,
    )

    status_data = FlightStatusCreateSerializer(required=False)

    class Meta:
        model = Flight
        fields = (
            "id",
            "route",
            "airplane",
            "departure_time",
            "arrival_time",
            "status",
            "status_data",
            "flight_number",
            "price",
            "departure_gate",
            "departure_gate_id",
            "arrival_gate",
            "arrival_gate_id",
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
        errors = {}

        departure = attrs.get("departure_time")
        arrival = attrs.get("arrival_time")

        if departure and arrival and departure >= arrival:
            errors["arrival_time"] = "Arrival time must be after departure time."

        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    def create(self, validated_data):
        """
        Create and return a new `Flight` instance,
        given the validated data.
        """

        status_data = validated_data.pop("status_data", None)
        if status_data:
            fs, _ = FlightStatus.objects.get_or_create(
                name=status_data["name"],
                defaults={
                    "description": status_data.get("description", ""),
                    "color_code": status_data.get("color_code", "#808080"),
                },
            )
            validated_data["status"] = fs
        return super().create(validated_data)


class FlightListSerializer(FlightSerializer):
    """Flight list serializer with flight status create logic"""


    status_data = FlightStatusCreateSerializer(
        write_only=True,
        required=False
    )

    status_display = serializers.CharField(
        source="status.get_name_display",
        read_only=True
    )
    route_info = serializers.CharField(
        source="route",
        read_only=True
    )
    airplane_name = serializers.CharField(
        source="airplane.name",
        read_only=True
    )
    flight_time = serializers.CharField(read_only=True)

    class Meta:
        model = Flight
        fields = (
            "id",
            "route_info",
            "airplane_name",
            "departure_time",
            "arrival_time",
            "status_display",
            "flight_number",
            "flight_time",
            "airplane_name",
            "flight_time",
            "status_data",
            "price",
        )


class FlightDetailSerializer(FlightSerializer):
    """Flight detail serializer with flight status update logic"""

    route_id = serializers.PrimaryKeyRelatedField(
        source="route",
        queryset=Route.objects.select_related("source", "destination"),
        write_only=True,
        required=False
    )
    airplane_id = serializers.PrimaryKeyRelatedField(
        source="airplane",
        queryset=Airplane.objects.select_related("airplane_type", "airline"),
        write_only=True,
        required=False
    )

    route = RouteListSerializer(read_only=True)
    airplane = AirplaneListSerializer(read_only=True)

    status = FlightStatusSerializer(read_only=True)

    status_data = FlightStatusCreateSerializer(source="status", required=False)

    route_info = RouteListSerializer(read_only=True)
    airplane_info = AirplaneListSerializer(read_only=True)
    departure_gate_info = GateListSerializer(read_only=True)
    arrival_gate_info = GateListSerializer(read_only=True)

    flight_time = serializers.CharField(read_only=True)

    class Meta:
        model = Flight
        fields = (
            "id",
            "route",
            "route_id",
            "route_info",
            "airplane",
            "airplane_id",
            "airplane_info",
            "departure_time",
            "arrival_time",
            "flight_time",
            "status",
            "status_data",
            "flight_number",
            "price",
            "departure_gate",
            "departure_gate_info",
            "arrival_gate",
            "arrival_gate_info",
        )

    def update(self, instance, validated_data):
        """
        Update flight status data,
        with instance.status fields.
        """
        status_payload = validated_data.pop("status", None)
        if status_payload is not None:
            name = status_payload.get("name")
            defaults = {
                "description": status_payload.get("description", ""),
                "color_code": status_payload.get("color_code", "#808080"),
            }
            fs, created = FlightStatus.objects.get_or_create(name=name, defaults=defaults)
            if not created:
                for k, v in defaults.items():
                    setattr(fs, k, v)
                fs.save(update_fields=list(defaults.keys()))
            instance.status = fs

        return super().update(instance, validated_data)


class CrewSerializer(serializers.ModelSerializer):
    """Crew serializer"""

    flights_scheduled = serializers.PrimaryKeyRelatedField(
        queryset=Flight.objects.select_related(
            "route__source", "route__destination", "airplane__airplane_type", "status"
        ),
        many=True,
        source="flights",
        required=False,
        help_text="Choose flights, for this Crew",
        style = {"base_template": "checkbox_multiple.html"}
    )

    class Meta:
        model = Crew
        fields = (
            "id",
            "first_name",
            "last_name",
            "flights_scheduled",
        )

    def create(self, validated_data):
        flights = validated_data.pop("flights", [])
        crew = super().create(validated_data)
        if flights:
            crew.flights.set(flights)
        return crew

    def update(self, instance, validated_data):
        flights = validated_data.pop("flights", None)
        instance = super().update(instance, validated_data)
        if flights is not None:
            instance.flights.set(flights)
        return instance


class FlightMiniSerializer(FlightListSerializer):
    """MINI serializer for Crew List (without double-query DB)"""

    class Meta(FlightListSerializer.Meta):
        fields = ("id", "flight_number", "route_info", "airplane_name", "status_display")


class CrewListSerializer(CrewSerializer):
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


class CrewDetailSerializer(CrewSerializer):
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


class TicketSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ticket
        fields = ("id", "row", "seat", "price")

    def validate(self, attrs):
        row = attrs.get("row", getattr(self.instance, "row", None))
        seat = attrs.get("seat", getattr(self.instance, "seat", None))

        flight = self.context.get("flight") or getattr(self.instance, "flight", None)
        if not flight:
            return attrs

        airplane = flight.airplane
        Ticket.validate_row(row, airplane.rows, serializers.ValidationError)
        Ticket.validate_seat(seat, airplane.seats_in_row, serializers.ValidationError)

        return attrs


class TicketListSerializer(TicketSerializer):
    flight_number = serializers.CharField(source="flight.flight_number", read_only=True)
    flight_from = serializers.CharField(source="flight.route.source.closest_big_city", read_only=True)
    flight_to = serializers.CharField(source="flight.route.destination.closest_big_city", read_only=True)

    class Meta:
        model = Ticket
        fields = ("id", "row", "seat", "price", "flight_number", "flight_from", "flight_to")


class TicketSeatsSerializer(TicketSerializer):
    class Meta:
        model = Ticket
        fields = ("row", "seat")


class OrderSerializer(serializers.ModelSerializer):
    tickets = TicketSerializer(many=True, read_only=False, allow_empty=False)
    flight_name = serializers.CharField(source="flight.route", read_only=True)
    flight = serializers.PrimaryKeyRelatedField(
        queryset=Flight.objects.select_related(
            "route__source",
            "route__destination"
        ),
        write_only=True,
    )

    class Meta:
        model = Order
        fields = ("id", "created_at", "flight", "flight_name", "tickets",)
        read_only_fields = ("created_at",)

    def validate(self, attrs):
        tickets_payload = self.initial_data.get("tickets", [])
        seen = set()
        for index, place in enumerate(tickets_payload):
            try:
                key = (int(place.get("row")), int(place.get("seat")))
            except (TypeError, ValueError):
                raise serializers.ValidationError({"tickets": f"tickets[{index}] has not correct row/seat"})
            if key in seen:
                raise serializers.ValidationError({"tickets": f"Duplicate seat in request at index {index}: {key}"})
            seen.add(key)
        return attrs

    def create(self, validated_data):
        with transaction.atomic():
            tickets_data = validated_data.pop("tickets")
            flight = validated_data["flight"]

            order = Order.objects.create(**validated_data)

            airplane = flight.airplane
            errors = {}
            req_pairs = []
            for index, place in enumerate(tickets_data):
                row = place["row"]
                seat = place["seat"]
                try:
                    Ticket.validate_row(row, airplane.rows, serializers.ValidationError)
                    Ticket.validate_seat(seat, airplane.seats_in_row, serializers.ValidationError)
                except serializers.ValidationError as e:
                    errors[f"tickets[{index}]"] = e.detail
                req_pairs.append((row, seat))

            if errors:
                raise serializers.ValidationError(errors)

            rows = [row for row, _ in req_pairs]
            seats = [seat for _, seat in req_pairs]
            taken_queryset = (Ticket.objects
                        .select_for_update()
                        .filter(flight=flight, row__in=rows, seat__in=seats))
            taken = {(taken.row, taken.seat) for taken in taken_queryset}
            clashes = [pair for pair in req_pairs if pair in taken]

            if clashes:
                raise serializers.ValidationError({
                    "tickets": [f"Seat already taken: row={row}, seat={seat}" for (row, seat) in clashes]
                })
            tickets = [
                Ticket(order=order, flight=flight, row=row, seat=seat, price=t.get("price"))
                for (row, seat), t in zip(req_pairs, tickets_data)
            ]
            Ticket.objects.bulk_create(tickets)

            return order

class TicketUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ("row", "seat", "price")

    def validate(self, attrs):
        inst: Ticket = self.instance
        flight = inst.flight

        row = attrs.get("row", inst.row)
        seat = attrs.get("seat", inst.seat)

        airplane = flight.airplane
        Ticket.validate_row(row, airplane.rows, serializers.ValidationError)
        Ticket.validate_seat(seat, airplane.seats_in_row, serializers.ValidationError)

        exists = Ticket.objects.filter(
            flight=flight, row=row, seat=seat
        ).exclude(pk=inst.pk).exists()
        if exists:
            raise serializers.ValidationError({"seat": "This seat is already taken for this flight."})

        return attrs

class OrderListSerializer(OrderSerializer):
    tickets = TicketListSerializer(many=True, read_only=True)
