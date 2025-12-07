FROM node:18-alpine

WORKDIR /app

# Install dependencies based on package.json
# We copy package.json first for caching
COPY package.json package-lock.json* ./
RUN npm install

# Copy source code (though volume mount overrides this in dev, it's good for build)
COPY . .

# Next.js collects telemetry, disable it
ENV NEXT_TELEMETRY_DISABLED 1

CMD ["npm", "run", "dev"]
