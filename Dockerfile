FROM python:3.7-alpine

ADD . /code
WORKDIR /code

RUN apk add --no-cache \
	build-base \
	libffi-dev

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080
CMD ["python3.7", "iomirea/app.py"]
