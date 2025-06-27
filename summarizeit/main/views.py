from django.shortcuts import render, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.core.cache import cache
import time
import threading
import queue

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
    # this is going to be a test for the threading of the process
    # starting the listening thread
    listener_thread = threading.Thread(target = record_audio_to_file)
    listener_thread.daemon = True # this allow program to exit even if this thread is running
    listener_thread.start()

    # processing the audio thread
    processor_thread = threading.Thread(target = run_summarizer_pipeline, args = (results,))
    processor_thread.daemon = True
    processor_thread.start()
    # completing the thread
    processor_thread.join()
    # retrieving the results from the queue
    transcription: results.get()
    keywords: results.get()
    summaries: results.get()

    return JsonResponse({
            "transcription": transcription,
            "keywords": keywords,
            "summaries": summaries,
        })
    # test code finish here

    cache.set("recording_active", True)
    # try:
    #     record_audio_to_file()
    #     return JsonResponse({'message': 'Recording started'})
    # except Exception as e:
    #     return JsonResponse({'error': str(e)})

@csrf_exempt
@require_POST

def stop_recording(request):
    if request.method == 'POST':
        cache.set("recording_active", False)  # STOP RECORDING
        time.sleep(1.0)  # give it a moment to finish writing the file
    #     transcription, keywords, summaries = run_summarizer_pipeline()
    #     return JsonResponse({
    #         "transcription": transcription,
    #         "keywords": keywords,
    #         "summaries": summaries,
    #     })

    processor_thread = threading.Thread(target = run_summarizer_pipeline, args = (results,))
    processor_thread.daemon = True
    processor_thread.start()
    # completing the thread
    processor_thread.join()
    # retrieving the results from the queue
    transcription: results.get()
    keywords: results.get()
    summaries: results.get()

    return JsonResponse({
            "transcription": transcription,
            "keywords": keywords,
            "summaries": summaries,
        })
    # return JsonResponse({
    #         "transcription": transcription,
    #         "keywords": keywords,
    #         "summaries": summaries,
    #     })


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