from flask import Flask, request, jsonify, render_template
import requests
import json
import os

app = Flask(__name__, static_folder='static')

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
    return render_template('anaSayfa.html', sehir=sehir, sicaklik=sicaklik, durum=durum)

@app.route('/bitki/<bitki_adi>')
def bitki_detay(bitki_adi):
    # JSON dosyasından oku
    dosya_yolu = os.path.join('bitki_veri', f'{bitki_adi}.json')
    if not os.path.exists(dosya_yolu):
        return 'Bitki bulunamadı', 404
    with open(dosya_yolu, encoding='utf-8') as f:
        bitki = json.load(f)
    return render_template('bitki_detay.html', bitki=bitki)

from flask import send_from_directory

@app.route('/static/manifest.json')
def manifest():
    return send_from_directory('static', 'manifest.json', mimetype='application/manifest+json')

if __name__ == '__main__':
    app.run(debug=True, port=8501)

'''
if __name__ == '__main__':
    app.run(debug=True, port=8501)
'''