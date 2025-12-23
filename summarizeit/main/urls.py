from django.urls import path
from . import views
from . import chat_views

urlpatterns = [
    path('',views.home, name='home'),
    # path('chat/', chat_views.chat, name='chat'),
    # for original
    # path('index/', views.index, name='index'),
    # for new
    path('index/', chat_views.index, name='index'),
    path('record/', views.record_audio, name='record_audio'),
    path("", views.SummarizeIT, name="SummarizeIT"),
    path("projects/", views.projects, name="projects"),
    path("team/", views.team, name="team"),
    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),
    path('stop/', views.stop_recording, name='stop_recording'),
    path('get_latest_results/', views.get_latest_results, name='get_latest_results'),
]