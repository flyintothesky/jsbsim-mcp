FROM python:3.12-slim

# Hugging Face Spaces expects port 7860 by default and runs the CMD below.
# Space will mount this Dockerfile as the build context.

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /code

# System deps needed by the wheel and for any JSBSim C-extension rebuild
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libxml2-utils \
        libexpat1 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first (image layer cache)
COPY requirements.txt /code/requirements.txt
RUN pip install -r /code/requirements.txt

# Copy application source
COPY app.py /code/app.py
COPY src /code/src
COPY run_stdio.py /code/run_stdio.py
COPY jsbsim_data /code/jsbsim_data

# Default port HF Spaces expects
EXPOSE 7860
ENV JBSIM_ROOT=/code/jsbsim_data

# uvicorn log level INFO; HF auto-restarts on crash
CMD ["uvicorn", "app:parent", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]
