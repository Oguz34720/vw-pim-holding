import streamlit as st
import pandas as pd
import os
import io
import requests
import time
from pathlib import Path
from PIL import Image, ImageDraw

# --- Gelişmiş Paket İthalat Korumaları ---
missing_packages = []

try:
    import google.generativeai as genai
except ImportError:
    genai = None
    missing_packages.append("google-generativeai")

try:
    from rembg import remove as rembg_remove
except ImportError:
    rembg_remove = None
    missing_packages.append("rembg")

try:
    import plotly.express as px
except ImportError:
    px = None
    missing_packages.append("plotly")

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None
    missing_packages.append("pypdf")

# --- Sayfa Konfigürasyonu ---
st.set_page_config(page_title="VW Classic Club PIM Holding", layout="wide", page_icon="🏎️")

# --- Durum Korumaları İçin Global Değişkenleri Başlatma ---
if "output" not in st.session_state:
    st.session_state.output = {"instagram": "", "email": "", "blog_yazisi": "", "ai_gorsel_bytes": None}
if "gemini_rapor" not in st.session_state:
    st.session_state.gemini_rapor = "Sistem optimize edildi. Sorgu bekleniyor..."

# --- Yararlı Fonksiyonlar ---
def ensure_str(value):
    if pd.isna(value) or value is None:
        return ""
    return str(value)

def get_shopify_cdn_url(resim_ismi):
    if not resim_ismi:
        return ""
    temiz_resim_ismi = str(resim_ismi).strip().replace(" ", "-").lower()
    versiyon = int(time.time())
    base_url = "https://cdn.shopify.com/s/files/1/0732/9638/0065/files/"
    return f"{base_url}{temiz_resim_ismi}?v={versiyon}"

def url_resmini_beyazlat_ve_kaydet(image_url, orijinal_isim, save_folder="Islem_Goren_Resimler"):
    if not image_url or not orijinal_isim:
        return None, "URL veya İsim eksik"
        
    try:
        response = requests.get(image_url, timeout=15)
        response.raise_for_status()
        
        img = Image.open(io.BytesIO(response.content)).convert("RGBA")
        
        # Eğer rembg bulutta tam kurulmadıysa hata verip çökmesin, pas geçsin
        if rembg_remove is not None:
            no_bg_img = rembg_remove(img)
        else:
            return None, "Bulutta Rembg modülü henüz hazır değil. Lütfen az sonra tekrar deneyin."
            
        white_bg = Image.new("RGBA", no_bg_img.size, (255, 255, 255, 255))
        white_bg.paste(no_bg_img, (0, 0), no_bg_img)
        final_img = white_bg.convert("RGB") 
        
        Path(save_folder).mkdir(parents=True, exist_ok=True)
        save_path = os.path.join(save_folder, orijinal_isim)
        kayit_formati = "JPEG" if orijinal_isim.lower().endswith(('.jpg', '.jpeg')) else "PNG"
        final_img.save(save_path, format=kayit_formati)
        
        return save_path, "Başarılı"
    except Exception as e:
        return None, f"Hata: {str(e)}"

# --- SIDEBAR: Holding Yönetim Merkezi ---
st.sidebar.title("🛠️ Holding Yönetim Merkezi")

if missing_packages:
    st.sidebar.warning(f"⚠️ Yüklenen Paketler: {', '.join(missing_packages)}")

st.sidebar.subheader("🔑 API & Bulut Kimlikleri")
gemini_key = st.sidebar.text_input("Google Gemini API Key", type="password")
project_name = st.sidebar.text_input("GCP Proje Adı", value="VW-PIM-Sistem")

if st.sidebar.button("API Bağlantısını Sına"):
    if not gemini_key or not genai:
        st.sidebar.error("Eksik API Anahtarı veya Kütüphane.")
    else:
        try:
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            res = model.generate_content("Bağlantı testi.")
            st.sidebar.success("Bağlantı Başarılı! Sistem Çevrimiçi.")
        except Exception as e:
            st.sidebar.error(f"Hata: {str(e)}")

# --- 4 ANA SEKME MİMARİSİ ---
tab1, tab2, tab3, tab4 = st.tabs([
    "🖥️ Canlı Simülatör", 
    "📦 Akıllı Katalog", 
    "📸 AI Medya Stüdyosu", 
    "📢 AI Pazarlama"
])

# TAB 1: CANLI SİMÜLATÖR
with tab1:
    st.header("🖥️ Canlı Simülatör & İş Analitiği")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🔍 Tekli Ürün Fiyat Radarı")
        urun_adi = st.text_input("Ürün Adı", value="Vosvos Distribütör Kapağı")
        sku_kodu = st.text_input("Ticimax SKU Kodu", value="4-4158")
        if st.button("Piyasa Fiyatını Tara"):
            st.success(f"{urun_adi} (SKU: {sku_kodu}) için analiz simüle edildi.")
            
    with col2:
        st.subheader("📈 Mağaza Kar/Zarar Dashboard")
        if px is not None:
            demo_data = pd.DataFrame({"Marka": ["Bosch", "Ate", "Sachs", "Meyle"], "Kar_Marji": [2500, 1800, 1400, 950]})
            fig = px.bar(demo_data, x="Marka", y="Kar_Marji", title="Karlılık Dağılımı", template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)

# TAB 2: AKILLI KATALOG
with tab2:
    st.header("📦 Akıllı Katalog & Pazaryeri Entegrasyonu")
    st.subheader("📄 Toplu Excel İşleme & CDN Linkleme")
    uploaded_excel = st.file_uploader("Ham Ticimax Excel Dosyası Yükle", type=["xlsx", "xls"])
    
    if st.button("Kataloğu İşle ve Shopify CDN ile Bağla"):
        if uploaded_excel:
            try:
                df = pd.read_excel(uploaded_excel)
                if "URUNADI" in df.columns and "STOKKODU" in df.columns:
                    for index, row in df.iterrows():
                        stok = ensure_str(row["STOKKODU"]).strip()
                        seo_resim_adi = f"{index+1}-{stok}-vw-classic-club.jpg"
                        df.at[index, "RESIM1"] = get_shopify_cdn_url(seo_resim_adi)
                st.success("Katalog Shopify formatında işlendi! 🏁")
                buffer = io.BytesIO()
                df.to_excel(buffer, index=False, engine="openpyxl")
                st.download_button("İşlenmiş Excel'i İndir", data=buffer.getvalue(), file_name="islenmis_katalog.xlsx")
            except Exception as e:
                st.error(f"Hata: {str(e)}")

# TAB 3: AI MEDYA STÜDYOSU (Otonom Resim Beyazlatma)
with tab3:
    st.header("📸 AI Medya Stüdyosu & İşlem Merkezi")
    st.subheader("🔗 URL'den Otonom Beyazlatma Motoru")
    url_excel = st.file_uploader("İçinde URL ve Orijinal Resim İsimleri Olan Excel Yükle", type=["xlsx", "xls"], key="url_beyaz")
    
    if url_excel:
        url_df = pd.read_excel(url_excel)
        col_url = st.selectbox("Resim Linklerinin Olduğu Sütun (URL)", url_df.columns)
        col_isim = st.selectbox("Orijinal Resim İsimlerinin Olduğu Sütun", url_df.columns)
        
        if st.button("Tüm Linklere Sız ve Resimleri Beyazlat"):
            with st.spinner("İnternetten resimler dekupe ediliyor..."):
                basarili, hatali = 0, 0
                for index, row in url_df.iterrows():
                    aktif_url = ensure_str(row[col_url]).strip()
                    aktif_isim = ensure_str(row[col_isim]).strip()
                    if aktif_url and aktif_isim:
                        kayit_yolu, durum = url_resmini_beyazlat_ve_kaydet(aktif_url, aktif_isim)
                        if kayit_yolu:
                            basarili += 1
                        else:
                            hatali += 1
                st.success(f"🏁 İşlem Tamamlandı! {basarili} resim stüdyo beyazına alındı. ({hatali} Hata)")

# TAB 4: AI PAZARLAMA
with tab4:
    st.header("📢 AI Pazarlama & SEO Blog Fabrikası")
    paz_urun = st.text_input("Sosyal Medya Başlığı", value="Bosch Orijinal Dağıtıcı")
    if st.button("Instagram Postu Üret"):
        if not gemini_key:
            st.error("API Anahtarı eksik.")
        else:
            try:
                genai.configure(api_key=gemini_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                res = model.generate_content(f"{paz_urun} ürünü için Instagram postu yaz.")
                st.session_state.output["instagram"] = res.text
            except Exception as e:
                st.error(f"Hata: {str(e)}")
    st.write(st.session_state.output.get("instagram", ""))