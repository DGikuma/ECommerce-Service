FROM python:3.11

# Set working directory inside the container
WORKDIR /app

# Install dependencies first (faster rebuilds)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project
COPY . .

# Ensure Python can find your project
ENV PYTHONPATH=/app

# Run gunicorn properly
CMD ["gunicorn", "ecommerce.wsgi:application", "--bind", "0.0.0.0:8000"]
