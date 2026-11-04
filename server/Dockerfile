FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Bo ky tu CR (byte 13) neu entrypoint.sh bi doi sang CRLF tren Windows - thieu buoc nay
# container bao "exec ./entrypoint.sh: no such file or directory" va server khong chay.
RUN python -c "import pathlib; p = pathlib.Path('entrypoint.sh'); p.write_bytes(p.read_bytes().replace(bytes([13]), b''))" \
    && chmod +x entrypoint.sh

EXPOSE 8000
# Tien trinh con tra loi (GET / khong can DB) - compose cho client doi server san sang.
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=12 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/', timeout=4).status == 200 else 1)"
ENTRYPOINT ["./entrypoint.sh"]
