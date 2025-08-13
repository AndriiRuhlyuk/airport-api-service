import time
from django.core.management.base import BaseCommand
from geopy.geocoders import Nominatim
from airport.models import City
from geopy.exc import GeocoderTimedOut

class Command(BaseCommand):
    help = "Finds and saves coordinates for cities that don't have them"

    def handle(self, *args, **options):
        geolocator = Nominatim(user_agent="city_geocoder_airport", timeout=10)
        cities_to_geocode = City.objects.filter(latitude__isnull=True)

        if not cities_to_geocode.exists():
            self.stdout.write(self.style.SUCCESS("All cities already have coordinates."))
            return

        self.stdout.write(f"Find {cities_to_geocode.count()} cities for geocoding.")

        for city in cities_to_geocode:
            try:
                query = f"{city.name}, {city.country.name}"
                location = geolocator.geocode(query)

                if location:
                    city.latitude = location.latitude
                    city.longitude = location.longitude
                    city.save()
                    self.stdout.write(
                        self.style.SUCCESS(f"Coordinates for {city.name} successful saved.")
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f"Can't find coordinates for {city.name}.")
                    )

            except GeocoderTimedOut:
                self.stdout.write(
                    self.style.ERROR(
                        f"Service timed out for {city.name}. Retrying..."
                    )
                )
                continue

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"An error occurred for {city.name}: {e}"))

            time.sleep(1)
