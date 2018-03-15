FROM python:3.6

RUN mkdir /app

WORKDIR /app

COPY requirements.txt /app

RUN pip install -r requirements.txt

COPY rsi.py /app
COPY index.py /app

CMD python index.py
