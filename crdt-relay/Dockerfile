FROM node:20-slim

WORKDIR /app

COPY package.json ./
RUN npm install --omit=dev

COPY server.js snapshot.js docs.js ./

EXPOSE 1234
EXPOSE 1235

CMD ["node", "server.js"]
