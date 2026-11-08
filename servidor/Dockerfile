# El contexto de build es la raíz del repo (ver docker-compose.yml y .dockerignore).

# Etapa 1: compila el panel web. Solo se usa para producir panel/dist: la imagen
# final no lleva Node, así queda más liviana.
FROM node:20-alpine AS panel
WORKDIR /panel
COPY panel/package.json panel/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY panel/ ./
RUN npm run build

# Etapa 2: el servidor del juego + la API, con el panel ya compilado
FROM python:3.12-slim
WORKDIR /app
COPY servidor/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY servidor/*.py ./
COPY --from=panel /panel/dist ./panel_dist
ENV PYTHONUNBUFFERED=1
EXPOSE 7777 8000
CMD ["python", "server.py"]
