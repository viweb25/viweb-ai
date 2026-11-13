FROM python:3.11-slim
RUN pip install --no-cache-dir mlflow==2.22.0
# MLflow 2.x imports a pool class removed by SQLAlchemy 2.1.
RUN pip install --no-cache-dir sqlalchemy==2.0.57
RUN mkdir -p /mlflow && useradd --uid 10001 --no-create-home mlflow && chown mlflow:mlflow /mlflow
USER mlflow
WORKDIR /mlflow
