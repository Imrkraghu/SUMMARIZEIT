from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.conf import settings
import json
import logging
import os
import time
from main.models import SummaryCache 
from summarizer.summarizer import (
    fetch_summary_for_keyword,
    extract_keywords_from_text,
    extract_valid_keywords
)


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
        keywords, keywords_file = extract_keywords_from_text(message_file)
        filtered_keywords = extract_valid_keywords(keywords_file)
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
                summary_text = fetch_summary_for_keyword(keyword)
                if summary_text == "No summary available":
                    logger.warning("Summary not available for %s", keyword)
                    source = 'unavailable'
                elif isinstance(summary_text, dict) and 'summary_text' in summary_text:
                    summary_text = summary_text['summary_text']
                    SummaryCache.objects.create(keyword=keyword, summary_text=summary_text)
                    source = 'generated'
        except Exception:
            logger.exception("Summary fetch failed for %s", keyword)
            summary_text, source = None, 'error'

        if summary_text:
            if isinstance(summary_text, dict) and 'summary_text' in summary_text:
                summary_text = summary_text['summary_text']
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