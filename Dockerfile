# Use a small official Python image.
FROM python:3.14-slim

# Everything CanvasSync needs will live here inside the container.
WORKDIR /app

# Copy the project into the container.
COPY . .

# Install CanvasSync and all dependencies from pyproject.toml.
RUN pip install --no-cache-dir .

# Run one CanvasSync job and then exit.
#
# Cloud Scheduler will eventually start this container once per hour.
CMD ["canvassync"]