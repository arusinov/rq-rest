FROM python:3.6-slim

ARG RQ_REST_VERSION='latest'

COPY dist/rq_rest-${RQ_REST_VERSION}.tar.gz /tmp/
RUN pip3 install /tmp/rq_rest-${RQ_REST_VERSION}.tar.gz

EXPOSE 8000

CMD ["rq-rest", "rest"]

