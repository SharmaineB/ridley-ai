FROM node:20-alpine AS build
WORKDIR /web
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
ARG API_URL=http://backend:8000
ENV API_URL=$API_URL
RUN npm run build

FROM node:20-alpine
WORKDIR /web
ENV NODE_ENV=production
COPY --from=build /web ./
EXPOSE 3000
CMD ["npm", "run", "start"]
