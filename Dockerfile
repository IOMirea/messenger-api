FROM python:3.7-alpine

WORKDIR /code

RUN apk add --no-cache \
	g++ \
	make \
	libffi-dev

# avoid cache invalidation after copying entire directory
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

RUN apk del g++ make libffi-dev

COPY . .
COPY config /config

EXPOSE 8080

RUN adduser -S iomirea
RUN chown -R iomirea /code
RUN chown -R iomirea /config
USER iomirea

CMD ["python", "iomirea/app.py"]
