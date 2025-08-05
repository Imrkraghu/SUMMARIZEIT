# SUMMARIZEIT

**AI-Powered Real-Time Speech Summarization Tool**

**SUMMARIZEIT** is an AI-driven platform that transcribes spoken language into concise, structured, and meaningful summaries. It captures audio from sources like meetings, interviews, or lectures and processes it using advanced speech recognition and NLP models. The platform is designed to enhance productivity in academic, corporate, and media environments by making spoken information easily searchable and useful.

---

## 🚀 Features

* **Real-Time Transcription** – Convert spoken content into accurate text using AI models
* **Keyword Extraction** – Identify relevant keywords contextually using NLP
* **Automatic Summarization** – Generate concise summaries with transformers (e.g., BART)
* **Web Interface** – Access via a browser using Django
* **Scalable Architecture** – Efficient handling of diverse audio workloads

---

## 🛠️ Tech Stack

* **Frontend**: HTML, CSS, JavaScript
* **Backend**: Python, Django
* **Speech Recognition**: SpeechRecognition
* **NLP & Summarization**: NLTK, spaCy, Transformers (BERT, BART)
* **Deep Learning**: PyTorch, TensorFlow
* **UI**: Bootstrap

---

## 📦 Installation

1. **Clone the Repository**:

   ```bash
   git clone https://github.com/Imrkraghu/SUMMARIZEIT.git
   cd SUMMARIZEIT
   ```

2. **Create a Virtual Environment**:

   ```bash
   python3 -m venv venv
   source venv/scripts/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**:

   ```bash
   sudo apt-get update
   sudo apt-get install portaudio19-dev python3-dev
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
├── main                   # main project which is going to get executed 
├── summarizeit/           # Django project settings
├── requirements.txt       # project requirements
└── README.md
```

---

## 📫 Contact

For questions or feedback, please contact [Imrkraghu](mailto:rohitgitpro@gmail.com).
