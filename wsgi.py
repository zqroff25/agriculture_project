from waitress import serve
from app import app
from config import (
    WAITRESS_THREADS,
    WAITRESS_CHANNEL_TIMEOUT,
    WAITRESS_CONNECTION_LIMIT
)

if __name__ == '__main__':
    # Waitress ile uygulamayı başlat
    serve(
        app,
        host='0.0.0.0',
        port=8501,
        threads=WAITRESS_THREADS,
        url_scheme='http',
        channel_timeout=WAITRESS_CHANNEL_TIMEOUT,
        connection_limit=WAITRESS_CONNECTION_LIMIT,
        cleanup_interval=30,  # Önbellek temizleme aralığı
        max_request_header_size=262144,  # 256KB
        max_request_body_size=1073741824  # 1GB
    ) 