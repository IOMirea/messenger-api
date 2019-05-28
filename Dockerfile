FROM python:3.7-alpine

WORKDIR /code

RUN apk add --no-cache \
	build-base \
	libffi-dev

COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt
RUN rm /requirements.txt

EXPOSE 8080
CMD ["python3.7", "iomirea/app.py"]
