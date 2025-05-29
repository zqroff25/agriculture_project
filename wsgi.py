from waitress import serve
from app import app
from config import GUNICORN_WORKERS, GUNICORN_THREADS

if __name__ == '__main__':
    # Waitress ile uygulamayı başlat
    # Windows'ta worker sayısı yerine thread sayısını kullanıyoruz
    serve(
        app,
        host='0.0.0.0',
        port=8501,
        threads=GUNICORN_WORKERS * GUNICORN_THREADS,  # Toplam thread sayısı
        url_scheme='http',
        channel_timeout=120  # 2 dakika timeout
    ) 