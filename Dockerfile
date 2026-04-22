FROM python:3.11-slim

WORKDIR /opt/satosa

RUN apt-get update && apt-get install -y xmlsec1 && \
    python3 -m pip install --no-cache-dir --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple && \
    python3 -m pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple \
    satosa gunicorn pysaml2 pyop