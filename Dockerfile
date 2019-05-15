FROM python:3.7
ADD . /code
WORKDIR /code
RUN echo "Updating apt"
RUN apt-get update
RUN echo "Installing python libraries"
RUN pip install --no-cache-dir -r requirements.txt
