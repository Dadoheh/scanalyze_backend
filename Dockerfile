FROM python:3.11

WORKDIR /app

RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    libleptonica-dev \
    tesseract-ocr-eng \
    tesseract-ocr-pol \
    libgl1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*


ENV PIP_DEFAULT_TIMEOUT=600
ENV PIP_NO_CACHE_DIR=1

COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata
RUN mkdir -p /app/uploads && chmod 777 /app/uploads

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
