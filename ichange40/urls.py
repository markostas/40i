from django.urls import path

from . import views


urlpatterns = [
    path("", views.index),
    path("change/<str:pair>", views.index),
    path("reserves", views.index),
    path("status/<str:code>", views.index),
    path("contacts/",  views.index)
]
