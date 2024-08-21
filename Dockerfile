# Start from the official Python base image.
FROM python:3.12-slim-bookworm

# Set the current working directory to /code
WORKDIR /code

# Copy the file with the requirements to the /code directory.
COPY ./requirements.txt /code/requirements.txt

# Install the package dependencies in the requirements file.
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Copy the ./ directory inside the /code directory.
COPY ./ /code/app

# Run the command to start the FastAPI server.
CMD ["fastapi", "run", "main.py", "--reload", "--host", "0.0.0.0", "--port", "8000"]