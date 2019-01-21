from django.contrib import admin
from django.urls import path
from places.views import place

urlpatterns = [
    path('admin/', admin.site.urls),
    path('places/<str:slug>/', place),
]
