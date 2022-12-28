FROM python:alpine3.7
COPY . /app
WORKDIR /app
RUN pip install Flask
RUN pip install requests
RUN pip install redis
RUN pip install docker
ENTRYPOINT ["python"]
CMD ["auto_scaler.py", "--host", "0.0.0.0"]