from django.contrib import admin
from django.utils.html import format_html

from airport.models import (
    Country,
    City,
    Airline,
    FlightStatus,
    Terminal,
    Gate,
    Airport,
    Route,
    AirplaneType,
    Airplane,
    Flight,
    Crew,
    Order,
    Ticket,
)


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ["name", "currency", "timezone", "cities_count"]
    search_fields = ["name", "currency"]
    list_filter = ["currency"]
    ordering = ["name"]

    def cities_count(self, obj):
        return obj.cities.count()

    cities_count.short_description = "Cities"


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ["name", "country", "population", "airports_count"]
    search_fields = ["name", "country__name"]
    list_filter = ["country"]
    ordering = ["country__name", "name"]

    def airports_count(self, obj):
        return obj.airports.count()

    airports_count.short_description = "Airports"


@admin.register(Airline)
class AirlineAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "code",
        "country",
        "founded_year",
        "is_active",
        "logo_preview",
    ]
    search_fields = ["name", "code"]
    list_filter = ["country", "is_active", "founded_year"]
    ordering = ["name"]
    readonly_fields = ["logo_preview"]

    def logo_preview(self, obj):
        if obj.logo:
            return format_html("<img src='{}' width='90' height='50' />", obj.logo.url)
        return "No logo"

    logo_preview.short_description = "Logo Preview"


@admin.register(FlightStatus)
class FlightStatusAdmin(admin.ModelAdmin):
    list_display = ["name", "get_display_name", "color_preview", "description"]
    search_fields = ["name"]
    list_filter = ["name"]

    def get_display_name(self, obj):
        return obj.get_name_display()

    get_display_name.short_description = "Display Name"

    def color_preview(self, obj):
        if obj.color_code:
            return format_html(
                '<div style="width: 20px; height: 20px; background-color: {}; border: 1px solid #ccc;"></div>',
                obj.color_code,
            )
        return "No color"

    color_preview.short_description = "Color"


@admin.register(Terminal)
class TerminalAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "airport",
        "capacity",
        "is_international",
        "opened_date",
        "gates_count",
    ]
    search_fields = ["name", "airport__name"]
    list_filter = ["is_international", "airport"]
    ordering = ["airport__name", "name"]

    def gates_count(self, obj):
        return obj.gates.count()

    gates_count.short_description = "Gates"


@admin.register(Gate)
class GateAdmin(admin.ModelAdmin):
    list_display = ["number", "terminal", "airport", "gate_type", "is_active"]
    search_fields = ["number", "terminal__name", "terminal__airport__name"]
    list_filter = ["gate_type", "is_active", "terminal__airport"]
    ordering = ["terminal__airport__name", "terminal__name", "number"]

    def airport(self, obj):
        return obj.terminal.airport.name

    airport.short_description = "Airport"


@admin.register(Airport)
class AirportAdmin(admin.ModelAdmin):
    list_display = ["name", "iata_code", "icao_code", "closest_big_city", "country"]
    search_fields = ["name", "iata_code", "icao_code", "closest_big_city__name"]
    list_filter = ["closest_big_city__country"]
    ordering = ["name"]

    def country(self, obj):
        return obj.closest_big_city.country.name

    country.short_description = "Country"


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = [
        "source",
        "destination",
        "distance",
        "source_country",
        "destination_country",
    ]
    search_fields = ["source__name", "destination__name"]
    list_filter = [
        "source__closest_big_city__country",
        "destination__closest_big_city__country",
    ]
    ordering = ["source__name"]

    def source_country(self, obj):
        return obj.source.closest_big_city.country.name

    source_country.short_description = "From Country"

    def destination_country(self, obj):
        return obj.destination.closest_big_city.country.name

    destination_country.short_description = "To Country"


@admin.register(AirplaneType)
class AirplaneTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "manufacturer", "image_preview", "airplanes_count"]
    search_fields = ["name", "manufacturer"]
    list_filter = ["manufacturer"]
    ordering = ["name"]
    readonly_fields = ["image_preview"]

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="100" height="60" />', obj.image.url
            )
        return "No image"

    image_preview.short_description = "Image Preview"

    def airplanes_count(self, obj):
        return obj.airplanes.count()

    airplanes_count.short_description = "Airplanes"


@admin.register(Airplane)
class AirplaneAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "registration_number",
        "airline",
        "airplane_type",
        "get_num_seats",
        "is_active",
    ]
    search_fields = ["name", "registration_number", "airline__name"]
    list_filter = ["airline", "airplane_type", "is_active"]
    ordering = ["airline__name", "name"]
    readonly_fields = ["get_num_seats"]

    def get_num_seats(self, obj):
        """Calculate the total number of seats (rows * seats_in_row)."""
        return obj.rows * obj.seats_in_row

    get_num_seats.short_description = "Number of Seats"


@admin.register(Flight)
class FlightAdmin(admin.ModelAdmin):
    list_display = [
        "flight_number",
        "route",
        "airplane",
        "departure_time",
        "arrival_time",
        "status",
        "flight_time_display",
        "price",
    ]
    search_fields = ["flight_number", "route__source__name", "route__destination__name"]
    list_filter = [
        "status",
        "airplane__airline",
        "departure_time",
    ]
    ordering = ["-departure_time"]
    date_hierarchy = "departure_time"
    readonly_fields = ["flight_time_display"]

    autocomplete_fields = ["status"]

    def flight_time_display(self, obj):
        return f"{obj.flight_time}h"

    flight_time_display.short_description = "Flight Time"


@admin.register(Crew)
class CrewAdmin(admin.ModelAdmin):
    list_display = ["first_name", "last_name", "flights_count"]
    search_fields = ["first_name", "last_name"]
    filter_horizontal = ["flights"]
    ordering = ["last_name", "first_name"]

    def flights_count(self, obj):
        return obj.flights.count()

    flights_count.short_description = "Flights"


class TicketInline(admin.TabularInline):
    model = Ticket
    extra = 0
    readonly_fields = ["price"]
    fields = ["row", "seat", "price"]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "user",
        "flight",
        "created_at",
        "total_price",
        "tickets_count",
    ]
    search_fields = ["user__email", "flight__flight_number"]
    list_filter = ["created_at"]
    ordering = ["-created_at"]
    date_hierarchy = "created_at"
    readonly_fields = ["created_at", "tickets_count"]
    inlines = [TicketInline]

    def tickets_count(self, obj):
        return obj.ticket_set.count()

    tickets_count.short_description = "Tickets"


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ["flight", "row", "seat", "order", "price", "passenger"]
    search_fields = ["flight__flight_number", "order__user__email"]
    list_filter = ["flight__departure_time", "flight__route__source"]
    ordering = ["flight__departure_time", "row", "seat"]

    def passenger(self, obj):
        return obj.order.user.email

    passenger.short_description = "Passenger"


# Customize admin site header and title
admin.site.site_header = "Airport Service Administration"
admin.site.site_title = "Airport Admin"
admin.site.index_title = "Welcome to Airport Service Admin Panel"
