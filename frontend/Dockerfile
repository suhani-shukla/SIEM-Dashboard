# FILE LOCATION: frontend/Dockerfile
#
# Multi-stage build with two usable targets:
#   dev  -> vite dev server with hot reload (what docker-compose.yml uses locally)
#   prod -> static build served by nginx (what a real deployment should use)
#
# Build the dev image (default, matches previous phases):
#   docker build --target dev -t siem-frontend:dev .
#
# Build the prod image:
#   docker build --target prod -t siem-frontend:prod .

FROM node:20-alpine AS base
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install

# ---- dev target ----
FROM base AS dev
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev"]

# ---- build stage for prod ----
FROM base AS build
COPY . .
RUN npm run build

# ---- prod target: nginx serving the static build ----
FROM nginx:1.27-alpine AS prod
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
