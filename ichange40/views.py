from django.shortcuts import render

# Create your views here.

from api import views


def index(request, pair: str = None, code: str = None):
    return render(request, "ichange40/index.html")
