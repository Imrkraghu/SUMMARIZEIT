from django.urls import path, include
from . import views

urlpatterns = [
    path('',views.home, name='home'),
    # path("", views.SummarizeIT, name="SummarizeIT"),
    path("projects/", views.projects, name="projects"),
    path("team/", views.team, name="team"),
    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),
    path('', include('chat.urls')),
    path('', include('summarizer.urls')),
]