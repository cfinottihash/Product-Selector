FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["streamlit", "run", "app/product_selector_app.py",
     "--server.address", "0.0.0.0", "--server.port", "8000"]