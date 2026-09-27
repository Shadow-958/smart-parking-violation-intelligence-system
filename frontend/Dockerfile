FROM node:20-alpine

WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev"]

# NOTE: this is a development-mode Dockerfile (Vite dev server with HMR).
# A production multi-stage build (vite build -> nginx) will be added in
# the Deployment module.
