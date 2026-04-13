FROM python:3.12-slim AS deps

RUN apt-get update && apt-get install -y \
    portaudio19-dev \
    python3-dev \
    build-essential \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --upgrade pip wheel

# Install heavy binary-only packages first (no compilation, pulls pre-built wheels)
RUN pip install --only-binary=:all: torch tensorflow

# Install common scientific packages as binaries
RUN pip install --only-binary=:all: \
    numpy pandas scipy scikit-learn \
    || true

# Install everything else from requirements.txt
RUN pip install -r requirements.txt

# Download spaCy model at build time (avoids runtime delay)
RUN python -m spacy download en_core_web_sm

# Download NLTK data at build time (avoids runtime delay)
RUN python -c "import nltk; nltk.download('stopwords'); nltk.download('punkt'); nltk.download('punkt_tab')"

# ---- Final stage ----
FROM deps AS final

WORKDIR /app
COPY . /app
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000
CMD ["/entrypoint.sh"]
