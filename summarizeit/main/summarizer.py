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

# Global threading variables
audio_queue = queue.Queue()
processing_threads = []
recording_counter = 0

# Record Audio
def record_audio_to_file(OUTPUT_FILENAME=None):
    global recording_counter
    
    if OUTPUT_FILENAME is None:
        recording_counter += 1
        OUTPUT_FILENAME = os.path.join(settings.MEDIA_ROOT, "recordings", f"recorded_audio_{recording_counter}.wav")
    
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

        if frames:  # Only save if we recorded something
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
def transcribe_audio(OUTPUT_FILENAME="recorded_audio.wav"):
    recognizer = sr.Recognizer()
    with sr.AudioFile(OUTPUT_FILENAME) as source:
        audio = recognizer.record(source)

    try:
        text = recognizer.recognize_google(audio)
        print("Transcription:", text)
        # Create unique transcription file for each audio
        base_name = os.path.splitext(os.path.basename(OUTPUT_FILENAME))[0]
        transcription_file = os.path.join(settings.MEDIA_ROOT, "transcriptions", f"{base_name}_transcription.txt")
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

    # Create unique keywords file for each transcription
    base_name = os.path.splitext(os.path.basename(transcription_file))[0]
    keywords_file = os.path.join(settings.MEDIA_ROOT, "keywords", f"{base_name}_keywords.txt")
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
def run_summarizer_pipeline(audio_file, results):
    # Ensure that these folders exist and if not create at runtime
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
        # Still put the transcription and empty results
        results.put(transcription)
        results.put([])
        results.put([])
        return

    bart_model = BartForConditionalGeneration.from_pretrained('facebook/bart-large-cnn')
    bart_tokenizer = BARTTokenizer.from_pretrained('facebook/bart-large-cnn')

    for keyword in filtered_keywords:
        summary = fetch_summary_for_keyword(keyword, bart_model, bart_tokenizer)
        summaries.append({'keyword': keyword, 'text': summary})
        print(f"\nSummary for '{keyword}':\n{summary}\n")

    # Put results in queue
    results.put(transcription)
    results.put(filtered_keywords)
    results.put(summaries)

# Threading Functions

def start_recording_thread():
    """Start continuous recording in a separate thread"""
    def record_loop():
        cache.set("recording_active", True)
        segment_duration = 5  # Record in 5-second segments
        
        while cache.get("recording_active", False):
            # Record a segment
            recorded_file = record_audio_segment(segment_duration)
            if recorded_file:
                print(f"Recorded segment: {recorded_file}")
                audio_queue.put(recorded_file)
            time.sleep(0.1)  # Small delay between segments
        print("Recording thread stopped")
    
    thread = threading.Thread(target=record_loop, daemon=True)
    thread.start()
    return thread

def record_audio_segment(duration_seconds):
    """Record a single audio segment"""
    global recording_counter
    recording_counter += 1
    
    OUTPUT_FILENAME = os.path.join(settings.MEDIA_ROOT, "recordings", f"segment_{recording_counter}_{int(time.time())}.wav")
    
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 44100
    CHUNK = 1024

    try:
        audio = pyaudio.PyAudio()
        stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                            input=True, frames_per_buffer=CHUNK)
        
        frames = []
        start_time = time.time()
        
        while (time.time() - start_time) < duration_seconds and cache.get("recording_active", False):
            data = stream.read(CHUNK)
            frames.append(data)

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
    except Exception as e:
        print(f"Error recording segment: {e}")
        return None

def process_audio_worker(results):
    """Worker thread to process audio files from queue"""
    while True:
        try:
            audio_path = audio_queue.get(timeout=2)
            if audio_path is None:  # Sentinel value to stop thread
                break
            print(f"Processing audio file: {audio_path}")
            run_summarizer_pipeline(audio_path, results)
            audio_queue.task_done()
        except queue.Empty:
            # Check if recording is still active, if not, break
            if not cache.get("recording_active", False):
                break
            continue
        except Exception as e:
            print(f"Error processing audio: {e}")
            audio_queue.task_done()
    print("Processing worker stopped")

def start_processing_threads(num_threads=3):
    """Start multiple processing worker threads"""
    results = queue.Queue()
    processing_threads.clear()
    
    for i in range(num_threads):
        t = threading.Thread(target=process_audio_worker, args=(results,), daemon=True)
        t.start()
        processing_threads.append(t)
        print(f"Started processing thread {i+1}")
    
    return results

def stop_all(record_thread):
    """Stop recording and wait for all processing to complete"""
    print("Stopping all threads...")
    cache.set("recording_active", False)
    
    if record_thread:
        record_thread.join()
        print("Recording thread joined")
    
    # Wait for queue to empty
    audio_queue.join()
    print("Audio queue emptied")
    
    # Send stop signals to all processing threads
    for _ in processing_threads:
        audio_queue.put(None)
    
    # Wait for all processing threads to finish
    for t in processing_threads:
        t.join()
    
    processing_threads.clear()
    print("All threads stopped")

# Test Entry
if __name__ == "__main__":
    # For testing purposes
    results = queue.Queue()
    transcription, keywords, summaries = run_summarizer_pipeline("test_audio.wav", results)