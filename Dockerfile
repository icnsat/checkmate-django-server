# Images
FROM python:3-alpine

# Setup
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
COPY . /app/

# Prepare Django
RUN pip install --no-cache-dir -r requirements.txt
RUN python manage.py collectstatic --noinput

# Expose the port the app runs on
EXPOSE 8000

# Run the application
CMD ["gunicorn", "checkmate.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]