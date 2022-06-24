FROM python:slim-buster

WORKDIR /app
COPY main.py main.py
RUN pip install requests

CMD ["python3", "main.py"]
