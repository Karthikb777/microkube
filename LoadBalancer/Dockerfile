FROM python:alpine3.7
COPY . /app
WORKDIR /app
RUN pip install Flask
RUN pip install requests
ENTRYPOINT ["python"]
CMD ["load_balancer.py", "--host", "0.0.0.0"]