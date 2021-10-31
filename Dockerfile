FROM python:3.9-slim-buster

COPY requirements.txt /app/

RUN apt-get update && apt-get install -y libcairo2-dev
RUN pip3 install --no-cache-dir -r /app/requirements.txt

COPY ./ /app/web
WORKDIR /app/web

CMD gunicorn -b :80 crabber:app
