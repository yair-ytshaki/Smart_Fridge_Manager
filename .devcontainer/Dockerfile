# Use a slim version of Python for a smaller image size
FROM python:3.10-slim

# Install system dependencies (needed for some scrapers/OpenCV later)
RUN apt-get update && apt-get install -y \
    build-essential \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container
WORKDIR /workspaces/Smart_Fridge_Manager

# Copy only the requirements first to leverage Docker caching
COPY requirements.txt .

# Only run pip if the file actually exists
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

# Keep the container running
CMD ["sleep", "infinity"]

# # Tell Docker how to run your app
# CMD ["python", "main_app.py"]