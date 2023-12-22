FROM python:3.11-alpine

# Copy the files.
WORKDIR /app
COPY . /app

# Install the dependencies.
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH "${PYTHONPATH}:/app"
RUN python3 -m pip install -r /app/requirements.txt

# Prepare the app.
EXPOSE 45982
ENTRYPOINT ["python3", "./Application.py"]