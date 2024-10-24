# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the current directory contents into the container
COPY . .

# Install any needed packages
RUN pip install --no-cache-dir -r requirements.txt

# Expose port for health checks
EXPOSE 8000

# Define environment variable
ENV NAME AutoFilterBot

# Run bot.py when the container launches
CMD ["python", "bot.py"]
