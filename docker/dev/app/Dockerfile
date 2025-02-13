FROM node:20-slim

WORKDIR /app

# Copy package files
COPY package.json ./

# Install dependencies with legacy peer deps
RUN npm install --legacy-peer-deps --force

# Copy the rest of the application code
COPY . .

# Build the application
RUN npm run build

# Expose port
EXPOSE 3000

# Start the application in development mode with explicit host binding
ENV HOSTNAME="0.0.0.0"
ENV PORT=3000
CMD ["npm", "run", "dev"] 