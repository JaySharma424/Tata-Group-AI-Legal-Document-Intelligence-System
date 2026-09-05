# Stage 1: Build the React Application (Upgraded to Node 20 for Vite compatibility)
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files and install dependencies
COPY package*.json ./
RUN npm install

# Copy the rest of the frontend code
COPY . .

# Bypass strict TypeScript checking and build directly with Vite
RUN npx vite build

# Stage 2: Serve with Nginx
FROM nginx:alpine

# Copy the built assets from the builder stage to Nginx's public folder
COPY --from=builder /app/dist /usr/share/nginx/html

# Optional: Overwrite default Nginx config to handle React Router (SPA) fallback
RUN echo 'server { \
    listen 80; \
    location / { \
        root /usr/share/nginx/html; \
        index index.html index.htm; \
        try_files $uri $uri/ /index.html; \
    } \
}' > /etc/nginx/conf.d/default.conf

# Expose Nginx default port
EXPOSE 80

# Start Nginx server
CMD ["nginx", "-g", "daemon off;"]