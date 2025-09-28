from django.shortcuts import render, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.core.cache import cache
import time
import threading
import queue
import json

from .summarizer import (
    start_recording_thread, 
    start_processing_threads, 
    stop_all, 
    audio_queue, 
    processing_threads
)

# Global variables to hold threads and results queue
record_thread = None
results_queue = None

@csrf_exempt
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
@require_POST
def record_audio(request):
    """Start recording audio and processing threads"""
    global record_thread, results_queue

    # Check if recording is already active
    if cache.get("recording_active", False):
        return JsonResponse({'error': 'Recording already in progress'}, status=400)

    try:
        # Clear any previous state
        cache.set("recording_active", False)  # Reset first
        time.sleep(0.1)  # Brief pause
        
        # Clear existing queue items
        while not audio_queue.empty():
            try:
                audio_queue.get_nowait()
                audio_queue.task_done()
            except queue.Empty:
                break

        # Clear processing threads list
        processing_threads.clear()

        # Start recording thread
        record_thread = start_recording_thread()
        
        # Start processing threads (3 worker threads)
        results_queue = start_processing_threads(num_threads=3)

        # this is the part which will send the json response for the continue
        transcription = request.session.get('transcription', '')
        keywords = request.session.get('keywords', [])
        summaries = request.session.get('summaries', []) 
        return JsonResponse({
            "transcription": transcription,
            "keywords": keywords,
            "summaries": summaries,
            "message": "recording started successfully"
        })

    except Exception as e:
        cache.set("recording_active", False)
        return JsonResponse({'error': f'Failed to start recording: {str(e)}'}, status=500)

@csrf_exempt
@require_POST
def stop_recording(request):
    """Stop recording and collect all results"""
    global record_thread, results_queue

    if not cache.get("recording_active", False):
        return JsonResponse({'error': 'No active recording to stop'}, status=400)

    try:
        # Signal to stop recording
        cache.set("recording_active", False)

        # Wait for recording thread to finish
        if record_thread and record_thread.is_alive():
            record_thread.join(timeout=10)

        # Wait for all queued audio to be processed
        audio_queue.join()

        # Stop all processing threads gracefully
        for _ in processing_threads:
            audio_queue.put(None)  # Sentinel value

        # Wait for processing threads to finish
        for t in processing_threads:
            if t.is_alive():
                t.join(timeout=5)

        # Collect all results from results_queue
        all_transcriptions = []
        all_keywords = []
        all_summaries = []

        while not results_queue.empty():
            try:
                transcription = results_queue.get_nowait()
                keywords = results_queue.get_nowait()  
                summaries = results_queue.get_nowait()

                if transcription and transcription.strip():
                    all_transcriptions.append(transcription)
                
                if keywords:
                    all_keywords.extend(keywords)
                
                if summaries:
                    all_summaries.extend(summaries)

            except queue.Empty:
                break

        # Combine all transcriptions
        combined_transcription = " | ".join(all_transcriptions) if all_transcriptions else ""
        
        # Remove duplicate keywords while preserving order
        seen = set()
        unique_keywords = []
        for keyword in all_keywords:
            if keyword not in seen:
                seen.add(keyword)
                unique_keywords.append(keyword)

        # Save results to session
        request.session['transcription'] = combined_transcription
        request.session['keywords'] = unique_keywords
        request.session['summaries'] = all_summaries

        # Clean up
        processing_threads.clear()
        record_thread = None
        results_queue = None

        return JsonResponse({
            "transcription": combined_transcription,
            "keywords": unique_keywords,
            "summaries": all_summaries,
            "message": "Recording stopped and processed successfully"
        })

    except Exception as e:
        cache.set("recording_active", False)
        return JsonResponse({'error': f'Error stopping recording: {str(e)}'}, status=500)

@csrf_exempt
def get_status(request):
    """Get current recording status"""
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