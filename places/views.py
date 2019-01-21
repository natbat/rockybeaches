from django.shortcuts import render, get_object_or_404
from .models import Place, Station

def place(request, slug):
    place = get_object_or_404(Place, slug=slug)
    return render(request, 'place.html', {
        'place': place,
    })
