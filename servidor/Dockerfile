# El contexto de build es la raíz del repo (ver docker-compose.yml y .dockerignore)
FROM python:3.12-slim
WORKDIR /app
COPY servidor/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY servidor/*.py ./
ENV PYTHONUNBUFFERED=1
EXPOSE 7777 8000
CMD ["python", "server.py"]
