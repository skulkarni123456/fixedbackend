FROM python:3.11-slim

# Install system deps: libreoffice, qpdf, ghostscript, poppler-utils
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice \
    qpdf \
    ghostscript \
    poppler-utils \
    build-essential \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . /app

# create uploads dir
RUN mkdir -p /app/uploads

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]