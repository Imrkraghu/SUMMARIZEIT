# Use official Python image
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    portaudio19-dev \
    python3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy project files
COPY . /app

# Upgrade pip and install Python dependencies
RUN python -m pip install --upgrade pip
RUN pip install -r requirements.txt

# Collect static files (optional for Django)
RUN python manage.py collectstatic --noinput

# Expose Railway port
EXPOSE 8000

# Start Django with Gunicorn
CMD ["gunicorn", "summarizeit.wsgi:application", "--bind", "0.0.0.0:$PORT"]
