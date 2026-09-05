FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including Tesseract OCR for document processing
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements from root directory and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project repository into the container workspace
COPY . .

EXPOSE 8000

# Run Uvicorn using the standard backend package path
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]