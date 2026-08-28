FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive

# Install system libraries needed for OpenCV and runtime support
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libopenblas0 \
    liblapack3 \
    libx11-6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Upgrade pip and install dlib via pre-compiled binary wheel to bypass C++ compilation
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir https://github.com/z-a-f/dlib-wheels/releases/download/v19.22/dlib-19.22.99-cp310-cp310-linux_x86_64.whl

COPY requirements.txt .

# Install the rest of your python requirements (face_recognition, flask, gunicorn, etc.)
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 10000

CMD ["gunicorn", "--bind", "0.0.0.0:10000", "app:app"]
