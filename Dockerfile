FROM python:3.7
ADD . /code
WORKDIR /code
RUN echo "Updating apt"
RUN apt-get update
RUN echo "Installing python libraries"
RUN pip install --no-cache -r requirements.txt
RUN echo "Creating default config file"
COPY config.yaml.example config.yaml
