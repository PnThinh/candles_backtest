from django.urls import path, include
from market import views

urlpatterns = [
    path('', views.chart_page, name='chart'),
    path('api/load-data/', views.load_data_api, name='load_data_api'),
]
