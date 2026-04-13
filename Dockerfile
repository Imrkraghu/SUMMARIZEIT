FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    portaudio19-dev \
    python3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . /app

RUN python -m pip install --upgrade pip
RUN pip install -r requirements.txt

EXPOSE 8000

# Run collectstatic at runtime, not build
CMD ["sh", "-c", "python manage.py collectstatic --noinput && gunicorn summarizeit.wsgi:application --bind 0.0.0.0:$PORT"]
