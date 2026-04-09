from django.urls import path
from . import views
from . import chat_views  

urlpatterns = [
     path('chat/', chat_views.index, name='chat'),
]