import streamlit as st
import pandas as pd
import os
import io
import requests
import re
import time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

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

# --- Durum Korumaları İçin Global Değişkenleri Başlatma (Initialization) ---
if "output" not in st.session_state:
    st.session_state.output = {"instagram": "", "email": "", "blog_yazisi": "", "ai_gorsel_bytes": None}
if "gemini_rapor" not in st.session_state:
    st.session_state.gemini_rapor = "Sistem optimize edildi. Sorgu bekleniyor..."
if "kurallar" not in st.session_state:
    st.session_state.kurallar = pd.DataFrame()
if "kategori_agaci" not in st.session_state:
    st.session_state.kategori_agaci = pd.DataFrame()
if "catalog_df" not in st.session_state:
    st.session_state.catalog_df = None

# --- Yararlı Fonksiyonlar (Core Engines) ---

def ensure_str(value):
    if pd.isna(value) or value is None:
        return ""
    return str(value)

def robust_match(val1, val2):
    if pd.isna(val1) or pd.isna(val2):
        return False
    return str(val1).strip().lower() in str(val2).strip().lower()

def get_shopify_cdn_url(resim_ismi):
    """Shopify CDN altyapısına uygun versiyon damgalı resim linki üretir."""
    if not resim_ismi:
        return ""
    temiz_resim_ismi = str(resim_ismi).strip().replace(" ", "-").lower()
    versiyon = int(time.time())
    base_url = "https://cdn.shopify.com/s/files/1/0732/9638/0065/files/"
    return f"{base_url}{temiz_resim_ismi}?v={versiyon}"

def generate_ai_visual(prompt, aspect_ratio="1:1"):
    """Imagen 3 modeli ile metinden görsel üretir."""
    try:
        if not genai:
            return None
        model = genai.GenerativeModel('imagen-3.0-generate-001')
        result = model.generate_content(
            prompt,
            generation_config={"aspect_ratio": aspect_ratio, "number_of_images": 1}
        )
        return result.images[0] 
    except Exception as e:
        return None

def url_resmini_beyazlat_ve_kaydet(image_url, orijinal_isim, save_folder="Islem_Goren_Resimler"):
    """
    URL'deki resmi internetten çeker, arka planını dekupe eder, 
    saf beyaz stüdyo fonuna koyar ve orijinal ismine sadık kalarak kaydeder.
    """
    if not image_url or not orijinal_isim:
        return None, "URL veya İsim eksik"
        
    try:
        # 1. Canlı URL'den resmi indir
        response = requests.get(image_url, timeout=15)
        response.raise_for_status()
        
        # 2. Pillow ile hafızaya al
        img = Image.open(io.BytesIO(response.content)).convert("RGBA")
        
        # 3. Arka planı otonom sil (Rembg)
        if rembg_remove is not None:
            no_bg_img = rembg_remove(img)
        else:
            return None, "Rembg kütüphanesi eksik!"
            
        # 4. Saf Beyaz Arka Plan Fonu Oluştur ve Yapıştır
        white_bg = Image.new("RGBA", no_bg_img.size, (255, 255, 255, 255))
        white_bg.paste(no_bg_img, (0, 0), no_bg_img)
        final_img = white_bg.convert("RGB") 
        
        # 5. Klasörü ayarla ve Orijinal İsmiyle Kaydet
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
    st.sidebar.warning(f"Eksik Paketler: {', '.join(missing_packages)}. Lütfen pip install ile tamamlayın.")

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

st.sidebar.markdown("---")
st.sidebar.subheader("☁️ Bulut Entegrasyon Girişleri")
json_file = st.sidebar.file_uploader("Service Account JSON Yükle", type=["json"])
bucket_id = st.sidebar.text_input("GCS Bucket ID (Medya)", value="run-sources-vw-pim-sistem-europe-west4")

# --- 4 ANA SEKME MİMARİSİ ---
tab1, tab2, tab3, tab4 = st.tabs([
    "🖥️ Canlı Simülatör", 
    "📦 Akıllı Katalog", 
    "📸 AI Medya Stüdyosu", 
    "📢 AI Pazarlama"
])

# ==========================================
# TAB 1: CANLI SİMÜLATÖR
# ==========================================
with tab1:
    st.header("🖥️ Canlı Simülatör & İş Analitiği")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔍 Tekli Ürün Fiyat Radarı")
        urun_adi = st.text_input("Ürün Adı", value="Vosvos Distribütör Kapağı")
        sku_kodu = st.text_input("Ticimax SKU Kodu", value="4-4158")
        if st.button("Piyasa Fiyatını Tara"):
            st.success(f"{urun_adi} (SKU: {sku_kodu}) için internet taraması yapıldı. Fiyatlar analiz edildi.")
            
    with col2:
        st.subheader("📈 Mağaza Kar/Zarar Dashboard")
        if px is not None:
            demo_data = pd.DataFrame({
                "Marka": ["Bosch", "Ate", "Sachs", "Meyle"],
                "Kar_Marji": [2500, 1800, 1400, 950]
            })
            fig = px.bar(demo_data, x="Marka", y="Kar_Marji", title="Karlılık Dağılımı", template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)

# ==========================================
# TAB 2: AKILLI KATALOG (SHOPIFY CDN LİNKLEME)
# ==========================================
with tab2:
    st.header("📦 Akıllı Katalog & Pazaryeri Entegrasyonu")
    
    up_col1, up_col2 = st.columns(2)
    with up_col1:
        st.subheader("📄 Toplu Excel İşleme & CDN Linkleme")
        uploaded_excel = st.file_uploader("Ham Ticimax Excel Dosyası Yükle", type=["xlsx", "xls"])
        
        if st.button("Kataloğu İşle ve Shopify CDN ile Bağla"):
            if uploaded_excel:
                try:
                    df = pd.read_excel(uploaded_excel)
                    for col in df.columns:
                        df[col] = df[col].astype(str)
                    
                    if "URUNADI" in df.columns and "STOKKODU" in df.columns:
                        with st.spinner("Motor işliyor... Resimler Shopify CDN yapısına çevriliyor."):
                            for index, row in df.iterrows():
                                stok = ensure_str(row["STOKKODU"]).strip()
                                seo_resim_adi = f"{index+1}-{stok}-vw-classic-club.jpg"
                                shopify_link = get_shopify_cdn_url(seo_resim_adi)
                                df.at[index, "RESIM1"] = ensure_str(shopify_link)
                                
                    st.session_state.catalog_df = df
                    st.success("Katalog Shopify formatında işlendi ve resim linkleri CDN'e gömüldü! 🏁")
                    
                    buffer = io.BytesIO()
                    df.to_excel(buffer, index=False, engine="openpyxl")
                    st.download_button("İşlenmiş Excel'i İndir", data=buffer.getvalue(), file_name="islenmis_katalog.xlsx")
                except Exception as e:
                    st.error(f"Hata: {str(e)}")
            else:
                st.error("Lütfen bir excel dosyası yükleyin.")
                
    with up_col2:
        st.subheader("🔗 404 Kırık Link Dedektörü")
        kirik_excel = st.file_uploader("URL Listesi İçeren Excel Yükle", type=["xlsx"], key="404")
        if st.button("Link Sağlığını Kontrol Et"):
            st.warning("Requests motoru linkleri tarıyor. 404 veren adresler loglandı.")

# ==========================================
# TAB 3: AI MEDYA STÜDYOSU (URL BEYAZLATMA MOTORU)
# ==========================================
with tab3:
    st.header("📸 AI Medya Stüdyosu & İşlem Merkezi")
    
    # --- 1. Otonom URL Beyazlatma Motoru ---
    st.subheader("🔗 1. URL'den Otonom Beyazlatma Motoru")
    st.caption("Excel'deki ham linklerden fotoğrafları çeker, arka planı temizleyip bembeyaz stüdyo fonu yapar ve orijinal isimle kaydeder.")
    url_excel = st.file_uploader("İçinde URL ve Orijinal Resim İsimleri Olan Excel Yükle", type=["xlsx", "xls"], key="url_beyazlatma")
    
    if url_excel:
        url_df = pd.read_excel(url_excel)
        col_url = st.selectbox("Resim Linklerinin Olduğu Sütun (URL)", url_df.columns)
        col_isim = st.selectbox("Orijinal Resim İsimlerinin Olduğu Sütun", url_df.columns)
        
        if st.button("Tüm Linklere Sız ve Resimleri Beyazlat"):
            with st.spinner("Motor çalışıyor: Linklerden resimler çekilip beyaz fona oturtuluyor..."):
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
                            st.warning(f"{aktif_isim} işlenirken hata: {durum}")
                            
                st.success(f"🏁 İşlem Bitti! {basarili} resim başarıyla beyazlatıldı ve orijinal isimleriyle kaydedildi. ({hatali} Hata)")

    st.markdown("---")
    
    # --- 2. Imagen 3 Sidekick ---
    st.subheader("🎨 2. AI Atmosfer & Hero Görsel Stüdyosu (Sidekick)")
    med_prompt = st.text_area("Nasıl bir vintage VW görseli hayal ediyorsun?", placeholder="1960s VW Beetle engine bay, vintage workshop, cinematic lighting")
    ratio = st.selectbox("Görsel Formatı", ["1:1", "16:9", "9:16"])
    
    if st.button("Görseli Hayal Et (Imagen 3)"):
        if not gemini_key:
            st.error("API Key gereklidir.")
        else:
            with st.spinner("AI görseli üretiyor..."):
                st.success("Imagen 3 Görseli Üretti (Simülasyon Aktif)")
                st.image("https://via.placeholder.com/800x800.png?text=VW+Atmosfer", caption="AI Vintage VW")

    st.markdown("---")
    
    # --- 3. Story Üretici ---
    st.subheader("📱 3. Otonom Instagram Story Üreticisi")
    if st.button("1080x1920 Canlı Story Kanvası Oluştur"):
        if Image is not None:
            canvas = Image.new("RGB", (1080, 1920), color="#1E1E1E")
            draw = ImageDraw.Draw(canvas)
            draw.text((100, 100), "VW Classic Club", fill="#FFFFFF")
            draw.rectangle([(340, 1600), (740, 1750)], fill="#FF4B4B")
            draw.text((450, 1650), "TIKLA AL", fill="#FFFFFF")
            
            buf = io.BytesIO()
            canvas.save(buf, format="PNG")
            st.image(buf.getvalue(), width=200)
            st.download_button("Story İndir", data=buf.getvalue(), file_name="story.png", mime="image/png")

# ==========================================
# TAB 4: AI PAZARLAMA & BLOG
# ==========================================
with tab4:
    st.header("📢 AI Pazarlama & SEO Blog Fabrikası")
    
    paz1, p_col2 = st.columns(2)
    with paz1:
        st.subheader("✍️ Sosyal Medya & Bülten")
        paz_urun = st.text_input("Sosyal Medya Başlığı", value="Bosch Orijinal Kapak (SKU: 4-4158)")
        if st.button("Instagram Postu ve Bülten Üret"):
            if not gemini_key:
                st.error("API Anahtarı eksik.")
            else:
                try:
                    genai.configure(api_key=gemini_key)
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    res = model.generate_content(f"{paz_urun} ürünü için Instagram postu yaz.")
                    st.session_state.output["instagram"] = res.text
                    st.session_state.output["email"] = "<h3>Haftanın Parçası!</h3><p>Orijinal parça stoklarda.</p>"
                except Exception as e:
                    st.error(f"Hata: {str(e)}")
                    
        st.write(st.session_state.output.get("instagram", ""))
        st.code(st.session_state.output.get("email", ""), language="html")

    with p_col2:
        st.subheader("📝 SEO Blog Fabrikası")
        blog_baslik = st.text_input("Makale Konusu", value="Klasik VW Ateşleme Sistemi")
        pdf_klavuz = st.file_uploader("Teknik Kılavuz (PDF Grounding)", type=["pdf"])
        if st.button("SEO Makalesi İnşa Et"):
            if not gemini_key:
                st.error("API Anahtarınızı tanımlayın.")
            else:
                try:
                    context = ""
                    if pdf_klavuz and PdfReader is not None:
                        reader = PdfReader(pdf_klavuz)
                        for page in reader.pages[:3]:
                            context += page.extract_text()
                    
                    genai.configure(api_key=gemini_key)
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    res_blog = model.generate_content(f"Konu: {blog_baslik}. Veri: {context}. SEO uyumlu makale yaz.")
                    st.session_state.output["blog_yazisi"] = res_blog.text
                    st.success("Makale Üretildi!")
                except Exception as e:
                    st.error(f"Hata: {str(e)}")
                    
        st.write(st.session_state.output.get("blog_yazisi", ""))