FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y gcc python3-dev libxml2-dev libxslt1-dev && \
    apt-get clean

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 5000
CMD ["python", "app.py"] 