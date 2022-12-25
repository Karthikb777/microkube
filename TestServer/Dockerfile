FROM python:alpine3.7
COPY . /app
WORKDIR /app
RUN pip install Flask
ENTRYPOINT ["python"]
CMD ["app.py", "--host", "0.0.0.0"]