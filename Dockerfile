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

# Install CPU-only torch (~800MB instead of ~2.5GB with CUDA)
RUN pip install --only-binary=:all: \
    torch --index-url https://download.pytorch.org/whl/cpu

# Install CPU-only tensorflow (~400MB instead of ~600MB)
RUN pip install --only-binary=:all: tensorflow-cpu

# Install remaining binary packages
RUN pip install --only-binary=:all: \
    numpy pandas scipy scikit-learn || true

# Install the rest
RUN pip install -r requirements.txt

# Download spaCy model at build time
RUN python -m spacy download en_core_web_sm

# Download NLTK data at build time
RUN python -c "import nltk; nltk.download('stopwords'); nltk.download('punkt'); nltk.download('punkt_tab')"

# ---- Final stage ----
FROM deps AS final

WORKDIR /app
COPY . /app
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000
CMD ["/entrypoint.sh"]
