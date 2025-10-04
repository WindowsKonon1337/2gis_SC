FROM python:3.11-alpine

WORKDIR /service

COPY . /service/

RUN cd /service && pip install -r requirements.txt

ENTRYPOINT [ "python", "service.py" ]