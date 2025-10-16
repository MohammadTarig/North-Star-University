from django.urls import path
from .views import generate_project_assets

urlpatterns = [
    path("generate-assets/", generate_project_assets, name="generate_assets"),
]
