# Set up
FROM python:3.7
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED 1
RUN mkdir /code
WORKDIR /code

# Install system dependencies and install lunes-cms package
COPY . /code/
RUN pip install --upgrade pip && pip install .
RUN apt-get update && apt-get install -y ffmpeg gettext

# Defining entrypoint
CMD sh dev-tools/init.sh && lunes-cms-cli runserver 0.0.0.0:8000
