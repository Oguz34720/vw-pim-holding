FROM python:3.10-slim

WORKDIR /app

# System dependencies for common Python packages
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       git \
       gcc \
       libglib2.0-0 \
       libsm6 \
       libxext6 \
       libxrender1 \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency manifest and install packages
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# Copy app sources
COPY . .

# Expose port used by Cloud Run
EXPOSE 8080

CMD ["streamlit", "run", "app.py", "--server.port", "8080", "--server.address", "0.0.0.0"]
