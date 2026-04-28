# syntax=docker/dockerfile:1.7
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . ./agent
EXPOSE 8080
CMD ["python", "-m", "agent.main"]
