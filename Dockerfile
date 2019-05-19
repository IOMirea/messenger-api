FROM python:3.7

ADD . /code
WORKDIR /code

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080
CMD ["./run.sh"]
