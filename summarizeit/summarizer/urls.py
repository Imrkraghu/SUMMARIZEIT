from django.urls import path
from . import views
# app_name = "summarizer"
urlpatterns =[
    path('summarizer/', views.index, name="summarizeit" ),
    path('record/', views.record_audio, name='record_audio'),
    path('stop/', views.stop_recording, name='stop_recording'),
    path("get_status/", views.get_status, name='get_status'),
    path('get_latest_results/', views.get_latest_results, name='get_latest_results'),
    path('microphone_status/', views.microphone_status, name="microphone_status")
]