import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timedelta
import os

TMO_CACHE_FILE = 'data/tmo_prices.json'
CACHE_DURATION_DAYS = 1  # 1 gün önbellek süresi

def scrape_tmo_prices():
    """TMO fiyat listesini çeker ve JSON dosyasına kaydeder."""
    try:
        # TMO'nun günlük fiyat listesi sayfası
        response = requests.get('https://www.tmo.gov.tr/tr/fiyat-listesi', timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Örnek veri yapısı (gerçek uygulamada API'den gelen veriye göre düzenlenecek)
        commodity_data = {
            'bugday': {
                'ekmeklik': {
                    'price': 8500,
                    'change': 1.2,
                    'unit': 'TL/Ton',
                    'date': datetime.now().strftime('%d.%m.%Y')
                },
                'makarnalik': {
                    'price': 8200,
                    'change': 0.8,
                    'unit': 'TL/Ton',
                    'date': datetime.now().strftime('%d.%m.%Y')
                }
            },
            'arpa': {
                'yemlik': {
                    'price': 7200,
                    'change': -0.5,
                    'unit': 'TL/Ton',
                    'date': datetime.now().strftime('%d.%m.%Y')
                },
                'maltlik': {
                    'price': 7500,
                    'change': 0.3,
                    'unit': 'TL/Ton',
                    'date': datetime.now().strftime('%d.%m.%Y')
                }
            },
            'misir': {
                'yemlik': {
                    'price': 6100,
                    'change': 1.5,
                    'unit': 'TL/Ton',
                    'date': datetime.now().strftime('%d.%m.%Y')
                }
            },
            'pancar': {
                'seker': {
                    'price': 1200,
                    'change': 0.0,
                    'unit': 'TL/Ton',
                    'date': datetime.now().strftime('%d.%m.%Y')
                }
            },
            'aycicegi': {
                'yaglik': {
                    'price': 15000,
                    'change': 2.1,
                    'unit': 'TL/Ton',
                    'date': datetime.now().strftime('%d.%m.%Y')
                }
            },
            'nohut': {
                'kirmizi': {
                    'price': 25000,
                    'change': 1.8,
                    'unit': 'TL/Ton',
                    'date': datetime.now().strftime('%d.%m.%Y')
                },
                'sari': {
                    'price': 24500,
                    'change': 1.5,
                    'unit': 'TL/Ton',
                    'date': datetime.now().strftime('%d.%m.%Y')
                },
                'beyaz': {
                    'price': 26000,
                    'change': 2.0,
                    'unit': 'TL/Ton',
                    'date': datetime.now().strftime('%d.%m.%Y')
                }
            }
        }
        
        # Veriyi JSON dosyasına kaydet
        os.makedirs('data', exist_ok=True)
        with open(TMO_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                'data': commodity_data,
                'timestamp': datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=4)
            
        return commodity_data
        
    except Exception as e:
        print(f"TMO verileri alınamadı: {e}")
        return None

def get_tmo_prices():
    """TMO fiyat verilerini önbellekten veya scraping ile alır."""
    # Önbellek dosyası var mı kontrol et
    if os.path.exists(TMO_CACHE_FILE):
        try:
            with open(TMO_CACHE_FILE, 'r', encoding='utf-8') as f:
                cache_content = json.load(f)
                cache_data = cache_content.get('data')
                timestamp_str = cache_content.get('timestamp')
                
                if timestamp_str:
                    cache_timestamp = datetime.fromisoformat(timestamp_str)
                    # Önbellek süresi dolmuş mu kontrol et
                    if datetime.now() - cache_timestamp < timedelta(days=CACHE_DURATION_DAYS):
                        return cache_data
        except Exception as e:
            print(f"TMO önbellek dosyası okunamadı: {e}")
    
    # Önbellek yok veya süresi dolmuşsa yeni veri çek
    return scrape_tmo_prices()

if __name__ == '__main__':
    # Test için scraper'ı çalıştır
    prices = get_tmo_prices()
    print("TMO fiyatları güncellendi:", prices is not None) 