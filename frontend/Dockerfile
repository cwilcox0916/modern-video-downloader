# --- Build stage ---
FROM node:20-alpine AS build

WORKDIR /app
COPY package*.json /app/

# Use npm ci when a lockfile exists, otherwise fall back to npm install
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

COPY . /app

# Allow overriding API base at build time
ARG VITE_API_URL=/
ENV VITE_API_URL=${VITE_API_URL}

RUN npm run build

# --- Runtime stage ---
FROM nginx:alpine

# Minimal hardened config (optional). Default nginx works too.
# Using default, just copy static files.
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

