# --- Build stage ---
FROM node:20-alpine AS build

WORKDIR /app
COPY package.json /app/package.json

# Copy lockfile if present (improves reproducibility)
# If using npm:
# COPY package-lock.json /app/package-lock.json
# If using pnpm/yarn, add the corresponding lockfile above.

RUN npm ci

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

