from django.urls import path

from . import views


app_name = "custom_admin"


urlpatterns = [
    path("top_pairs", views.top_pairs, name="top_pairs"),
]
