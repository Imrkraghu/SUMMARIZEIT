import os
import wave
import torch
import pyaudio
import nltk
import requests
import pandas as pd
import speech_recognition as sr
import time
from collections import Counter
from bs4 import BeautifulSoup
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from transformers import BertTokenizer, BertModel, BartForConditionalGeneration, BartTokenizer as BARTTokenizer
from django.core.cache import cache
from django.conf import settings

import threading
import queue

# NLTK Setup

NLTK_CUSTOM_PATH = os.path.join(settings.BASE_DIR, 'nltk_resources')
os.makedirs(NLTK_CUSTOM_PATH, exist_ok=True)
nltk.data.path.append(NLTK_CUSTOM_PATH)

def is_resource_available(resource_path):
    try:
        nltk.data.find(resource_path)
        return True
    except LookupError:
        return False

for resource in ['punkt', 'stopwords']:
    if not is_resource_available(f'tokenizers/{resource}') and not is_resource_available(f'corpora/{resource}'):
        nltk.download(resource, download_dir=NLTK_CUSTOM_PATH)

# Record Audio
def record_audio_to_file(OUTPUT_FILENAME=os.path.join(settings.MEDIA_ROOT, "recordings", "recorded_audio.wav")):
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 44100
    CHUNK = 1024

    try:
        audio = pyaudio.PyAudio()
        stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                            input=True, frames_per_buffer=CHUNK)
        print("Recording...")

        frames = []
        while cache.get("recording_active", False):
            data = stream.read(CHUNK)
            frames.append(data)
            time.sleep(0.01)

        print("Recording finished.")
        stream.stop_stream()
        stream.close()
        audio.terminate()

        with wave.open(OUTPUT_FILENAME, 'wb') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(audio.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames))

        return OUTPUT_FILENAME
    except OSError as e:
        print(f"OSError: {e}")
        return None

# Transcribe Audio
def transcribe_audio(OUTPUT_FILENAME="recorded_audio.wav"):
    recognizer = sr.Recognizer()
    with sr.AudioFile(OUTPUT_FILENAME) as source:
        audio = recognizer.record(source)

    try:
        text = recognizer.recognize_google(audio)
        print("Transcription:", text)
        with open(os.path.join(settings.MEDIA_ROOT, "transcriptions", "transcription.txt"),"w") as f:
            f.write(text)
        return text
    except sr.UnknownValueError:
        print("Speech Recognition could not understand the audio.")
    except sr.RequestError as e:
        print(f"Could not request results; {e}")
    return ""

# Extract Keywords
def extract_keywords_from_text():
    with open(os.path.join(settings.MEDIA_ROOT, "transcriptions", "transcription.txt"),"r") as file:
        text = file.read()

    words = word_tokenize(text)
    words = [word.lower() for word in words if word.isalnum()]
    stop_words = set(stopwords.words("english"))
    filtered_words = [word for word in words if word not in stop_words]
    word_freq = Counter(filtered_words)
    keywords = [kw for kw, _ in word_freq.most_common(10)]

    with open(os.path.join(settings.MEDIA_ROOT, "keywords", "keywords.txt"),"w") as file:
        for keyword in keywords:
            file.write(f"{keyword}\n")

    print("Top keywords:", keywords)
    return keywords

# Filter Keywords
def extract_valid_keywords():
    with open(os.path.join(settings.MEDIA_ROOT, "keywords", "keywords.txt"), "r") as file:
        keywords = [kw.strip() for kw in file.readlines()]
    
    dataset_path = os.path.join(settings.BASE_DIR, 'main', 'data', 'dataset.csv')
    df = pd.read_csv(dataset_path)
    valid_set = set()
    for column in df.columns:
        valid_set.update(df[column].dropna().str.lower().str.strip().tolist())

    filtered_keywords = [kw for kw in keywords if kw.lower() in valid_set]
    print("Filtered keywords:", filtered_keywords)
    return filtered_keywords

# Generate Summary
def generate_summary(text, model, tokenizer):
    inputs = tokenizer(text, return_tensors='pt', padding=True, truncation=True, max_length=1024)
    summary_ids = model.generate(inputs['input_ids'], num_beams=4, max_length=150, early_stopping=True)
    return tokenizer.decode(summary_ids[0], skip_special_tokens=True)

# Fetch Wikipedia & Summarize
def fetch_summary_for_keyword(keyword, model, tokenizer):
    try:
        print(f"Fetching summary for: {keyword}")
        url = f"https://en.wikipedia.org/wiki/{keyword}"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.content, "html.parser")
        paragraphs = soup.find_all("p")
        extracted_text = " ".join(p.get_text() for p in paragraphs[:3]).strip()
        return generate_summary(extracted_text, model, tokenizer)
    except Exception as e:
        print(f"Failed to summarize {keyword}: {e}")
        return "Summary unavailable."

# Main Pipeline
def run_summarizer_pipeline(results):
    # this will ensure that these folder exist and if not create at the runtime
    for folder in ["recordings", "transcriptions", "keywords"]:
        os.makedirs(os.path.join(settings.MEDIA_ROOT, folder), exist_ok=True)

    summaries = []

    audio_path = "recorded_audio.wav"
    if not os.path.exists(audio_path):
        return "", [], []

    transcription = transcribe_audio(audio_path)
    if not transcription.strip():
        return "", [], []

    keywords = extract_keywords_from_text()
    filtered_keywords = extract_valid_keywords()

    bart_model = BartForConditionalGeneration.from_pretrained('facebook/bart-large-cnn')
    bart_tokenizer = BARTTokenizer.from_pretrained('facebook/bart-large-cnn')

    for keyword in filtered_keywords:
        summary = fetch_summary_for_keyword(keyword, bart_model, bart_tokenizer)
        summaries.append({'keyword': keyword, 'text': summary})
        print(f"\nSummary for '{keyword}':\n{summary}\n")

    # return transcription, filtered_keywords, summaries
    # this is a test code you can remove this part
    results.put(transcription)
    results.put(keywords)
    results.put(summaries)

# Test Entry
if __name__ == "__main__":
    transcription, keywords, summaries = run_summarizer_pipeline()