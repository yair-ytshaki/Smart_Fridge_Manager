# Use a slim version of Python for a smaller image size
FROM python:3.10-slim

# Install system dependencies (needed for some scrapers/OpenCV later)
# Add wget to the installation list
RUN apt-get update && apt-get install -y \
    build-essential \
    libsqlite3-dev \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container
WORKDIR /workspaces/Smart_Fridge_Manager

# Use a wildcard to prevent the "not found" crash if the file is missing
COPY requirements.txt* ./

# Install requirements if the file exists
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

# Keep the container running
CMD ["sleep", "infinity"]

# # Tell Docker how to run your app
# CMD ["python", "main_app.py"]