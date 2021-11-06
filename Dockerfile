# Set up
FROM python:3.7
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED 1
RUN mkdir /code
WORKDIR /code

# Install system dependencies and install vocabulary-trainer package
COPY . /code/
RUN pip install --upgrade pip && pip install .
RUN apt-get update && apt-get install -y ffmpeg gettext

# Defining entrypoint
CMD sh dev-tools/init.sh && vocabulary-trainer runserver 0.0.0.0:8000
