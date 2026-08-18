# 🎙️ SUMMARIZEIT

**AI-Powered Real-Time Speech Summarization Platform**

**SUMMARIZEIT** is an intelligent, real-time speech-to-summary system designed to transcribe spoken language and generate concise, contextual summaries. Built for meetings, lectures, interviews, and more, it transforms audio into searchable insights using cutting-edge NLP and deep learning models.

---

## ✨ Features

- **Live Transcription Streaming** – Transcriptions update instantly as audio is processed
- **Keyword Extraction** – Context-aware keyword identification using NLTK and Transformers
- **Automatic Summarization** – Generates meaningful summaries using BART
- **Web Interface** – Interactive browser-based UI powered by Django
- **Threaded Audio Processing** – Efficient multi-threaded architecture for scalable workloads

---

## 🧠 Tech Stack

| Layer        | Tools & Libraries |
|--------------|-------------------|
| Frontend     | HTML, CSS, JavaScript, Bootstrap |
| Backend      | Python, Django |
| Audio Input  | PyAudio, SpeechRecognition |
| NLP & ML     | Rake NLTK, Transformers (BART), PyTorch |
| Caching      | Django Cache Framework |
| Database     | Sqlite |
---

## 📦 Installation Guide

1. **Clone the Repository**

   ```bash
   git clone https://github.com/Imrkraghu/SUMMARIZEIT.git
   cd SUMMARIZEIT


2. **Create a Virtual Environment**:

   ```bash
   python3 -m venv venv
   source venv/scripts/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**:

   ```
   pip install -r requirements.txt
   ```

4. **Run Database Migrations** (if needed):

   ```bash
   python manage.py migrate
   ```

---

## 🚀 Run the Application

To start the Django development server:

```bash
python manage.py runserver
```

Then open your browser and visit:

```
http://localhost:8000
```

---

## 📂 Project Structure

```
SUMMARIZEIT/
├── manage.py 
├── main      # main project 
├── media
├── db.sqlite # database to store summaries
├── nltk_resources   
├── summarizeit         
├── summarizeit/   # Django project settings
├── requirements.txt   #project requirements
└── README.md
```

---

## 📫 Contact

For questions or feedback, please contact [Imrkraghu](mailto:rohitgitpro@gmail.com).
