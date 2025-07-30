# Goodreaps: Goodreads Scraper

## 1. Aplikasi Dashboard (`dashboard.py`)

### Gambaran Umum
Dashboard ini merupakan alat analisis sentimen komprehensif untuk ulasan buku Goodreads yang memiliki fitur:
- Pra-pemrosesan dan pembersihan data
- Analisis sentimen menggunakan model multibahasa BERT
- Visualisasi interaktif
- Generasi data sampel
- Fungsi unggah CSV

### Kelas Utama

#### ReviewPreprocessor
Menangani pra-pemrosesan dan pembersihan teks ulasan.

**Metode Utama:**
- `clean_text(text)`: Membersihkan dan memproses teks dengan menghapus HTML, URL, karakter khusus, stopword, serta menerapkan stemming
- `is_valid_review(text, min_length=10)`: Memeriksa apakah ulasan memenuhi persyaratan panjang minimum untuk analisis

#### SentimentAnalyzer
Melakukan analisis sentimen menggunakan model transformer.

**Metode Utama:**
- `_load_transformer_model()`: Memuat model sentimen multibahasa BERT
- `analyze_sentiment_transformer(text)`: Menganalisis sentimen dari sebuah teks
- `analyze_batch(texts)`: Menganalisis sentimen untuk sekumpulan teks

#### DataGenerator
Menghasilkan data ulasan sampel menyerupai Goodreads untuk keperluan demonstrasi.

**Metode Utama:**
- `generate_sample_data(n_reviews=1000)`: Membuat data ulasan sintetis dengan pola yang realistis

#### Dashboard
Kelas utama yang mengatur aplikasi Streamlit.

**Metode Utama:**
- `setup_page()`: Mengonfigurasi pengaturan halaman Streamlit
- `sidebar_controls()`: Membuat kontrol sidebar interaktif
- `load_data()`: Menangani pemuatan data (sampel atau CSV yang diunggah)
- `preprocess_data()`: Membersihkan dan mempersiapkan data untuk analisis
- `create_visualizations()`: Menghasilkan semua bagan dan tabel dashboard
- `run()`: Metode eksekusi utama untuk dashboard

### Tab Visualisasi
Dashboard mencakup lima tab utama:
1. **Gambaran Umum**: Menampilkan metrik ringkasan dan distribusi dasar
2. **Tren**: Menampilkan tren sentimen dan peringkat dari waktu ke waktu
3. **Analisis Peringkat**: Menguji hubungan antara peringkat dan sentimen
4. **Word Clouds**: Memvisualisasikan kata-kata paling sering berdasarkan sentimen
5. **Tampilan Detail**: Menyediakan akses terfilter ke data ulasan mentah

## 2. Spider Buku (`goodreads_books.py`)

### Gambaran Umum
Mengambil metadata buku dari Goodreads termasuk:
- Judul, penulis, peringkat rata-rata
- Jumlah peringkat dan ulasan
- ISBN, jumlah halaman, penerbit
- Genre

### Fitur Utama
- Mengambil buku secara berurutan berdasarkan ID (rentang yang dapat dikonfigurasi)
- Penanganan error dan logika percobaan ulang yang kuat
- Saluran pembersihan data
- Output CSV dengan detail buku yang komprehensif

### Metode Utama
- `start_requests()`: Membuat permintaan awal untuk halaman buku
- `parse_book(response)`: Mengekstrak detail buku dari HTML halaman
- `extract_text(response, selector)`: Pembantu untuk ekstraksi teks bersih
- `handle_error(failure)`: Penanganan error untuk permintaan yang gagal

### Konfigurasi
- Pengaturan penundaan khusus untuk menghindari pembatasan laju
- Penundaan acak antara permintaan
- Logika percobaan ulang untuk permintaan yang gagal
- Pengaturan user-agent dan header yang komprehensif

## 3. Spider Ulasan (`goodreads_reviews.py`)

### Gambaran Umum
Mengambil ulasan buku dari Goodreads termasuk:
- Teks ulasan dan peringkat
- Informasi reviewer
- Tanggal ulasan
- Detail buku terkait

### Fitur Utama
- Mengambil ulasan untuk buku dalam rentang ID yang dapat dikonfigurasi
- Beberapa strategi cadangan untuk ekstraksi data
- Pembersihan teks yang menyeluruh
- Penanganan error yang kuat
- Output CSV dengan metadata ulasan dan buku

### Metode Utama
- `start_requests()`: Membuat permintaan awal untuk halaman buku
- `parse_book_page(response)`: Logika parsing utama untuk ekstraksi ulasan
- `extract_book_title(response)`, `extract_book_author(response)`: Ekstraksi metadata buku
- `extract_avg_rating(response)`, `extract_ratings_count(response)`: Ekstraksi info peringkat
- `extract_reviews(response, book_id)`: Mengekstrak semua ulasan dari halaman buku
- `extract_review_text(card)`: Ekstraksi teks ulasan yang kuat dengan beberapa cadangan
- `clean_text(text)`: Metode pembersihan teks yang menyeluruh

### Konfigurasi
- Penundaan permintaan yang konservatif untuk menghindari pemblokiran
- Permintaan bersamaan tunggal
- Pengaturan percobaan ulang yang komprehensif
- Pengkodean UTF-8 untuk output teks

## Aliran Data

1. **Pengumpulan Data**:
   - Spider buku mengumpulkan metadata tentang buku
   - Spider ulasan mengumpulkan ulasan aktual dengan peringkat

2. **Pemrosesan Data**:
   - Ulasan dibersihkan dan diproses sebelumnya
   - Analisis sentimen dilakukan menggunakan model BERT
   - Hasil di-cache untuk kinerja

3. **Visualisasi**:
   - Dashboard interaktif menunjukkan distribusi sentimen
   - Tren dari waktu ke waktu dianalisis
   - Frekuensi kata divisualisasikan
   - Data mentah dapat difilter dan diekspor

## Rekomendasi Penggunaan

1. **Untuk Pengambilan Data**:
   - Jalankan spider secara terpisah dengan `scrapy crawl [nama_spider]`
   - Sesuaikan parameter `START_ID` dan `END_ID` sesuai kebutuhan
   - Pertimbangkan untuk menjalankan selama jam sepi untuk Goodreads

2. **Untuk Dashboard**:
   - Instal dependensi yang diperlukan dengan `pip install -r requirements.txt`
   - Jalankan dengan `streamlit run dashboard.py`
   - Mulai dengan data sampel untuk mengeksplorasi fungsionalitas
   - Unggah CSV Anda sendiri dengan kolom yang diperlukan untuk analisis khusus

3. **Untuk Analisis**:
   - Sesuaikan ambang batas kepercayaan berdasarkan kebutuhan Anda
   - Bereksperimen dengan ukuran potongan yang berbeda untuk ulasan panjang
   - Gunakan tampilan detail untuk memeriksa ulasan tertentu yang menarik
