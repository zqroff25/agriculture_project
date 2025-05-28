from PIL import Image, ImageDraw, ImageFont
import os
import shutil

def create_test_image(filename, text, size=(800, 600), bg_color=(255, 255, 255), text_color=(0, 0, 0)):
    # Yeni bir görsel oluştur
    img = Image.new('RGB', size, bg_color)
    draw = ImageDraw.Draw(img)
    
    # Metin ekle
    try:
        font = ImageFont.truetype("arial.ttf", 40)
    except:
        font = ImageFont.load_default()
    
    # Metni ortala
    text_width = draw.textlength(text, font=font)
    text_height = 40
    x = (size[0] - text_width) // 2
    y = (size[1] - text_height) // 2
    
    # Metni çiz
    draw.text((x, y), text, font=font, fill=text_color)
    
    # Görseli kaydet
    os.makedirs('static/hastaliklar', exist_ok=True)
    img.save(f'static/hastaliklar/{filename}')

def copy_test_image(source, target):
    # Hedef dizini oluştur
    os.makedirs('static/hastaliklar', exist_ok=True)
    # Görseli kopyala
    shutil.copy2(source, f'static/hastaliklar/{target}')
    print(f'Kopyalandı: {target}')

# Kaynak görsel
source_image = 'static/sariPas.png'

# Fungusit hastalıkları için görseller
fungusit_hastaliklar = [
    'sari_pas_1.jpg',
    'sari_pas_2.jpg',
    'sari_pas_3.jpg',
    'kahverengi_pas_1.jpg',
    'kahverengi_pas_2.jpg',
    'kara_pas_1.jpg',
    'kara_pas_2.jpg',
    'surme_1.jpg',
    'surme_2.jpg',
    'rastik_1.jpg',
    'rastik_2.jpg',
    'kuleme_1.jpg',
    'kuleme_2.jpg',
    'septoria_1.jpg',
    'septoria_2.jpg',
    'fusarium_1.jpg',
    'fusarium_2.jpg',
    'kok_curuklugu_1.jpg',
    'kok_curuklugu_2.jpg'
]

# Herbisit (yabani ot) görselleri
herbisit_hastaliklar = [
    'yabani_hardal_1.jpg',
    'yabani_hardal_2.jpg',
    'yabani_yulaf_1.jpg',
    'yabani_yulaf_2.jpg',
    'tilki_kuyrugu_1.jpg',
    'tilki_kuyrugu_2.jpg',
    'delice_1.jpg',
    'delice_2.jpg',
    'cobancantasi_1.jpg',
    'cobancantasi_2.jpg',
    'gelincik_1.jpg',
    'gelincik_2.jpg',
    'yabani_turp_1.jpg',
    'yabani_turp_2.jpg',
    'koygocuren_1.jpg',
    'koygocuren_2.jpg',
    'tarla_sarmasigi_1.jpg',
    'tarla_sarmasigi_2.jpg',
    'ballibaba_1.jpg',
    'ballibaba_2.jpg'
]

# İnsektisit (zararlı) görselleri
insektisit_hastaliklar = [
    'sune_1.jpg',
    'sune_2.jpg',
    'kimil_1.jpg',
    'kimil_2.jpg',
    'ekin_kambur_1.jpg',
    'ekin_kambur_2.jpg',
    'ekin_bambul_1.jpg',
    'ekin_bambul_2.jpg',
    'yaprak_biti_1.jpg',
    'yaprak_biti_2.jpg',
    'thrips_1.jpg',
    'thrips_2.jpg'
]

# Tüm görselleri kopyala
for filename in fungusit_hastaliklar + herbisit_hastaliklar + insektisit_hastaliklar:
    copy_test_image(source_image, filename) 