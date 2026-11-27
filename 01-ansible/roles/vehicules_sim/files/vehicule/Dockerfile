FROM python:3.12-slim
WORKDIR /opt
COPY agent.py /opt/agent.py
COPY navlib_base/navlib /opt/navlib/navlib
RUN echo "1.4.2" > /opt/navlib/VERSION
ENV PYTHONUNBUFFERED=1
CMD ["python3", "/opt/agent.py"]
