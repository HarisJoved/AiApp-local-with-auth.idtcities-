# Development stage
FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Expose port 3333
EXPOSE 3333

# Start development server
CMD ["npm", "start"]
