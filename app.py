from flask import Flask, request, jsonify, render_template, abort
import requests
import json
import os
from functools import lru_cache
from typing import Dict, List, Any
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

app = Flask(__name__, static_folder='static')

# Önbellek için global değişkenler
_bitki_verileri_cache = None
_bitki_arama_indeksi = None

# Para birimi verileri için önbellek
_currency_cache = None
_currency_cache_time = None
CACHE_DURATION = timedelta(minutes=5)  # 5 dakika önbellek süresi

# Tarım borsası verileri için önbellek
_commodity_cache = None
_commodity_cache_time = None
COMMODITY_CACHE_DURATION = timedelta(days=3)  # 3 gün önbellek süresi

# Haber verileri için önbellek (Artık kalıcı depolama için kullanılacak)
_news_cache_file = 'news_cache.json'
NEWS_CACHE_DURATION_DAYS = 7 # Bir hafta

def turkce_karakter_duzelt(bitki_adi):
    # Türkçe karakterleri düzeltme sözlüğü
    karakter_duzeltme = {
        'ğ': 'g', 'Ğ': 'G',
        'ü': 'u', 'Ü': 'U',
        'ş': 's', 'Ş': 'S',
        'ı': 'i', 'İ': 'I',
        'ö': 'o', 'Ö': 'O',
        'ç': 'c', 'Ç': 'C'
    }
    
    # Karakterleri düzelt
    for turkce, latin in karakter_duzeltme.items():
        bitki_adi = bitki_adi.replace(turkce, latin)
    
    return bitki_adi.lower()

# Bitki ve hastalık verileri
bitkiler = {
    'buğday': {
        'isim': 'Buğday',
        'gorsel': 'https://readdy.ai/api/search-image?query=icon%2C%203D%20vector%20illustration%2C%20wheat%20plant%20with%20golden%20grains%2C%20detailed%20stalks%2C%20agricultural%20crop%2C%20the%20icon%20should%20take%20up%2070%25%20of%20the%20frame%2C%20isolated%20on%20white%20background%2C%20centered%20composition%2C%20soft%20lighting%2C%20no%20shadows%2C%20clean%20and%20modern%20look%2C%20single%20object%20focus&width=200&height=200&seq=21&orientation=squarish',
        'hastaliklar': [
            {
                'isim': 'Kök Çürüklüğü',
                'aciklama': 'Toprak kökenli bir mantar hastalığıdır.',
                'gorsel': 'https://readdy.ai/api/search-image?query=wheat%20root%20rot&width=200&height=200'
            },
            {
                'isim': 'Sarı Pas',
                'aciklama': 'Yapraklarda sarımsı lekeler oluşturan bir mantar hastalığıdır.',
                'gorsel': 'https://readdy.ai/api/search-image?query=wheat%20yellow%20rust&width=200&height=200'
            }
        ]
    },
    'arpa': {
        'isim': 'Arpa',
        'gorsel': 'https://readdy.ai/api/search-image?query=icon%2C%203D%20vector%20illustration%2C%20barley%20plant%20with%20golden%20spikes%2C%20detailed%20stalks%2C%20agricultural%20crop%2C%20the%20icon%20should%20take%20up%2070%25%20of%20the%20frame%2C%20isolated%20on%20white%20background%2C%20centered%20composition%2C%20soft%20lighting%2C%20no%20shadows%2C%20clean%20and%20modern%20look%2C%20single%20object%20focus&width=200&height=200&seq=22&orientation=squarish',
        'hastaliklar': [
            {
                'isim': 'Arpa Yaprak Lekesi',
                'aciklama': 'Yapraklarda kahverengi lekeler oluşturan bir hastalıktır.',
                'gorsel': 'https://readdy.ai/api/search-image?query=barley%20leaf%20spot&width=200&height=200'
            }
        ]
    },
    # Diğer bitkiler de benzer şekilde eklenebilir
}

OPENWEATHER_API_KEY = 'a6d5a4f3356cd42bd0014cb967b5f0e5'

# Arama verileri
arama_verileri = {
    'bitkiler': [
        {
            'type': 'bitki',
            'title': 'Buğday',
            'description': 'Türkiye\'nin en önemli tarım ürünlerinden biri',
            'icon': 'ri-wheat-line',
            'link': '/bitki/bugday',
            'keywords': ['buğday', 'tahıl', 'ekmek', 'un', 'hasat', 'triticum', 'ekmeklik', 'makarnalık', 'durum', 'ekin'],
            'alt_kategoriler': ['ekmeklik', 'makarnalık', 'durum'],
            'hastaliklar': ['sarı pas', 'kök çürüklüğü', 'süne', 'külleme'],
            'bolgeler': ['iç anadolu', 'marmara', 'ege', 'güneydoğu anadolu']
        },
        {
            'type': 'bitki',
            'title': 'Arpa',
            'description': 'Hayvan yemi ve malt üretiminde kullanılan önemli bir tahıl',
            'icon': 'ri-wheat-line',
            'link': '/bitki/arpa',
            'keywords': ['arpa', 'tahıl', 'malt', 'yem', 'hordeum', 'bira', 'hayvan yemi', 'saman'],
            'alt_kategoriler': ['yemlik', 'maltlık'],
            'hastaliklar': ['arpa yaprak lekesi', 'arpa küllemesi'],
            'bolgeler': ['iç anadolu', 'marmara', 'ege']
        },
        {
            'type': 'bitki',
            'title': 'Mısır',
            'description': 'Silaj ve yem üretiminde kullanılan yüksek verimli bir bitki',
            'icon': 'ri-wheat-line',
            'link': '/bitki/misir',
            'keywords': ['mısır', 'silaj', 'yem', 'koçan', 'zea mays', 'dane', 'süt', 'hasat'],
            'alt_kategoriler': ['silage', 'dane', 'süt'],
            'hastaliklar': ['mısır kurdu', 'mısır yaprak lekesi'],
            'bolgeler': ['akdeniz', 'ege', 'marmara']
        },
        {
            'type': 'bitki',
            'title': 'Şeker Pancarı',
            'description': 'Şeker üretiminde kullanılan önemli bir endüstri bitkisi',
            'icon': 'ri-plant-line',
            'link': '/bitki/pancar',
            'keywords': ['pancar', 'şeker', 'beta vulgaris', 'endüstri bitkisi', 'şeker pancarı', 'şeker fabrikası'],
            'alt_kategoriler': ['şeker pancarı', 'yem pancarı'],
            'hastaliklar': ['pancar mildiyösü', 'pancar nematodu'],
            'bolgeler': ['iç anadolu', 'marmara', 'ege']
        },
        {
            'type': 'bitki',
            'title': 'Ayçiçeği',
            'description': 'Yağ üretiminde kullanılan önemli bir yağ bitkisi',
            'icon': 'ri-sun-flower-line',
            'link': '/bitki/aycicegi',
            'keywords': ['ayçiçeği', 'helianthus', 'yağ bitkisi', 'çekirdek', 'yağ', 'çiçek'],
            'alt_kategoriler': ['yağlık', 'çerezlik'],
            'hastaliklar': ['ayçiçeği mildiyösü', 'ayçiçeği pası'],
            'bolgeler': ['trakya', 'iç anadolu', 'marmara']
        },
        {
            'type': 'bitki',
            'title': 'Nohut',
            'description': 'Protein açısından zengin, kuraklığa dayanıklı önemli bir baklagil',
            'icon': 'ri-plant-line',
            'link': '/bitki/nohut',
            'keywords': ['nohut', 'baklagil', 'cicer', 'protein', 'kuraklık', 'mercimek', 'fasulye', 'bakla'],
            'alt_kategoriler': ['kırmızı nohut', 'sarı nohut', 'beyaz nohut'],
            'hastaliklar': ['antraknoz', 'askohitoz', 'fusarium solgunluğu', 'kök çürüklüğü'],
            'bolgeler': ['iç anadolu', 'güneydoğu anadolu', 'ege', 'akdeniz']
        }
    ],
    'hastaliklar': [
        {
            'type': 'hastalik',
            'title': 'Sarı Pas',
            'description': 'Buğdayda görülen yaygın bir mantar hastalığı',
            'icon': 'ri-virus-line',
            'link': '/hastalik/bugday/sari-pas',
            'keywords': ['sarı pas', 'buğday', 'mantar', 'hastalık', 'pas', 'puccinia', 'yaprak', 'lekeler'],
            'etkilenen_bitkiler': ['buğday', 'arpa'],
            'belirtiler': ['sarı lekeler', 'yaprak dökümü', 'verim kaybı'],
            'donem': ['ilkbahar', 'yaz']
        },
        {
            'type': 'hastalik',
            'title': 'Kök Çürüklüğü',
            'description': 'Toprak kökenli bir mantar hastalığı',
            'icon': 'ri-virus-line',
            'link': '/hastalik/bugday/kok-curuklugu',
            'keywords': ['kök çürüklüğü', 'buğday', 'mantar', 'hastalık', 'kök', 'fusarium', 'rhizoctonia'],
            'etkilenen_bitkiler': ['buğday', 'arpa', 'mısır'],
            'belirtiler': ['kök çürümesi', 'solgunluk', 'verim düşüşü'],
            'donem': ['tüm sezon']
        },
        {
            'type': 'hastalik',
            'title': 'Süne',
            'description': 'Buğdayda önemli verim kaybına neden olan bir zararlı',
            'icon': 'ri-bug-line',
            'link': '/hastalik/bugday/sune',
            'keywords': ['süne', 'buğday', 'zararlı', 'böcek', 'eurygaster', 'kımıl', 'verim kaybı'],
            'etkilenen_bitkiler': ['buğday', 'arpa'],
            'belirtiler': ['beyazlaşma', 'kavrulma', 'dane kaybı'],
            'donem': ['ilkbahar', 'yaz']
        }
    ],
    'ilaclar': [
        {
            'type': 'ilac',
            'title': 'Fungisit',
            'description': 'Mantar hastalıklarına karşı kullanılan ilaç türü',
            'icon': 'ri-medicine-bottle-line',
            'link': '/bilgi/fungisit',
            'keywords': ['fungisit', 'mantar ilacı', 'hastalık', 'ilaç', 'mantar', 'fungal', 'tedavi'],
            'kullanim_alanlari': ['buğday', 'arpa', 'mısır', 'pancar'],
            'hastaliklar': ['sarı pas', 'külleme', 'mildiyö'],
            'uygulama_zamani': ['ilkbahar', 'yaz']
        },
        {
            'type': 'ilac',
            'title': 'Herbisit',
            'description': 'Yabani otlara karşı kullanılan ilaç türü',
            'icon': 'ri-medicine-bottle-line',
            'link': '/bilgi/herbisit',
            'keywords': ['herbisit', 'yabani ot ilacı', 'ot', 'ilaç', 'yabancı ot', 'mücadele'],
            'kullanim_alanlari': ['tüm bitkiler'],
            'hedef_otlar': ['darıcan', 'köpek dişi', 'pıtrak'],
            'uygulama_zamani': ['ekim öncesi', 'çıkış sonrası']
        },
        {
            'type': 'ilac',
            'title': 'İnsektisit',
            'description': 'Zararlı böceklere karşı kullanılan ilaç türü',
            'icon': 'ri-medicine-bottle-line',
            'link': '/bilgi/insektisit',
            'keywords': ['insektisit', 'böcek ilacı', 'zararlı', 'ilaç', 'böcek', 'mücadele'],
            'kullanim_alanlari': ['buğday', 'mısır', 'pancar'],
            'hedef_zararlilar': ['süne', 'mısır kurdu', 'pancar nematodu'],
            'uygulama_zamani': ['ilkbahar', 'yaz']
        }
    ]
}

@app.route('/')
def render_index():
    # Kullanıcının IP adresini al
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    # ipapi.co ile şehir bilgisini al
    try:
        ip_info = requests.get(f'https://ipapi.co/{ip}/json/').json()
        sehir = ip_info.get('city', 'Ankara')
    except Exception:
        sehir = 'Ankara'
    # OpenWeatherMap ile hava durumu bilgisini al
    try:
        weather_url = f'https://api.openweathermap.org/data/2.5/weather?q={sehir}&appid={"a6d5a4f3356cd42bd0014cb967b5f0e5"}&units=metric&lang=tr'
        weather_data = requests.get(weather_url).json()
        sicaklik = int(weather_data['main']['temp'])
        durum = weather_data['weather'][0]['description'].capitalize()
    except Exception:
        sicaklik = 24
        durum = 'Güneşli'

    # Bilgi kartları için veri
    bilgi_kartlari = [
        {
            'baslik': 'Buğday Hastalıkları',
            'aciklama': 'Türkiye\'de buğdayda en çok karşılaşılan hastalık Sarı Pas\'tır. Özellikle nemli ve ılık geçen bahar aylarında yaygınlaşır. Erken teşhis ve doğru ilaçlama zamanlaması verim kaybını önemli ölçüde azaltır.',
            'link': 'bugday-hastaliklari',
            'tarih': '16 Mayıs 2024'
        },
        {
            'baslik': 'Tarım İstatistikleri',
            'aciklama': 'Türkiye, dünyanın en büyük buğday üreticileri arasında yer alıyor. 2023 yılında yaklaşık 20 milyon ton buğday üretimi gerçekleştirildi. Verim artışı için modern tarım tekniklerinin kullanımı önem taşıyor.',
            'link': 'tarim-istatistikleri',
            'tarih': '15 Mayıs 2024'
        },
        {
            'baslik': 'İklim Değişikliği',
            'aciklama': 'İklim değişikliği tarımsal üretimi doğrudan etkiliyor. Kuraklığa dayanıklı çeşitlerin kullanımı ve su tasarruflu sulama sistemleri, gelecekteki üretim için kritik öneme sahip.',
            'link': 'iklim-degisikligi',
            'tarih': '14 Mayıs 2024'
        },
        {
            'baslik': 'Akıllı Tarım',
            'aciklama': 'Drone teknolojisi ve yapay zeka destekli hastalık tespiti, modern tarımın vazgeçilmez parçaları haline geliyor. Bu teknolojiler sayesinde erken uyarı sistemleri daha etkili hale geliyor.',
            'link': 'akilli-tarim',
            'tarih': '13 Mayıs 2024'
        },
        {
            'baslik': 'Organik Tarım',
            'aciklama': 'Türkiye\'de organik tarım alanları her geçen yıl artıyor. 2023 yılında organik tarım yapılan alan 500 bin hektarı aştı. Bu artış, sürdürülebilir tarım uygulamalarının yaygınlaştığını gösteriyor.',
            'link': 'organik-tarim',
            'tarih': '12 Mayıs 2024'
        },
        {
            'baslik': 'Tarım Teknolojileri',
            'aciklama': 'Sensör teknolojileri ve IoT cihazları sayesinde toprak nemi, sıcaklık ve besin değerleri anlık olarak takip edilebiliyor. Bu veriler, sulama ve gübreleme zamanlamasını optimize ediyor.',
            'link': 'tarim-teknolojileri',
            'tarih': '11 Mayıs 2024'
        }
    ]

    return render_template('anaSayfa.html', 
                         sehir=sehir, 
                         sicaklik=sicaklik, 
                         durum=durum,
                         bilgi_kartlari=bilgi_kartlari)

@app.route('/bitki/<bitki_adi>')
def bitki_detay(bitki_adi):
    # Türkçe karakterleri düzelt
    dosya_adi = turkce_karakter_duzelt(bitki_adi)
    # JSON dosyasından oku
    dosya_yolu = os.path.join('bitki_veri', f'{dosya_adi}.json')
    if not os.path.exists(dosya_yolu):
        return 'Bitki bulunamadı', 404
    with open(dosya_yolu, encoding='utf-8') as f:
        bitki = json.load(f)
    return render_template('bitki_detay.html', bitki=bitki)

@app.route('/detay/<bitki_adi>/<item_adi>')
def detay_sayfasi(bitki_adi, item_adi):
    # Türkçe karakterleri düzelt
    dosya_adi = turkce_karakter_duzelt(bitki_adi)
    # Bitki verilerini yükle
    with open(f'bitki_veri/{dosya_adi}.json', 'r', encoding='utf-8') as f:
        bitki = json.load(f)
    
    # İtemi bul (hastalık, herbisit veya insektisit olabilir)
    item = None
    item_type = None
    
    # Hastalıkları kontrol et
    for h in bitki.get('hastaliklar', []):
        if h['isim'] == item_adi:
            item = h
            item_type = 'hastalik'
            break
    
    # Eğer bulunamazsa herbisitleri kontrol et
    if item is None:
        for herbisit in bitki.get('herbisitler', []):
            if herbisit['isim'] == item_adi:
                item = herbisit
                item_type = 'herbisit'
                break
    
    # Eğer hala bulunamazsa insektisitleri kontrol et
    if item is None:
        for insektisit in bitki.get('insektisitler', []):
            if insektisit['isim'] == item_adi:
                item = insektisit
                item_type = 'insektisit'
                break

    
    if item is None:
        return "Detay bulunamadı", 404
    
    return render_template('hastalik_detay.html', bitki=bitki, item=item, item_type=item_type)

from flask import send_from_directory

@app.route('/static/manifest.json')
def manifest():
    return send_from_directory('static', 'manifest.json', mimetype='application/manifest+json')

@app.route('/bilgi-kartlari')
def bilgi_kartlari():
    return render_template('bilgi_kartlari.html')

@app.route('/bilgi/<konu>')
def bilgi_detay(konu):
    # Konu başlıklarını ve içeriklerini bir sözlükte saklayalım
    bilgi_icerikleri = {
        'bugday-hastaliklari': {
            'baslik': 'Buğday Hastalıkları',
            'icerik': {
                'genel_bilgi': 'Buğday hastalıkları, üretimde verim kaybına neden olan önemli faktörlerden biridir. Özellikle nemli ve ılık geçen bahar aylarında hastalık riski artar.',
                'hastaliklar': [
                    {
                        'isim': 'Sarı Pas',
                        'belirtiler': 'Yapraklarda sarı-turuncu lekeler, yaprak dökümü',
                        'mudahale': 'Erken dönemde fungisit uygulaması',
                        'onlemler': 'Dayanıklı çeşit kullanımı, erken ekim'
                    },
                    {
                        'isim': 'Külleme',
                        'belirtiler': 'Yapraklarda beyaz pudra görünümü',
                        'mudahale': 'Sistemik fungisitler',
                        'onlemler': 'Hava sirkülasyonu, dengeli gübreleme'
                    }
                ]
            }
        },
        'tarim-istatistikleri': {
            'baslik': 'Tarım İstatistikleri',
            'icerik': {
                'genel_bilgi': 'Türkiye tarım sektörü, dünya tarımında önemli bir yere sahiptir.',
                'veriler': {
                    'bugday_uretim': '20 milyon ton',
                    'ekili_alan': '7.5 milyon hektar',
                    'verim': '2.67 ton/hektar'
                }
            }
        },
        'iklim-degisikligi': {
            'baslik': 'İklim Değişikliği ve Tarım',
            'icerik': {
                'genel_bilgi': 'İklim değişikliği, tarımsal üretimi doğrudan etkileyen en önemli faktörlerden biridir.',
                'etkiler': [
                    'Kuraklık riski artışı',
                    'Hastalık ve zararlı popülasyonlarında değişim',
                    'Üretim sezonlarında kayma'
                ],
                'cozumler': [
                    'Kuraklığa dayanıklı çeşitler',
                    'Su tasarruflu sulama sistemleri',
                    'Toprak nemini koruyan tarım teknikleri'
                ]
            }
        },
        'akilli-tarim': {
            'baslik': 'Akıllı Tarım Teknolojileri',
            'icerik': {
                'genel_bilgi': 'Modern tarım teknolojileri, üretim verimliliğini artırmada önemli rol oynar.',
                'teknolojiler': [
                    {
                        'isim': 'Drone Teknolojisi',
                        'kullanim': 'İlaçlama, gözlem, haritalama',
                        'avantajlar': 'Hızlı müdahale, düşük maliyet'
                    },
                    {
                        'isim': 'Yapay Zeka',
                        'kullanim': 'Hastalık tespiti, verim tahmini',
                        'avantajlar': 'Erken uyarı, doğru karar'
                    }
                ]
            }
        },
        'organik-tarim': {
            'baslik': 'Organik Tarım',
            'icerik': {
                'genel_bilgi': 'Organik tarım, sürdürülebilir tarım uygulamalarının en önemli parçalarından biridir.',
                'avantajlar': [
                    'Çevre dostu üretim',
                    'Daha yüksek ürün değeri',
                    'Sürdürülebilir tarım'
                ],
                'uygulamalar': [
                    'Doğal gübre kullanımı',
                    'Biyolojik mücadele',
                    'Rotasyon uygulamaları'
                ]
            }
        },
        'tarim-teknolojileri': {
            'baslik': 'Tarım Teknolojileri',
            'icerik': {
                'genel_bilgi': 'Modern tarım teknolojileri, üretim süreçlerini optimize eder.',
                'teknolojiler': [
                    {
                        'isim': 'IoT Sensörleri',
                        'kullanim': 'Toprak analizi, sulama kontrolü',
                        'faydalar': 'Su tasarrufu, verim artışı'
                    },
                    {
                        'isim': 'Mobil Uygulamalar',
                        'kullanim': 'Hastalık takibi, ilaçlama planlaması',
                        'faydalar': 'Kolay erişim, hızlı karar'
                    }
                ]
            }
        }
    }
    
    # İstenen konunun içeriğini al
    konu_icerigi = bilgi_icerikleri.get(konu)
    if konu_icerigi is None:
        abort(404)
    
    return render_template('bilgi_detay.html', konu=konu_icerigi)

def _yukle_bitki_verileri() -> Dict[str, Any]:
    """Tüm bitki verilerini JSON dosyalarından yükler ve önbelleğe alır."""
    global _bitki_verileri_cache
    if _bitki_verileri_cache is not None:
        return _bitki_verileri_cache
    
    bitki_verileri = {}
    bitki_veri_klasoru = 'bitki_veri'
    
    for dosya in os.listdir(bitki_veri_klasoru):
        if dosya.endswith('.json'):
            bitki_adi = dosya[:-5]  # .json uzantısını kaldır
            with open(os.path.join(bitki_veri_klasoru, dosya), 'r', encoding='utf-8') as f:
                bitki_verileri[bitki_adi] = json.load(f)
    
    _bitki_verileri_cache = bitki_verileri
    return bitki_verileri

def _olustur_arama_indeksi() -> Dict[str, List[Dict[str, Any]]]:
    """Bitki verilerinden arama indeksi oluşturur."""
    global _bitki_arama_indeksi
    if _bitki_arama_indeksi is not None:
        return _bitki_arama_indeksi
    
    bitki_verileri = _yukle_bitki_verileri()
    indeks = {
        'bitkiler': [],
        'hastaliklar': [],
        'ilaclar': []
    }
    
    for bitki_adi, bitki in bitki_verileri.items():
        # Bitki bilgilerini indekse ekle
        bitki_item = {
            'type': 'bitki',
            'title': bitki['isim'],
            'description': bitki.get('aciklama', ''),
            'icon': 'ri-plant-line',
            'link': f'/bitki/{bitki_adi}',
            'keywords': [bitki['isim'].lower()] + 
                       [h['isim'].lower() for h in bitki.get('hastaliklar', [])] +
                       [bitki_adi.lower()],
            'alt_kategoriler': bitki.get('cesitler', []),
            'hastaliklar': [h['isim'].lower() for h in bitki.get('hastaliklar', [])],
            'bolgeler': bitki.get('bolgeler', []),
            'detay': bitki  # Tüm detay bilgileri
        }
        indeks['bitkiler'].append(bitki_item)
        
        # Hastalık bilgilerini indekse ekle
        for hastalik in bitki.get('hastaliklar', []):
            hastalik_item = {
                'type': 'hastalik',
                'title': hastalik['isim'],
                'description': hastalik.get('aciklama', ''),
                'icon': 'ri-virus-line',
                'link': f'/hastalik/{bitki_adi}/{turkce_karakter_duzelt(hastalik["isim"])}',
                'keywords': [hastalik['isim'].lower()] + 
                           [bitki['isim'].lower()] +
                           hastalik.get('belirtiler', []) +
                           hastalik.get('mudahale', []) +
                           hastalik.get('onlemler', []),
                'etkilenen_bitkiler': [bitki['isim'].lower()],
                'belirtiler': hastalik.get('belirtiler', []),
                'donem': hastalik.get('donem', []),
                'detay': hastalik  # Tüm detay bilgileri
            }
            indeks['hastaliklar'].append(hastalik_item)
    
    # Mevcut ilaç verilerini de ekle
    indeks['ilaclar'] = arama_verileri['ilaclar']
    
    _bitki_arama_indeksi = indeks
    return indeks

@app.route('/api/search')
def search():
    # API'ye gönderilecek sorgu parametrelerini al
    query = request.args.get('q', '')
    categories = request.args.getlist('categories') # Birden fazla kategori seçilebilir

    if not query:
        return jsonify([]) # Boş sorguda boş sonuç döndür

    # Arama fonksiyonunu çağır
    results = _arama(query, categories)

    return jsonify(results)

@app.route('/borsa')
def borsa():
    # Tarım borsası verilerini şablona gönder
    commodity_prices = get_commodity_prices()
    return render_template('borsa.html', commodity_prices=commodity_prices)

def get_currency_rates():
    """Para birimi verilerini çeker ve önbelleğe alır."""
    global _currency_cache, _currency_cache_time
    
    # Önbellekteki veri hala geçerli mi kontrol et
    if _currency_cache is not None and _currency_cache_time is not None:
        if datetime.now() - _currency_cache_time < CACHE_DURATION:
            return _currency_cache
    
    try:
        # ExchangeRate-API'den veri çek (ücretsiz API)
        response = requests.get('https://open.er-api.com/v6/latest/USD')
        data = response.json()
        
        if data['result'] == 'success':
            # TRY kuru
            try_rate = data['rates']['TRY']
            
            # Euro kuru için ayrı bir istek
            eur_response = requests.get('https://open.er-api.com/v6/latest/EUR')
            eur_data = eur_response.json()
            eur_rate = eur_data['rates']['TRY'] if eur_data['result'] == 'success' else None
            
            # Altın fiyatı için ayrı bir API (örnek olarak)
            # Not: Gerçek uygulamada güvenilir bir altın API'si kullanılmalıdır
            gold_price = try_rate * 0.0005  # Örnek hesaplama
            
            # Değişim oranları (örnek veriler)
            # Gerçek uygulamada geçmiş verilerden hesaplanmalıdır
            usd_change = round((try_rate - 31.5) / 31.5 * 100, 2)  # Örnek değişim
            eur_change = round((eur_rate - 34.2) / 34.2 * 100, 2) if eur_rate else 0
            gold_change = round((gold_price - 1950) / 1950 * 100, 2)  # Örnek değişim
            
            _currency_cache = {
                'usd': {'price': try_rate, 'change': usd_change},
                'eur': {'price': eur_rate, 'change': eur_change},
                'gold': {'price': gold_price, 'change': gold_change}
            }
            _currency_cache_time = datetime.now()
            
            return _currency_cache
    except Exception as e:
        print(f"Para birimi verileri alınamadı: {e}")
        # Hata durumunda örnek veriler
        return {
            'usd': {'price': 31.50, 'change': 0.5},
            'eur': {'price': 34.20, 'change': -0.3},
            'gold': {'price': 1950.00, 'change': 1.2}
        }

@app.route('/api/currency-rates')
def currency_rates():
    """Para birimi verilerini JSON olarak döndürür."""
    rates = get_currency_rates()
    return jsonify(rates)

def get_commodity_prices():
    """Tarım borsası verilerini çeker ve önbelleğe alır."""
    global _commodity_cache, _commodity_cache_time
    
    # Önbellekteki veri hala geçerli mi kontrol et
    if _commodity_cache is not None and _commodity_cache_time is not None:
        if datetime.now() - _commodity_cache_time < COMMODITY_CACHE_DURATION:
            return _commodity_cache
    
    try:
        # TMO'nun günlük fiyat listesi API'si (örnek URL)
        # Not: Gerçek API endpoint'i ve authentication bilgileri gerekli olacaktır
        response = requests.get('https://www.tmo.gov.tr/tr/fiyat-listesi')
        
        # HTML içeriğini parse et
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
        
        _commodity_cache = commodity_data
        _commodity_cache_time = datetime.now()
        
        return _commodity_cache
        
    except Exception as e:
        print(f"Tarım borsası verileri alınamadı: {e}")
        # Hata durumunda örnek veriler
        return {
            'bugday': {
                'ekmeklik': {'price': 8500, 'change': 1.2, 'unit': 'TL/Ton', 'date': datetime.now().strftime('%d.%m.%Y')},
                'makarnalik': {'price': 8200, 'change': 0.8, 'unit': 'TL/Ton', 'date': datetime.now().strftime('%d.%m.%Y')}
            },
            'arpa': {
                'yemlik': {'price': 7200, 'change': -0.5, 'unit': 'TL/Ton', 'date': datetime.now().strftime('%d.%m.%Y')}
            },
            'misir': {
                'yemlik': {'price': 6100, 'change': 1.5, 'unit': 'TL/Ton', 'date': datetime.now().strftime('%d.%m.%Y')}
            },
            'nohut': {
                'kirmizi': {'price': 25000, 'change': 1.8, 'unit': 'TL/Ton', 'date': datetime.now().strftime('%d.%m.%Y')},
                'sari': {'price': 24500, 'change': 1.5, 'unit': 'TL/Ton', 'date': datetime.now().strftime('%d.%m.%Y')}
            }
        }

@app.route('/api/commodity-prices')
def commodity_prices():
    """Tarım borsası verilerini JSON olarak döndürür."""
    prices = get_commodity_prices()
    return jsonify(prices)

def get_news():
    """Tarım ve Orman Bakanlığı haber arşivinden haber verilerini çeker ve kaydeder."""
    news_list = []
    cache_data = None
    cache_timestamp = None
    url = 'https://www.tarimorman.gov.tr/HaberArsivi'

    # 1. Önbellek dosyasından veriyi oku
    if os.path.exists(_news_cache_file):
        try:
            with open(_news_cache_file, 'r', encoding='utf-8') as f:
                cache_content = json.load(f)
                cache_data = cache_content.get('news', [])
                # Zaman damgasını datetime objesine çevir
                timestamp_str = cache_content.get('timestamp')
                if timestamp_str:
                    cache_timestamp = datetime.fromisoformat(timestamp_str)
        except Exception as e:
            print(f"Haber önbellek dosyası okunamadı: {e}")
            cache_data = None # Okuma hatası durumunda önbelleği geçersiz say

    # 2. Önbelleğin geçerliliğini kontrol et
    is_cache_valid = False
    if cache_timestamp and cache_data is not None:
        # Önbellek süresi bir haftadan azsa geçerli
        if datetime.now() - cache_timestamp < timedelta(days=NEWS_CACHE_DURATION_DAYS):
            is_cache_valid = True

    # 3. Veriyi çekme veya önbelleği kullanma mantığı
    if is_cache_valid:
        # Önbellek geçerliyse, önbellekteki veriyi döndür
        print("Haberler önbellekten getirildi.")
        return cache_data
    else:
        # Önbellek geçerli değilse (yok veya süresi dolmuş)
        # Sadece Pazartesi günleri scraping yap - Bu kontrol şu an yorum satırında, Pazartesi güncellemesi için etkinleştirilebilir.
        # if datetime.now().weekday() == 0: # Pazartesi = 0
        print("Önbellek süresi dolmuş veya dosya yok. Scraping yapılıyor...")
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Haber öğelerini bulma ve parse etme mantığı (önceki güncellemelerden)
            news_list = []
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
                    image = '' # Görsel yok

                    news_list.append({
                        'title': title,
                        'summary': summary,
                        'link': link,
                        'image': image
                    })
                except Exception as e:
                    print(f"Haber öğesi parse edilirken hata oluştu: {e}")
                    continue

            # Başarılı scraping sonrası veriyi kaydet
            try:
                with open(_news_cache_file, 'w', encoding='utf-8') as f:
                    json.dump({'news': news_list, 'timestamp': datetime.now().isoformat()}, f, ensure_ascii=False, indent=4)
                print("Yeni haberler dosyaya kaydedildi.")
            except Exception as e:
                print(f"Haber önbellek dosyasına yazılamadı: {e}")

            return news_list

        except requests.exceptions.RequestException as e:
            print(f"Haber kaynağına bağlanırken hata oluştu: {e}")
            # Bağlantı hatası durumunda, eğer eski veri varsa onu kullan
            if cache_data is not None:
                 print("Bağlantı hatası, eski önbellek verisi kullanılıyor.")
                 return cache_data
            return [] # Hata ve eski veri yoksa boş liste
        except Exception as e:
            print(f"Haber verileri alınamadı veya parse hatası: {e}")
             # Hata durumunda, eğer eski veri varsa onu kullan
            if cache_data is not None:
                 print("Parse hatası, eski önbellek verisi kullanılıyor.")
                 return cache_data
            return [] # Hata ve eski veri yoksa boş liste
        # else:
            # Pazartesi değil ve önbellek süresi dolmuş, eski veri varsa onu kullan
            # if cache_data is not None:
            #      print("Önbellek süresi dolmuş ama bugün Pazartesi değil, eski önbellek verisi kullanılıyor.")
            #      return cache_data
            # print("Önbellek süresi dolmuş veya dosya yok. Bugün Pazartesi değil, scraping yapılmıyor.")
            # return [] # Pazartesi değil ve eski veri yok

@app.route('/api/news')
def news_api():
    """Haber verilerini JSON olarak döndürür."""
    news_data = get_news()
    return jsonify(news_data)

if __name__ == '__main__':
    app.run(debug=True, port=8501)

'''
if __name__ == '__main__':
    app.run(debug=True, port=8501)
    agrowy.com
'''