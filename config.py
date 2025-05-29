import os
from datetime import timedelta

# API Anahtarları
OPENWEATHER_API_KEY = 'a6d5a4f3356cd42bd0014cb967b5f0e5'
EXCHANGE_RATE_API_URL = 'https://open.er-api.com/v6/latest/USD'
EUR_EXCHANGE_RATE_API_URL = 'https://open.er-api.com/v6/latest/EUR'

# Scraper URL'leri
TMO_URL = 'https://www.tmo.gov.tr/tr/fiyat-listesi'
NEWS_URL = 'https://www.tarimorman.gov.tr/HaberArsivi'

# Timeout Süreleri (saniye)
API_TIMEOUT = 5
SCRAPER_TIMEOUT = 8

# Önbellek Süreleri
TMO_CACHE_DURATION = timedelta(hours=12)
NEWS_CACHE_DURATION = timedelta(days=3)
CURRENCY_CACHE_DURATION = timedelta(minutes=15)

# Waitress Ayarları
WAITRESS_THREADS = 8
WAITRESS_CHANNEL_TIMEOUT = 30
WAITRESS_CONNECTION_LIMIT = 1000

# Gunicorn Ayarları
GUNICORN_TIMEOUT = 120  # 2 dakika
GUNICORN_WORKERS = 2
GUNICORN_THREADS = 4 