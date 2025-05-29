import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timedelta
import os

NEWS_CACHE_FILE = 'data/news_cache.json'
NEWS_CACHE_DURATION_DAYS = 7  # 1 hafta önbellek süresi

def scrape_news():
    """Tarım ve Orman Bakanlığı haber arşivinden haberleri çeker ve JSON dosyasına kaydeder."""
    news_list = []
    url = 'https://www.tarimorman.gov.tr/HaberArsivi'

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        # Haber öğelerini bulma ve parse etme
        iletisim_baslik = soup.find('h4', string='\xa0 İLETİŞİM')

        if iletisim_baslik:
            haber_basliklari = iletisim_baslik.find_all_previous('h4')
            haber_basliklari.reverse()
        else:
            haber_basliklari = soup.find_all('h4')

        for baslik_elementi in haber_basliklari:
            try:
                title = baslik_elementi.get_text(strip=True)
                if title == 'Haber Arşivi':
                    continue

                link_elementi = baslik_elementi.find_next_sibling('a')
                link = link_elementi['href'] if link_elementi and link_elementi.has_attr('href') else '#'

                ozet_elementi = None
                current_element = baslik_elementi.next_sibling
                while current_element:
                    if current_element.name == 'p':
                        ozet_elementi = current_element
                        break
                    current_element = current_element.next_sibling

                summary = ozet_elementi.get_text(strip=True)[:200] + '...' if ozet_elementi else 'Özet bulunamadı.'
                image = ''  # Görsel yok

                news_list.append({
                    'title': title,
                    'summary': summary,
                    'link': link,
                    'image': image
                })
            except Exception as e:
                print(f"Haber öğesi parse edilirken hata oluştu: {e}")
                continue

        # Veriyi JSON dosyasına kaydet
        os.makedirs('data', exist_ok=True)
        with open(NEWS_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                'news': news_list,
                'timestamp': datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=4)

        return news_list

    except Exception as e:
        print(f"Haber verileri alınamadı: {e}")
        return None

def get_news():
    """Haber verilerini önbellekten veya scraping ile alır."""
    cache_data = None  # cache_data'yı başlangıçta None olarak tanımla
    
    # Önbellek dosyası var mı kontrol et
    if os.path.exists(NEWS_CACHE_FILE):
        try:
            with open(NEWS_CACHE_FILE, 'r', encoding='utf-8') as f:
                cache_content = json.load(f)
                cache_data = cache_content.get('news', [])
                timestamp_str = cache_content.get('timestamp')
                
                if timestamp_str:
                    cache_timestamp = datetime.fromisoformat(timestamp_str)
                    # Önbellek süresi dolmuş mu kontrol et
                    if datetime.now() - cache_timestamp < timedelta(days=NEWS_CACHE_DURATION_DAYS):
                        return cache_data
        except Exception as e:
            print(f"Haber önbellek dosyası okunamadı: {e}")
            cache_data = None  # Hata durumunda cache_data'yı None yap
    
    # Önbellek yok veya süresi dolmuşsa yeni veri çek
    # Sadece Pazartesi günleri scraping yap
    if datetime.now().weekday() == 0:  # Pazartesi = 0
        return scrape_news()
    elif cache_data is not None:  # Pazartesi değilse ve eski veri varsa onu kullan
        return cache_data
    return []  # Hiç veri yoksa boş liste döndür

if __name__ == '__main__':
    # Test için scraper'ı çalıştır
    news = get_news()
    print(f"{len(news)} adet haber güncellendi.") 