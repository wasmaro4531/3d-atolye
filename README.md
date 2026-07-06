# 3D Atölye Yönetim ve Optimizasyon Platformu

3D baskı atölyesi için geliştirilmiş all-in-one yönetim paneli.

## Modüller
- **Dashboard** - Ciro, kâr, stok durumu grafikleri
- **Filament Stok** - Raf ömrü, nem takibi, CRUD işlemleri
- **Maliyet & ROI** - Akıllı maliyet hesaplama, yatırım geri dönüşü
- **Sipariş Oluştur** - Çoklu filament + ek giderler ile teklif/sipariş
- **Gider Yönetimi** - Anahtarlık zinciri, hediye paketi vb. ek giderler
- **G-code Optimizasyon** - F değeri limit optimizasyonu
- **Kalite Kontrol** - Kural tabanlı kusur analizi

## Teknolojiler
- Python 3.12+
- Streamlit
- SQLite
- Plotly

## Çalıştırma
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Cloud Deploy
[![Streamlit](https://img.shields.io/badge/Streamlit-Cloud-ff4b4b?logo=streamlit)](https://share.streamlit.io/)
