FROM python:3.7-alpine

ARG UID=1500
ARG GID=1500

ARG PORT=8080
# workaround for CMD not being able to parse variable at build time
ENV PORT ${PORT}

# enables propper stdout flushing
ENV PYTHONUNBUFFERED 1

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

EXPOSE ${PORT}

RUN addgroup -g $GID -S iomirea && \
    adduser -u $UID -S api -G iomirea
RUN chown -R api:iomirea /code
RUN chown -R api:iomirea /config
USER api

CMD python iomirea/app.py --port=$PORT --host=0.0.0.0
