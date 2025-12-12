import os
import wave
import torch
import pyaudio
import nltk
import requests
import pandas as pd
import speech_recognition as sr
from collections import Counter
from bs4 import BeautifulSoup
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from transformers import BartForConditionalGeneration, BartTokenizer as BARTTokenizer
from django.core.cache import cache
from django.conf import settings
import threading
import queue
import time
from .models import SummaryCache


# NLTK Setup
NLTK_CUSTOM_PATH = os.path.join(settings.BASE_DIR, 'nltk_resources')
os.makedirs(NLTK_CUSTOM_PATH, exist_ok=True)
nltk.data.path.append(NLTK_CUSTOM_PATH)

# Load BART model and tokenizer once
bart_model = BartForConditionalGeneration.from_pretrained('facebook/bart-large-cnn')
bart_tokenizer = BARTTokenizer.from_pretrained('facebook/bart-large-cnn')

def is_resource_available(resource_path):
    try:
        nltk.data.find(resource_path)
        return True
    except LookupError:
        return False

for resource in ['punkt', 'stopwords', 'punkt_tab']:
    if not is_resource_available(f'tokenizers/{resource}') and not is_resource_available(f'corpora/{resource}'):
        nltk.download(resource, download_dir=NLTK_CUSTOM_PATH)

# Global threading variables
audio_queue = queue.Queue()
processing_threads = []
recording_counter = 0

# Record Audio
def record_audio_to_file(OUTPUT_FILENAME=None, duration=10):
    global recording_counter
    if OUTPUT_FILENAME is None:
        recording_counter += 1
        OUTPUT_FILENAME = os.path.join(settings.MEDIA_ROOT, "recordings", f"recorded_audio_{recording_counter}.wav")
    output_dir = os.path.dirname(OUTPUT_FILENAME)
    os.makedirs(output_dir, exist_ok=True)

    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 44100
    CHUNK = 1024
    NUM_CHUNKS = int(RATE / CHUNK * duration)
    try:
        audio = pyaudio.PyAudio()
        stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
        print(f"Recording for {duration} seconds...")

        frames = []
        for _ in range(NUM_CHUNKS):
            data = stream.read(CHUNK)
            frames.append(data)

        print("Recording finished.")
        stream.stop_stream()
        stream.close()
        audio.terminate()

        if frames:
            with wave.open(OUTPUT_FILENAME, 'wb') as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(audio.get_sample_size(FORMAT))
                wf.setframerate(RATE)
                wf.writeframes(b''.join(frames))
            return OUTPUT_FILENAME
        return None
    except OSError as e:
        print(f"OSError: {e}")
        return None

# Transcribe Audio
def transcribe_audio(OUTPUT_FILENAME="recorded_audio_1.wav"):
    recognizer = sr.Recognizer()
    with sr.AudioFile(OUTPUT_FILENAME) as source:
        audio = recognizer.record(source)
    try:
        text = recognizer.recognize_google(audio)
        print("Transcription:", text)
        base_name = os.path.splitext(os.path.basename(OUTPUT_FILENAME))[0]
        transcription_file = os.path.join(settings.MEDIA_ROOT, "transcriptions", f"{base_name}_transcription.txt")
        os.makedirs(os.path.dirname(transcription_file), exist_ok=True)
        with open(transcription_file, "w") as f:
            f.write(text)
        return text, transcription_file
    except sr.UnknownValueError:
        print("Speech Recognition could not understand the audio.")
    except sr.RequestError as e:
        print(f"Could not request results; {e}")
    return "", None

# Extract Keywords
def extract_keywords_from_text(transcription_file):
    with open(transcription_file, "r") as file:
        text = file.read()
    words = word_tokenize(text)
    words = [word.lower() for word in words if word.isalnum()]
    stop_words = set(stopwords.words("english"))
    filtered_words = [word for word in words if word not in stop_words]
    word_freq = Counter(filtered_words)
    keywords = [kw for kw, _ in word_freq.most_common(10)]

    base_name = os.path.splitext(os.path.basename(transcription_file))[0]
    keywords_file = os.path.join(settings.MEDIA_ROOT, "keywords", f"{base_name}_keywords.txt")
    os.makedirs(os.path.dirname(keywords_file), exist_ok=True)
    with open(keywords_file, "w") as file:
        for keyword in keywords:
            file.write(f"{keyword}\n")

    print("Top keywords:", keywords)
    return keywords, keywords_file

# Filter Keywords
def extract_valid_keywords(keywords_file):
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

# Generate Summary-
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
def run_summarizer_pipeline(audio_file, results, counter=1):
    for folder in ["recordings", "transcriptions", "keywords"]:
        os.makedirs(os.path.join(settings.MEDIA_ROOT, folder), exist_ok=True)

    summaries = []
    if not os.path.exists(audio_file):
        print(f"Audio file {audio_file} does not exist")
        return

    transcription, transcription_file = transcribe_audio(audio_file)
    if not transcription.strip() or not transcription_file:
        print("No transcription available")
        return

    keywords, keywords_file = extract_keywords_from_text(transcription_file)
    filtered_keywords = extract_valid_keywords(keywords_file)

    if not filtered_keywords:
        print("No valid keywords found")
        results.put(transcription)
        results.put([])
        results.put([])
        return

    for keyword in filtered_keywords:
        try:
            summary = SummaryCache.objects.get(keyword=keyword)
            summaries.append({'keyword': keyword, 'text': summary.summary_text})
            print(f"\nSummary for '{keyword}':\n{summary.summary_text}\n")
        except SummaryCache.DoesNotExist:
            try:
                summary = fetch_summary_for_keyword(keyword, bart_model, bart_tokenizer)
                SummaryCache.objects.create(keyword=keyword, summary_text=summary)
                summaries.append({'keyword': keyword, 'text': summary})
                print(f"\nSummary for '{keyword}':\n{summary}\n")
            except Exception as e:
                print(f"error while saving to database : {e}")  

    results.put(transcription)
    results.put(filtered_keywords)
    results.put(summaries)

# Threading Functions
def start_recording_thread():
    def record_loop():
        cache.set("recording_active", True)
        global recording_counter
        while cache.get("recording_active", False):
            recording_counter += 1
            output_filename = os.path.join(settings.MEDIA_ROOT, "recordings", f"recorded_audio_{recording_counter}.wav")
            recorded_file = record_audio_to_file(output_filename, duration=10)
            if recorded_file:
                print(f"Recorded audio: {recorded_file}")
                audio_queue.put(recorded_file)
            time.sleep(1)  # Small delay in between recordings
        print("Recording thread stopped")

    thread = threading.Thread(target=record_loop, daemon=True)
    thread.start()
    return thread

def process_audio_worker(results):
    while True:
        try:
            audio_path = audio_queue.get(timeout=2)
            if audio_path is None:
                break
            print(f"Processing audio file: {audio_path}")
            run_summarizer_pipeline(audio_path, results)
            audio_queue.task_done()
        except queue.Empty:
            if not cache.get("recording_active", False):
                break
            continue
        except Exception as e:
            print(f"Error processing audio: {e}")
            audio_queue.task_done()
    print("Processing worker stopped")

def start_processing_threads(num_threads=1):
    results = queue.Queue()
    processing_threads.clear()
    for i in range(num_threads):
        t = threading.Thread(target=process_audio_worker, args=(results,), daemon=True)
        t.start()
        processing_threads.append(t)
        print(f"Started processing thread {i+1}")
    return results

def stop_all(record_thread):
    print("Stopping all threads...")
    cache.set("recording_active", False)
    if record_thread:
        record_thread.join()
        print("Recording thread joined")
    audio_queue.join()
    print("Audio queue emptied")
    for _ in processing_threads:
        audio_queue.put(None)
    for t in processing_threads:
        t.join()
    processing_threads.clear()
    print("All threads stopped")

# Test Entry
if __name__ == "__main__":
    results = queue.Queue()
    # Example single recording/test
    record_thread = start_recording_thread()
    results = start_processing_threads(1)
    stop_all(record_thread)