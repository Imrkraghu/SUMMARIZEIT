# core/views.py
from django.shortcuts import render, redirect, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .summarizer import run_summarizer_pipeline, transcribe_audio, extract_keywords_from_text

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
def record_audio(request):
    """Handles full audio recording, transcription, keyword extraction, and summary"""
    if request.method == 'POST':
        try:
            transcription, keywords, summaries = run_summarizer_pipeline()

            # Save results to session
            request.session['transcription'] = transcription
            request.session['keywords'] = keywords
            request.session['summaries'] = summaries

            return JsonResponse({
                'transcription': transcription,
                'keywords': keywords,
                'summaries': summaries
            })
        except Exception as e:
            return JsonResponse({'error': str(e)})
    return JsonResponse({'error': 'Invalid request method'})

def SummarizeIT(request):
    return render(request, 'main/summarizeIT.html')

def home(request):
    return render(request, 'main/homepage.html')

def projects(request):
    return render(request, 'main/projects.html')

def about(request):
    return render(request, "main/about.html")

def team(request):
    return render(request, "main/team.html")

def contact(request):
    return render(request, "main/contact.html")

def rohit(request):
    return HttpResponse("hello Sir, my master you are the almighty")