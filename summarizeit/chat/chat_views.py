from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse, HttpResponseBadRequest
from django.conf import settings
import json
import logging
import os
import time
import pandas as pd
import nltk
from collections import Counter
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from rake_nltk import Rake
from transformers import BartForConditionalGeneration, BartTokenizer as BARTTokenizer
from main.models import SummaryCache 
from main.summarizer import (
    fetch_summary_for_keyword
)

# Load BART model and tokenizer once
bart_model = BartForConditionalGeneration.from_pretrained('facebook/bart-large-cnn')
bart_tokenizer = BARTTokenizer.from_pretrained('facebook/bart-large-cnn')
NLTK_CUSTOM_PATH = os.path.join(settings.BASE_DIR, 'nltk_resources')

def is_resource_available(resource_path):
    try:
        nltk.data.find(resource_path)
        return True
    except LookupError:
        return False

for resource in ['punkt', 'stopwords', 'punkt_tab']:
    if not is_resource_available(f'tokenizers/{resource}') and not is_resource_available(f'corpora/{resource}'):
        nltk.download(resource, download_dir=NLTK_CUSTOM_PATH)

def extract_keywords(transcription_file):
    with open(transcription_file, "r", encoding="utf-8") as file:
        text = file.read()

    r = Rake()
    r.extract_keywords_from_text(text)
    keywords = r.get_ranked_phrases()[:10]

    base_name = os.path.splitext(os.path.basename(transcription_file))[0]
    keywords_file = os.path.join(settings.MEDIA_ROOT, "keywords", f"{base_name}_keywords.txt")
    os.makedirs(os.path.dirname(keywords_file), exist_ok=True)

    with open(keywords_file, "w", encoding="utf-8") as file:
        for keyword in keywords:
            file.write(f"{keyword}\n")
    print("Top keywords:", keywords)
    return keywords, keywords_file

def valid_keywords(keywords_file):
    with open(keywords_file, "r") as file:
        keywords = [kw.strip() for kw in file.readlines()]
    dataset_path = os.path.join(settings.BASE_DIR, 'main', 'data', 'dataset.csv')
    df = pd.read_csv(dataset_path)
    valid_set = set()
    for column in df.columns:
        valid_set.update(df[column].dropna().str.lower().str.strip().tolist())
    filtered_keywords = [kw for kw in keywords if kw.lower() in valid_set]
    print("Filtered keywords:", filtered_keywords)
    return filtered_keywords


logger = logging.getLogger(__name__)

@require_http_methods(["GET", "POST"])
def index(request):
    if request.method == "GET":
        # Get history from session
        history = request.session.get('chat_history', [])
        return render(request, "chat/chat.html", {'history': history})

    # POST Logic
    try:
        payload = json.loads(request.body.decode("utf-8"))
        message = (payload.get("message") or "").strip()
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    if not message:
        return JsonResponse({'error': 'Empty message'}, status=400)

    # 1. Save message to a unique file
    timestamp = int(time.time())
    chat_dir = os.path.join(settings.MEDIA_ROOT, "chat")
    os.makedirs(chat_dir, exist_ok=True)
    message_file = os.path.join(chat_dir, f"msg_{timestamp}.txt")
    
    with open(message_file, "w", encoding="utf-8") as f:
        f.write(message)

    # 2. Keyword extraction
    try:
        # Assuming extract_keywords_from_text returns (list, path_to_file)
        keywords, keywords_file = extract_keywords(message_file)
        filtered_keywords = valid_keywords(keywords_file)
        # filtered_keywords = keywords
    except Exception as e:
        logger.exception("Extraction failed")
        filtered_keywords = []

    # 3. Process Keywords and get Summaries
    results = []
    for keyword in filtered_keywords:
        try:
            cached = SummaryCache.objects.filter(keyword=keyword).first()
            if cached:
                summary_text = cached.summary_text
                source = 'cache'
            else:
                summary_text = fetch_summary_for_keyword(keyword, bart_model, bart_tokenizer)
                if summary_text.strip() == "No summary available":
                    logger.warning("Summary not available for %s", keyword)
                    source = 'unavailable'

                if summary_text!="No summary available":
                    SummaryCache.objects.create(keyword=keyword, summary_text=summary_text)
                source = 'generated'
        except Exception:
            logger.exception("Summary fetch failed for %s", keyword)
            summary_text, source = None, 'error'

        if summary_text:
            results.append({
                'keyword': keyword,
                'text': summary_text or "No summary available",
                'source': source
            })


    # 4. Update Session History
    entry = {
        'message': message,
        'keywords': filtered_keywords,
        'results': results,
        'timestamp': time.strftime('%H:%M')
    }
    
    history = request.session.get('chat_history', [])
    history.append(entry)
    request.session['chat_history'] = history
    request.session.modified = True

    return JsonResponse({
        'reply': f"Processed and found {len(results)} summary(ies).",
        'keywords': filtered_keywords,
        'results': results,
        'entry': entry
    })