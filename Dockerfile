FROM python:3.10-slim

RUN apt-get update -y
RUN apt-get install -y python3-dev libpq-dev build-essential

COPY requirements.txt /opt/project/requirements.txt

RUN pip install -r /opt/project/requirements.txt

WORKDIR /opt/project
ENV PYTHONPATH="$PYTHONPATH":/opt/project
