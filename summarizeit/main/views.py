from django.shortcuts import render, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.core.cache import cache
import time

from .summarizer import run_summarizer_pipeline, record_audio_to_file

@csrf_exempt
def index(request):
    transcription = request.session.get('transcription')
    keywords = request.session.get('keywords', [])
    summaries = request.session.get('summaries', [])
    return render(request, 'main/index.html', {
        'transcription': transcription,
        'keywords': keywords,
        'summaries': summaries
    })

@csrf_exempt
@require_POST
def record_audio(request):
    """Start recording audio by setting a cache flag."""
    cache.set("recording_active", True)
    try:
        record_audio_to_file()
        return JsonResponse({'message': 'Recording started'})
    except Exception as e:
        return JsonResponse({'error': str(e)})

@csrf_exempt
@require_POST

def stop_recording(request):
    if request.method == 'POST':
        cache.set("recording_active", False)  # STOP RECORDING
        time.sleep(1.0)  # give it a moment to finish writing the file
        transcription, keywords, summaries = run_summarizer_pipeline()
        return JsonResponse({
            "transcription": transcription,
            "keywords": keywords,
            "summaries": summaries,
        })


def SummarizeIT(request):
    return render(request, 'main/summarizeIT.html')

def home(request):
    return render(request, 'main/homepage.html')

def projects(request):
    return render(request, 'main/projects.html')

def about(request):
    return render(request, 'main/about.html')

def team(request):
    return render(request, 'main/team.html')

def contact(request):
    return render(request, 'main/contact.html')

def rohit(request):
    return HttpResponse("hello Sir, my master you are the almighty")