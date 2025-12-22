FROM python:3.12-slim

WORKDIR /app



COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Command is overridden by docker-compose for dev, but this is good for prod
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
