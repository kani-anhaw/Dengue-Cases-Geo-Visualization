from django.urls import path
from . import views
app_name = 'final'  

urlpatterns = [
    path("", views.index, name="index"),
    path('others/', views.others, name='others'),
    path('analytics/', views.analytics, name='analytics'),
    path('bubbleMap/', views.bubble_map, name='bubbleMap')
    
]