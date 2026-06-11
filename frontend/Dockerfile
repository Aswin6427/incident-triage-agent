# ── Stage 1: build the Vite static bundle ───────────────────
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# ── Stage 2: serve + reverse-proxy with nginx ────────────────
FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html

# The stock nginx entrypoint runs envsubst over files in /etc/nginx/templates,
# substituting ${BACKEND_HOST} (set as a Cloud Run env var) into the config.
COPY nginx.conf.template /etc/nginx/templates/default.conf.template

EXPOSE 8080
