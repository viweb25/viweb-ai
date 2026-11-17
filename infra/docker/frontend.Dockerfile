FROM node:22-alpine
WORKDIR /workspace
COPY package.json package-lock.json ./
COPY frontend/package.json frontend/package.json
RUN npm ci
COPY frontend frontend
EXPOSE 3000
CMD ["npm", "run", "dev", "--workspace", "@vi/web", "--", "--host", "0.0.0.0"]
