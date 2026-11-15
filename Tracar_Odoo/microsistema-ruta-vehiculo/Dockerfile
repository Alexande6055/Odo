FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install --omit=dev

COPY --from=builder /app/dist ./dist
COPY server.js ./

EXPOSE 3000

ENV PORT=3000
ENV TRACCAR_URL=http://traccar:8082

CMD ["node", "server.js"]
