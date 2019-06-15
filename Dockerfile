FROM python:3.7-alpine

ARG UID=1000
ARG GID=1000

WORKDIR /code

RUN apk add --no-cache \
	gcc \
	make \
	libffi-dev \
	musl-dev

# avoid cache invalidation after copying entire directory
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

RUN apk del \
	gcc \
	make \
	libffi-dev \
	musl-dev

COPY . .
COPY config /config

EXPOSE 8080

RUN addgroup -g $GID -S iomirea && \
    adduser -u $UID -S api -G iomirea
RUN chown -R api:iomirea /code
RUN chown -R api:iomirea /config
USER api

CMD ["python", "iomirea/app.py"]
