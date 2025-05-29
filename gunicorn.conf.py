from config import GUNICORN_TIMEOUT, GUNICORN_WORKERS, GUNICORN_THREADS

# Worker sayısı
workers = GUNICORN_WORKERS

# Her worker için thread sayısı
threads = GUNICORN_THREADS

# Worker timeout süresi (saniye)
timeout = GUNICORN_TIMEOUT

# Worker'ların yeniden başlatılması
max_requests = 1000
max_requests_jitter = 50

# Worker'ların yeniden başlatılma süresi
graceful_timeout = 30

# Hata ayıklama
capture_output = True
enable_stdio_inheritance = True

# Loglama
accesslog = '-'
errorlog = '-'
loglevel = 'info' 