from django.db import models

from wagtail.core.models import Page
from wagtail.core.fields import RichTextField
from wagtail.admin.edit_handlers import FieldPanel, InlinePanel, MultiFieldPanel


class HomePage(Page):
    body = RichTextField(blank=True)

    parent_page_types = []

    content_panels = Page.content_panels + [
        FieldPanel('body', classname="full"),
    ]

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

class PlacePage(Page):
    # Basic Information
    tagline = models.CharField(max_length=255, blank=True)
    body = RichTextField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    website_url = models.URLField(blank=True)

    # Location
    latitude = models.FloatField()
    longitude = models.FloatField()
    radius_km = models.FloatField(default=0.5)
    station = models.ForeignKey(
        Station,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="places"
    )
    address = models.CharField(max_length=128, blank=True)

    # Logistics & Interpretation
    open_to_public = models.BooleanField(default=True)
    directions = RichTextField(blank=True)
    accessibility_and_safety = RichTextField(blank=True)
    entry_cost = models.CharField(max_length=128, blank=True)
    parking = RichTextField(blank=True)
    docents = models.BooleanField(default=False)
    visitor_center = models.BooleanField(default=False)

    # Other needs
    bathrooms = models.BooleanField(default=False)
    food_options = RichTextField(blank=True)
    dogs = models.BooleanField(default=False)
    pet_policy = RichTextField(blank=True)

    parent_page_types = ['home.HomePage']
    subpage_types = []

    def main_image(self):
        gallery_item = self.gallery_images.first()
        if gallery_item:
            return gallery_item.image
        else:
            return None

    # search_fields = Page.search_fields + [
    #     index.SearchField('name'),
    #     index.SearchField('tagline'),
    #     index.SearchField('body'),
    # ]

    content_panels = Page.content_panels + [
        MultiFieldPanel([
            FieldPanel('tagline'),
            FieldPanel('slug'),
            FieldPanel('body', classname="full"),
            FieldPanel('phone'),
            FieldPanel('website_url'),
        ], heading="Basic Information"),
        MultiFieldPanel([
            FieldPanel('latitude'),
            FieldPanel('longitude'),
            FieldPanel('radius_km'),
            FieldPanel('station'),
            FieldPanel('address'),
            FieldPanel('directions'),
        ], heading="Location"),
        MultiFieldPanel([
            FieldPanel('open_to_public'),
            FieldPanel('accessibility_and_safety'),
            FieldPanel('entry_cost'),
            FieldPanel('parking'),
            FieldPanel('docents'),
            FieldPanel('visitor_center'),
        ], heading="Logistics & Interpretation"),
        MultiFieldPanel([
            FieldPanel('bathrooms'),
            FieldPanel('food_options'),
            FieldPanel('dogs'),
            FieldPanel('pet_policy'),
        ], heading="Other Needs"),
    ]
