# Set up
FROM python:3
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED 1
RUN mkdir /code
WORKDIR /code

# Define virtual environment
ENV VIRTUAL_ENV=.venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install system dependencies and install vocabulary-trainer package
RUN pip install -U pip setuptools
RUN pip install wheel
RUN apt-get update && apt-get install -y ffmpeg gettext
COPY . /code/
RUN python3 setup.py build

# Defining entrypoint. Adding src/vocabulary-trainer fails in during build, so it needs to be called manually
CMD sh dev-tools/init.sh && src/vocabulary-trainer runserver 0.0.0.0:8000
