from django.urls import path, include
from market import views

urlpatterns = [
    path('', views.chart_page, name='chart'),
]
