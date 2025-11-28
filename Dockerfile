FROM python:3.11-slim

# Install Node.js
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    chromium \
    chromium-driver \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy package files
COPY package.json ./
COPY requirements.txt ./

# Install dependencies
RUN npm install
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY config/.env.example ./config/.env.example

# Create logs directory
RUN mkdir -p logs

# Set environment variables for Puppeteer
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium

# Expose port for WhatsApp service
EXPOSE 3000

# Create startup script
RUN echo '#!/bin/bash\n\
echo "Starting WhatsApp service..."\n\
node src/whatsapp_service.js &\n\
WHATSAPP_PID=$!\n\
echo "WhatsApp service started (PID: $WHATSAPP_PID)"\n\
\n\
echo "Waiting for WhatsApp service to be ready..."\n\
sleep 10\n\
\n\
echo "Starting email monitoring bot..."\n\
python src/main.py\n\
' > /app/start.sh && chmod +x /app/start.sh

CMD ["/app/start.sh"]
