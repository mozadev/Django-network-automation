FROM python:3.12.9-slim 

ENV DEBIAN_FRONTEND=noninteractive

RUN apt update && apt install -y tzdata && \
    ln -sf /usr/share/zoneinfo/America/Lima /etc/localtime && \
    echo "America/Lima" > /etc/timezone && \
    apt clean
    
WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
