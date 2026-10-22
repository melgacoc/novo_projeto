FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json .npmrc ./
RUN npm ci
COPY . .
ARG VITE_API_URL=http://localhost:8000/api/v1
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json .npmrc ./
RUN npm ci --omit=dev

FROM node:20-alpine
WORKDIR /app
ENV NODE_ENV=production PORT=3000
COPY package.json ./
COPY --from=deps /app/node_modules ./node_modules
COPY --from=build /app/build ./build
USER node
EXPOSE 3000
CMD ["npm", "run", "start"]
