from django.shortcuts import render, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST,  require_http_methods
from django.http import JsonResponse
from django.core.cache import cache
import time
import queue
from .models import SummaryCache 

from summarizer.summarizer import (
    start_recording_thread, 
    start_processing_threads, 
    audio_queue, 
    processing_threads
)

# Global variables to hold threads and results
record_thread = None
results_queue = None

# Global accumulator for the current session
current_session_data = {
    "transcriptions": [],
    "keywords": [],
    "summaries": []
}

def collect_results_from_queue():
    """
    Helper function to drain the queue into the global storage
    without blocking the main thread.
    """
    global results_queue, current_session_data
    
    if not results_queue:
        return

    while not results_queue.empty():
        try:
            # The workers in summarizer.py should now be using the 
            # 'smart_summarize' function that checks the DB
            transcription = results_queue.get_nowait()
            keywords = results_queue.get_nowait()  
            summaries = results_queue.get_nowait()

            if transcription and transcription.strip():
                current_session_data["transcriptions"].append(transcription)
            
            if keywords:
                current_session_data["keywords"].extend(keywords)
            
            if summaries:
                # 'summaries' list contains objects like {'keyword': 'X', 'text': 'Y'}
                current_session_data["summaries"].extend(summaries)
                
        except queue.Empty:
            break
        except Exception as e:
            print(f"Error draining queue: {e}")
            break

def format_response_data():
    """Helper to format the current data for JSON response"""
    combined_transcription = " | ".join(current_session_data["transcriptions"])
    
    # Remove duplicates for keywords in the UI list
    seen = set()
    unique_keywords = []
    for keyword in current_session_data["keywords"]:
        if keyword not in seen:
            seen.add(keyword)
            unique_keywords.append(keyword)

    return {
        "transcription": combined_transcription,
        "keywords": unique_keywords,
        "summaries": current_session_data["summaries"]
    }

def index(request):
    transcription = request.session.get('transcription', '')
    keywords = request.session.get('keywords', [])
    summaries = request.session.get('summaries', [])
    
    return render(request, 'main/index.html', {
        'transcription': transcription,
        'keywords': keywords,
        'summaries': summaries
    })

@csrf_exempt
def get_latest_results(request):
    """Called by JS to get updates while recording/processing"""
    collect_results_from_queue() 
    data = format_response_data()
    
    is_processing = (audio_queue.qsize() > 0 or len(processing_threads) > 0)
    
    return JsonResponse({
        "transcription": data["transcription"],
        "keywords": data["keywords"],
        "summaries": data["summaries"],
        "is_processing": is_processing
    })

@csrf_exempt
@require_POST
def record_audio(request):
    """Start recording audio and processing threads"""
    global record_thread, results_queue, current_session_data

    if cache.get("recording_active", False):
        return JsonResponse({'error': 'Recording already in progress'}, status=400)

    try:
        # Reset Global Data
        current_session_data = {
            "transcriptions": [],
            "keywords": [],
            "summaries": []
        }
        
        cache.set("recording_active", False)
        time.sleep(0.1)
        
        # Clear queues
        while not audio_queue.empty():
            try:
                audio_queue.get_nowait()
                audio_queue.task_done()
            except queue.Empty:
                break

        processing_threads.clear()

        # Start threads
        record_thread = start_recording_thread()
        results_queue = start_processing_threads(num_threads=3)

        return JsonResponse({
            "transcription": "",
            "keywords": [],
            "summaries": [],
            "message": "recording started successfully"
        })

    except Exception as e:
        cache.set("recording_active", False)
        return JsonResponse({'error': f'Failed to start recording: {str(e)}'}, status=500)

@csrf_exempt
@require_POST
def stop_recording(request):
    """Stop recording and collect all results"""
    global record_thread, results_queue, current_session_data

    if not cache.get("recording_active", False):
        return JsonResponse({'error': 'No active recording to stop'}, status=400)

    try:
        cache.set("recording_active", False)

        if record_thread and record_thread.is_alive():
            record_thread.join(timeout=10)

        audio_queue.join()

        for _ in processing_threads:
            audio_queue.put(None)

        for t in processing_threads:
            if t.is_alive():
                t.join(timeout=5)

        collect_results_from_queue()
        final_data = format_response_data()

        request.session['transcription'] = final_data["transcription"]
        request.session['keywords'] = final_data["keywords"]
        request.session['summaries'] = final_data["summaries"]

        processing_threads.clear()
        record_thread = None
        results_queue = None

        return JsonResponse({
            "transcription": final_data["transcription"],
            "keywords": final_data["keywords"],
            "summaries": final_data["summaries"],
            "message": "Recording stopped and processed successfully"
        })

    except Exception as e:
        cache.set("recording_active", False)
        return JsonResponse({'error': f'Error stopping recording: {str(e)}'}, status=500)

@csrf_exempt
def get_status(request):
    is_recording = cache.get("recording_active", False)
    queue_size = audio_queue.qsize() if audio_queue else 0
    
    return JsonResponse({
        'is_recording': is_recording,
        'queue_size': queue_size,
        'processing_threads': len(processing_threads)
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