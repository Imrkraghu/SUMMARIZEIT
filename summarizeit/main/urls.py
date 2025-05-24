from django.urls import path
from . import views

urlpatterns = [
    path('',views.home, name='home'),
    path('index/', views.index, name='index'),
    path('record/', views.record_audio, name='record_audio'),
     path("", views.SummarizeIT, name="SummarizeIT"),
    path("projects/", views.projects, name="projects"),
    path("team/", views.team, name="team"),
    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),
    path('stop/', views.stop_recording, name='stop_recording'),
]