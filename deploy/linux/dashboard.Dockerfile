FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 PYTHONPATH=/opt/tradingbot
RUN pip install --no-cache-dir pandas numpy python-dotenv pyyaml requests streamlit streamlit-autorefresh matplotlib
WORKDIR /opt/tradingbot
