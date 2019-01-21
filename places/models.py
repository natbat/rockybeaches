from django.db import models

class Station(models.Model):
    station_id = models.CharField(
        unique=True,
        max_length=20
    )
    name = models.CharField(max_length=128)
    latitude = models.FloatField()
    longitude = models.FloatField()

    def __str__(self):
        return self.name + ", " + self.station_id

class Place(models.Model):
    # Core information
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=128)
    latitude = models.FloatField()
    longitude = models.FloatField()
    radius_km = models.FloatField(default=0.5)
    station = models.ForeignKey(
        Station,
        on_delete=models.CASCADE,
        related_name="places"
    )

    # Descriptive
    tagline = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)

    # Utilitarian
    address = models.CharField(max_length=128, blank=True)
    directions = models.TextField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    url = models.URLField(blank=True)

    # Logistical
    entry_cost = models.CharField(max_length=128, blank=True)
    parking = models.TextField(blank=True)
    open_to_public = models.BooleanField(default=True)

    # Informational
    docents = models.BooleanField(default=False)
    visitor_center = models.BooleanField(default=False)

    # Human needs
    bathrooms = models.BooleanField(default=False)
    food_options = models.TextField(blank=True)
    accessibility = models.TextField(blank=True)
    dogs = models.BooleanField(default=False)
    pet_policy = models.TextField(blank=True)

    def __str__(self):
        return self.name

# MLLW
