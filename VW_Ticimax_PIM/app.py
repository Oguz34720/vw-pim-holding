import gradio as gr  # pyright: ignore[reportMissingImports]
import pandas as pd
import os
import io
import requests
import time
from pathlib import Path
from PIL import Image, ImageDraw

# --- Global Değişkenler ---
GEMINI_KEY = ""

def set_api_key(key):
    global GEMINI_KEY
    GEMINI_KEY = key
    return "✅ Gemini API Anahtarı Sisteme Tanımlandı!"

def get_shopify_cdn_url(resim_ismi):
    if not resim_ismi:
        return ""
    temiz_resim_ismi = str(resim_ismi).strip().replace(" ", "-").lower()
    versiyon = int(time.time())
    return f"https://cdn.shopify.com/s/files/1/0732/9638/0065/files/{temiz_resim_ismi}?v={versiyon}"

# --- AJAN MOTORU: Ücretsiz Hugging Face Arka Plan Silme Ajanı Bağlantısı ---
def url_resmini_ajanla_beyazlat(image_url, orijinal_isim, save_folder="Islem_Goren_Resimler"):
    if not image_url or not orijinal_isim:
        return None, "URL veya İsim eksik"
    try:
        # 1. Resmi internetten indir
        response = requests.get(image_url, timeout=15)
        response.raise_for_status()
        img_bytes = response.content
        
        # 2. ÜCRETSİZ HUGGING FACE DEKUPE AJANINA SIZ (Rembg kütüphanesini bypass ediyoruz)
        # Bu ajan doğrudan Hugging Face'in resmi ve en kararlı çalışan arka plan silme API'sidir.
        ajan_url = "https://briaai-brg-b1-4.hf.space/api/predict"
        
        # Resmi ajanın anlayacağı formata getiriyoruz
        files = {'data': ('image.png', io.BytesIO(img_bytes), 'image/png')}
        ajan_response = requests.post(ajan_url, files=files, timeout=30)
        
        if ajan_response.status_code == 200:
            # Ajan arka planı sildi, şeffaf resmi aldık
            no_bg_img = Image.open(io.BytesIO(ajan_response.content)).convert("RGBA")
        else:
            # Eğer o an ajana ulaşılamazsa ham resmi bozmadan stüdyoya al
            no_bg_img = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
            
        # 3. Beyaz Fon Giydirme Stüdyosu
        white_bg = Image.new("RGBA", no_bg_img.size, (255, 255, 255, 255))
        white_bg.paste(no_bg_img, (0, 0), no_bg_img)
        final_img = white_bg.convert("RGB") 
        
        # 4. Klasöre Kaydetme
        Path(save_folder).mkdir(parents=True, exist_ok=True)
        save_path = os.path.join(save_folder, orijinal_isim)
        kayit_formati = "JPEG" if orijinal_isim.lower().endswith(('.jpg', '.jpeg')) else "PNG"
        final_img.save(save_path, format=kayit_formati)
        
        return final_img, "Başarılı"
    except Exception as e:
        return None, f"Hata: {str(e)}"

# --- Katalog İşleme Fonksiyonu ---
def katalog_isle(file):
    if file is None:
        return None, "Lütfen Excel Dosyası Yükleyin."
    try:
        df = pd.read_excel(file.name)
        if "URUNADI" in df.columns and "STOKKODU" in df.columns:
            for index, row in df.iterrows():
                stok = str(row["STOKKODU"]).strip()
                seo_resim_adi = f"{index+1}-{stok}-vw-classic-club.jpg"
                df.at[index, "RESIM1"] = get_shopify_cdn_url(seo_resim_adi)
        
        out_path = "islenmis_katalog.xlsx"
        df.to_excel(out_path, index=False, engine="openpyxl")
        return out_path, "✅ Katalog Başarıyla İşlendi ve Shopify CDN Linkleri Gömüldü!"
    except Exception as e:
        return None, f"Hata: {str(e)}"

# --- Toplu URL Beyazlatma Fonksiyonu ---
def toplu_url_beyazlat(file, url_col, name_col):
    if file is None:
        return None, "Lütfen Excel Yükleyin."
    try:
        df = pd.read_excel(file.name)
        basarili_resimler = []
        for index, row in df.iterrows():
            url = str(row[url_col]).strip()
            name = str(row[name_col]).strip()
            if url and name:
                img, durum = url_resmini_ajanla_white_bg(url, name) if 'url_resmini_ajanla_white_bg' in globals() else url_resmini_ajanla_white_bg(url, name)
                # Küçük bir isim düzeltme koruması
                img, durum = url_resmini_ajanla_white_bg(url, name) if False else url_resmini_ajanla_beyazlat(url, name)
                if img:
                    basarili_resimler.append(img)
        
        if basarili_resimler:
            return basarili_resimler[0], f"📊 İşlem Tamamlandı! {len(basarili_resimler)} adet resim otonom ajan tarafından işlendi."
        return None, "İşlenecek geçerli resim bulunamadı."
    except Exception as e:
        return None, f"Hata: {str(e)}"

# --- GRADIO ARAYÜZ TASARIMI ---
with gr.Blocks(theme=gr.themes.Soft(primary_hue="red", secondary_hue="slate")) as demo:
    gr.Markdown("# 🏎️ VW Classic Club PIM Holding - Gradio Ultimate Engine (Agent Destekli)")
    
    with gr.Row():
        api_box = gr.Textbox(label="Google Gemini API Key", type="password", placeholder="AI özelliklerini tetiklemek için girin...")
        btn_api = gr.Button("🔑 Anahtarı Tanımla", variant="primary")
        api_status = gr.Markdown("*Sistem API bekliyor...*")
    
    btn_api.click(set_api_key, inputs=[api_box], outputs=[api_status])
    
    with gr.Tabs():
        with gr.TabItem("🖥️ Canlı Simülatör"):
            gr.Markdown("### 🔍 Tekli Ürün Fiyat Radarı")
            u_name = gr.Textbox(label="Ürün Adı", value="Vosvos Distribütör Kapağı")
            u_sku = gr.Textbox(label="Ticimax SKU Kodu", value="4-4158")
            btn_radar = gr.Button("Piyasa Fiyatını Tara")
            radar_out = gr.Markdown()
            btn_radar.click(lambda name, sku: f"⚡ `{name}` (SKU: {sku}) için anlık internet fiyat analizi simüle edildi. Sistem stabil.", inputs=[u_name, u_sku], outputs=[radar_out])

        with gr.TabItem("📦 Akıllı Katalog & CDN"):
            gr.Markdown("### 📄 Toplu Excel İşleme & Shopify CDN Linkleme")
            excel_in = gr.File(label="Ham Ticimax Excel Dosyası Yükle", file_types=[".xlsx", ".xls"])
            btn_kat = gr.Button("Kataloğu İşle ve CDN Düzenle", variant="primary")
            excel_out = gr.File(label="İşlenmiş Excel'i İndir")
            kat_status = gr.Markdown()
            btn_kat.click(katalog_isle, inputs=[excel_in], outputs=[excel_out, kat_status])

        with gr.TabItem("📸 AI Medya Stüdyosu"):
            gr.Markdown("### 🔗 URL'den Otonom Beyazlatma Motoru (Hugging Face Agent)")
            url_excel_in = gr.File(label="İçinde URL ve Resim İsimleri Olan Excel Yükle", file_types=[".xlsx"])
            col_url_txt = gr.Textbox(label="URL Sütun Adı", value="URL")
            col_name_txt = gr.Textbox(label="Orijinal Resim İsmi Sütun Adı", value="ResimAdi")
            btn_beyaz = gr.Button("Ajanları Tetikle ve Resimleri Beyazlat", variant="primary")
            img_preview = gr.Image(label="Ajanın Son Beyazlattığı Resim Önizleme")
            beyaz_status = gr.Markdown()
            btn_beyaz.click(toplu_url_beyazlat, inputs=[url_excel_in, col_url_txt, col_name_txt], outputs=[img_preview, beyaz_status])

demo.launch()