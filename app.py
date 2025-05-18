from flask import Flask, request, jsonify, render_template, abort
import requests
import json
import os
from functools import lru_cache
from typing import Dict, List, Any

app = Flask(__name__, static_folder='static')

# Önbellek için global değişkenler
_bitki_verileri_cache = None
_bitki_arama_indeksi = None

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

@app.route('/hastalik/<bitki_adi>/<hastalik_adi>')
def hastalik_detay(bitki_adi, hastalik_adi):
    # Türkçe karakterleri düzelt
    dosya_adi = turkce_karakter_duzelt(bitki_adi)
    # Bitki verilerini yükle
    with open(f'bitki_veri/{dosya_adi}.json', 'r', encoding='utf-8') as f:
        bitki = json.load(f)
    
    # Hastalığı bul
    hastalik = None
    for h in bitki['hastaliklar']:
        if h['isim'] == hastalik_adi:
            hastalik = h
            break
    
    if hastalik is None:
        return "Hastalık bulunamadı", 404
    
    return render_template('hastalik_detay.html', bitki=bitki, hastalik=hastalik)

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
    query = request.args.get('q', '').lower().strip()
    categories = request.args.getlist('categories')
    
    if not query or len(query) < 2:
        return jsonify([])
    
    # Arama indeksini al
    indeks = _olustur_arama_indeksi()
    
    # Tüm kategorileri birleştir
    all_items = []
    if not categories or 'bitki' in categories:
        all_items.extend(indeks['bitkiler'])
    if not categories or 'hastalik' in categories:
        all_items.extend(indeks['hastaliklar'])
    if not categories or 'ilac' in categories:
        all_items.extend(indeks['ilaclar'])
    
    # Arama yap
    results = []
    for item in all_items:
        # Anahtar kelimelerde ara
        keyword_match = any(query in keyword.lower() for keyword in item['keywords'])
        
        # Başlık ve açıklamada ara
        title_match = query in item['title'].lower()
        desc_match = query in item['description'].lower()
        
        # Alt kategorilerde ara (varsa)
        alt_kategori_match = False
        if 'alt_kategoriler' in item:
            alt_kategori_match = any(query in cat.lower() for cat in item['alt_kategoriler'])
        
        # Hastalıklarda ara (varsa)
        hastalik_match = False
        if 'hastaliklar' in item:
            hastalik_match = any(query in h.lower() for h in item['hastaliklar'])
        
        # Bölgelerde ara (varsa)
        bolge_match = False
        if 'bolgeler' in item:
            bolge_match = any(query in b.lower() for b in item['bolgeler'])
        
        # Belirtilerde ara (varsa)
        belirti_match = False
        if 'belirtiler' in item:
            belirti_match = any(query in b.lower() for b in item['belirtiler'])
        
        # Dönemlerde ara (varsa)
        donem_match = False
        if 'donem' in item:
            donem_match = any(query in d.lower() for d in item['donem'])
        
        # Eğer herhangi bir eşleşme varsa sonuçlara ekle
        if (keyword_match or title_match or desc_match or 
            alt_kategori_match or hastalik_match or bolge_match or 
            belirti_match or donem_match):
            
            # Sonuç öğesini oluştur
            result_item = {
                'type': item['type'],
                'title': item['title'],
                'description': item['description'],
                'icon': item['icon'],
                'link': item['link']
            }
            
            # Eşleşme türünü belirt (öne çıkarma için)
            if title_match:
                result_item['match_type'] = 'title'
            elif keyword_match:
                result_item['match_type'] = 'keyword'
            elif hastalik_match:
                result_item['match_type'] = 'hastalik'
            elif alt_kategori_match:
                result_item['match_type'] = 'alt_kategori'
            else:
                result_item['match_type'] = 'other'
            
            # Eşleşen içeriği vurgulamak için ek bilgiler
            if 'detay' in item:
                result_item['detay'] = item['detay']
            
            results.append(result_item)
    
    # Sonuçları önceliklendir
    results.sort(key=lambda x: {
        'title': 1,
        'keyword': 2,
        'hastalik': 3,
        'alt_kategori': 4,
        'other': 5
    }.get(x.get('match_type', 'other'), 5))
    
    return jsonify(results)

if __name__ == '__main__':
    app.run(debug=True, port=8501)

'''
if __name__ == '__main__':
    app.run(debug=True, port=8501)
    agrowy.com
'''