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
from transformers import BertTokenizer, BertModel, BartForConditionalGeneration, BartTokenizer as BARTTokenizer

# Define custom NLTK data path
NLTK_CUSTOM_PATH = 'nltk_resources'
os.makedirs(NLTK_CUSTOM_PATH, exist_ok=True)
nltk.data.path.append(NLTK_CUSTOM_PATH)

# Download required NLTK resources
def is_resource_available(resource_path):
    try:
        nltk.data.find(resource_path)
        return True
    except LookupError:
        return False

for resource in ['punkt', 'stopwords']:
    if not is_resource_available(f'tokenizers/{resource}') and not is_resource_available(f'corpora/{resource}'):
        nltk.download(resource, download_dir=NLTK_CUSTOM_PATH)

# 1. Record Audio
def record_audio_to_file(OUTPUT_FILENAME="recorded_audio.wav", duration=10):
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 44100
    CHUNK = 1024

    try:
        audio = pyaudio.PyAudio()
        stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                            input=True, frames_per_buffer=CHUNK)
        print("Recording...")

        frames = [stream.read(CHUNK) for _ in range(0, int(RATE / CHUNK * duration))]

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

# 2. Transcribe Audio
def transcribe_audio(OUTPUT_FILENAME="recorded_audio.wav"):
    recognizer = sr.Recognizer()
    with sr.AudioFile(OUTPUT_FILENAME) as source:
        audio = recognizer.record(source)

        try:
            text = recognizer.recognize_google(audio)
            print("Transcription:", text)
            with open("transcription.txt", "w") as f:
                f.write(text)
            return text
        except sr.UnknownValueError:
            print("Speech Recognition could not understand the audio.")
        except sr.RequestError as e:
            print(f"Could not request results; {e}")
        return ""

# 3. Extract Keywords from Transcription
def extract_keywords_from_text():
    with open("transcription.txt", "r") as file:
        text = file.read()

    words = word_tokenize(text)
    words = [word.lower() for word in words if word.isalnum()]
    stop_words = set(stopwords.words("english"))
    filtered_words = [word for word in words if word not in stop_words]
    word_freq = Counter(filtered_words)
    keywords = [kw for kw, _ in word_freq.most_common(10)]

    with open("keywords.txt", "w") as file:
        for keyword in keywords:
            file.write(f"{keyword}\n")

    print("Top keywords:", keywords)
    return keywords

# 4. Filter Keywords using BERT and Dataset
def extract_valid_keywords(num_keywords=5):
    model = BertModel.from_pretrained('bert-base-uncased')
    tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')

    with open("keywords.txt", "r") as file:
        text = file.read()

    df = pd.read_csv("dataset.csv")
    valid_keywords = set()
    for column in df.columns:
        valid_keywords.update(df[column].dropna().str.strip().tolist())

    inputs = tokenizer(text, return_tensors='pt')
    with torch.no_grad():
        outputs = model(**inputs)
        last_hidden_states = outputs.last_hidden_state

    tokens = tokenizer.convert_ids_to_tokens(inputs['input_ids'][0])
    cls_embedding = last_hidden_states[:, 0, :].squeeze()
    similarities = torch.matmul(last_hidden_states.squeeze(), cls_embedding)
    top_indices = similarities.topk(min(num_keywords, len(similarities))).indices

    keywords = [tokens[i] for i in top_indices if tokens[i] != '[CLS]' and tokens[i] in valid_keywords]
    print("Filtered keywords:", keywords)
    return keywords

# 5. Generate Summary
def generate_summary(text, model, tokenizer):
    inputs = tokenizer(text, return_tensors='pt', padding=True, truncation=True, max_length=1024)
    summary_ids = model.generate(inputs['input_ids'], num_beams=4, max_length=150, early_stopping=True)
    return tokenizer.decode(summary_ids[0], skip_special_tokens=True)

# 6. Fetch Wikipedia Content and Summarize
def fetch_summary_for_keyword(keyword, model, tokenizer):
    try:
        print(f"Fetching summary for: {keyword}")
        url = f"https://en.wikipedia.org/wiki/{keyword}"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.content, "html.parser")
        paragraphs = soup.find_all("p")
        extracted_text = " ".join([p.get_text() for p in paragraphs]).strip()
        # only taking first 500 words
        extracted_text = extracted_text[:500]
        return generate_summary(extracted_text, model, tokenizer)
    except Exception as e:
        print(f"Failed to summarize {keyword}: {e}")
        return "Summary unavailable."

# 7. Main Pipeline
def run_summarizer_pipeline():
    summaries = []

    # Step 1
    audio_path = record_audio_to_file()
    if not audio_path:
        return None, [], []

    # Step 2
    transcription = transcribe_audio(audio_path)

    # Step 3
    keywords = extract_keywords_from_text()

    # Step 4
    filtered_keywords = extract_valid_keywords()

    # Step 5
    bart_model = BartForConditionalGeneration.from_pretrained('facebook/bart-large-cnn')
    bart_tokenizer = BARTTokenizer.from_pretrained('facebook/bart-large-cnn')

    for keyword in filtered_keywords:
        summary = fetch_summary_for_keyword(keyword, bart_model, bart_tokenizer)
        summaries.append({'keyword': keyword, 'text': summary})
        print(f"\nSummary for '{keyword}':\n{summary}\n")

    return transcription, filtered_keywords, summaries

# Run pipeline
if __name__ == "__main__":
    transcription, keywords, summaries = run_summarizer_pipeline()