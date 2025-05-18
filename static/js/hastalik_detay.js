// Global değişkenler
let currentSlide = 0;
let currentModalIndex = 0;
let totalSlides = 0;
let slider = null;
let dots = null;
let diseaseImages = [];

// Sayfa yüklendiğinde çalışacak fonksiyon
function initSlider() {
    const container = document.querySelector('.slider-container');
    slider = document.getElementById('diseaseSlider');
    dots = document.querySelectorAll('.slider-dot');
    
    // Data attribute'lardan değerleri al
    totalSlides = parseInt(container.dataset.totalSlides);
    diseaseImages = JSON.parse(container.dataset.images);

    // Event listener'ları ekle
    setupEventListeners();
    
    // İlk slider durumunu güncelle
    updateSlider();

    // Otomatik slider
    let slideInterval = setInterval(nextSlide, 5000);

    // Mouse hover olduğunda otomatik geçişi durdur
    container.addEventListener('mouseenter', () => {
        clearInterval(slideInterval);
    });

    // Mouse ayrıldığında otomatik geçişi başlat
    container.addEventListener('mouseleave', () => {
        slideInterval = setInterval(nextSlide, 5000);
    });
}

function setupEventListeners() {
    // Slider navigasyon butonları
    document.querySelector('.slider-prev').addEventListener('click', prevSlide);
    document.querySelector('.slider-next').addEventListener('click', nextSlide);
    
    // Slider noktaları
    dots.forEach(dot => {
        dot.addEventListener('click', () => {
            goToSlide(parseInt(dot.dataset.index));
        });
    });

    // Resimlere tıklama
    document.querySelectorAll('.slider-item img').forEach(img => {
        img.addEventListener('click', () => {
            openModal(diseaseImages[parseInt(img.dataset.index)], parseInt(img.dataset.index));
        });
    });

    // Modal kontrolleri
    const modal = document.getElementById('imageModal');
    const modalContent = modal.querySelector('.modal-content');
    const modalClose = modal.querySelector('.modal-close');
    const modalPrev = modal.querySelector('.modal-prev');
    const modalNext = modal.querySelector('.modal-next');

    modal.addEventListener('click', closeModal);
    modalContent.addEventListener('click', e => e.stopPropagation());
    modalClose.addEventListener('click', closeModal);
    modalPrev.addEventListener('click', e => prevModalImage(e));
    modalNext.addEventListener('click', e => nextModalImage(e));

    // Klavye kontrolleri
    document.addEventListener('keydown', handleKeyPress);
}

function updateSlider() {
    slider.style.transform = `translateX(-${currentSlide * 100}%)`;
    dots.forEach((dot, index) => {
        dot.classList.toggle('active', index === currentSlide);
    });
}

function nextSlide() {
    currentSlide = (currentSlide + 1) % totalSlides;
    updateSlider();
}

function prevSlide() {
    currentSlide = (currentSlide - 1 + totalSlides) % totalSlides;
    updateSlider();
}

function goToSlide(index) {
    currentSlide = index;
    updateSlider();
}

function openModal(imageSrc, index) {
    const modal = document.getElementById('imageModal');
    const modalImg = document.getElementById('modalImage');
    modal.classList.add('active');
    modalImg.src = imageSrc;
    currentModalIndex = index;
    document.body.style.overflow = 'hidden';
}

function closeModal() {
    const modal = document.getElementById('imageModal');
    modal.classList.remove('active');
    document.body.style.overflow = '';
}

function nextModalImage(event) {
    event.stopPropagation();
    currentModalIndex = (currentModalIndex + 1) % totalSlides;
    const modalImg = document.getElementById('modalImage');
    modalImg.src = diseaseImages[currentModalIndex];
}

function prevModalImage(event) {
    event.stopPropagation();
    currentModalIndex = (currentModalIndex - 1 + totalSlides) % totalSlides;
    const modalImg = document.getElementById('modalImage');
    modalImg.src = diseaseImages[currentModalIndex];
}

function handleKeyPress(event) {
    if (event.key === 'Escape') {
        closeModal();
    } else if (event.key === 'ArrowLeft') {
        if (document.getElementById('imageModal').classList.contains('active')) {
            prevModalImage(event);
        } else {
            prevSlide();
        }
    } else if (event.key === 'ArrowRight') {
        if (document.getElementById('imageModal').classList.contains('active')) {
            nextModalImage(event);
        } else {
            nextSlide();
        }
    }
}

// Sayfa yüklendiğinde slider'ı başlat
document.addEventListener('DOMContentLoaded', initSlider); 