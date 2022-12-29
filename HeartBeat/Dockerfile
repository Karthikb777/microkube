FROM python:alpine3.7
COPY . /app
WORKDIR /app
RUN pip install requests
RUN pip install redis
ENTRYPOINT ["python"]
CMD ["heartbeat.py", "--host", "0.0.0.0"]