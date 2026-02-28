from django.urls import path
from . import views

app_name = 'skills_engine'

urlpatterns = [
    path('trending-skills/', views.TrendingSkillsView.as_view(), name='trending-skills'),
    path('health/', views.HealthCheckView.as_view(), name='health-check'),
]