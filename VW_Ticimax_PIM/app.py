import gradio as gr  # pyright: ignore[reportMissingImports]
import pandas as pd
import requests
import io
import os
import time
from pathlib import Path
from PIL import Image
import google.generativeai as genai  # pyright: ignore[reportMissingImports]

# --- Global Değişkenler ---
GEMINI_KEY = ""

def set_api_key(key):
    global GEMINI_KEY
    GEMINI_KEY = key
    if key:
        genai.configure(api_key=key)
        return "✅ Gemini ve Otonom Ajan Motoru Başarıyla Eşleşti!"
    return "❌ Lütfen geçerli bir anahtar girin."

def get_shopify_cdn_url(resim_ismi):
    if not resim_ismi:
        return ""
    temiz_resim_ismi = str(resim_ismi).strip().replace(" ", "-").lower()
    versiyon = int(time.time())
    return f"https://cdn.shopify.com/s/files/1/0732/9638/0065/files/{temiz_resim_ismi}?v={versiyon}"


# --- 🛠️ OTONOM RESİM BEYAZLATMA MOTORU ---
def url_resmini_beyazlat(image_url):
    ajan_url = "https://briaai-brg-b1-4.hf.space/api/predict"
    try:
        res = requests.get(image_url, timeout=15)
        res.raise_for_status()
        
        files = {'data': ('image.png', res.content, 'image/png')}
        ajan_res = requests.post(ajan_url, files=files, timeout=30)
        
        if ajan_res.status_code == 200:
            no_bg_img = Image.open(io.BytesIO(ajan_res.content)).convert("RGBA")
            white_bg = Image.new("RGBA", no_bg_img.size, (255, 255, 255, 255))
            white_bg.paste(no_bg_img, (0, 0), no_bg_img)
            final_img = white_bg.convert("RGB")
            
            Path("Ajan_Medyalari").mkdir(parents=True, exist_ok=True)
            save_path = "Ajan_Medyalari/son_islenen.jpg"
            final_img.save(save_path, format="JPEG")
            return "başarılı"
        return "meşgul"
    except Exception as e:
        return f"hata: {str(e)}"


# --- 🤖 MODEL TABANLI AJAN MERKEZİ (YENİ NESİL FLASH BEYİN) ---
def ajan_merkezi_calistir(görev_metni):
    global GEMINI_KEY
    if not GEMINI_KEY:
        return "🚨 Ustam önce yukarıdan 'Google Gemini API Key' anahtarını tanımlaman lazım ki ajan bilinci aktif olsun."
    if not görev_metni:
        return "Ustam, lütfen ajana bir görev verin."
        
    try:
        # 404 hatasını önlemek için yepyeni gemini-1.5-flash motoruna geçildi!
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        sistem_talimati = (
            "Sen VW Classic Club Holding'in kıdemli yapay zeka ajanısın. "
            "Kullanıcı senden bir linkteki resmi beyazlatmanı isterse, metnin içinden sadece URL'yi ayıkla ve "
            "cevap olarak sadece ve sadece 'ISLEM_TETIKLE: <URL>' şeklinde yaz. Başka hiçbir şey yazma. "
            "Eğer soru normal bir soruysa normal cevap ver."
        )
        
        response = model.generate_content(f"{sistem_talimati}\n\nKullanıcı Emri: {görev_metni}")
        cevap = response.text.strip()
        
        if "ISLEM_TETIKLE:" in cevap:
            url = cevap.split("ISLEM_TETIKLE:")[1].strip()
            durum = url_resmini_beyazlat(url)
            if durum == "başarılı":
                return f"🤖 Ajan Raporu:\nEmriniz anlaşıldı usta! Metinden '{url}' linkini ayıkladım, dekupe aracımı otonom olarak tetikledim ve resmi başarıyla stüdyo beyazına aldım! 🏎️"
            else:
                return f"🤖 Ajan Raporu:\nLink ayıklandı ama dekupe aracı şu an nazlanıyor. Durum: {durum}"
        
        return f"🤖 Ajan Cevabı:\n{cevap}"
    except Exception as e:
        return f"🚨 Ajan akıl yürütürken bir sorun yaşadı: {str(e)}"


# --- 📦 KATALOG İŞLEME FONKSİYONU ---
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


# --- 📸 TOPLU URL BEYAZLATMA FONKSİYONU ---
def toplu_url_beyazlat(file, url_col, name_col):
    if file is None:
        return None, "Lütfen Excel Yükleyin."
    try:
        df = pd.read_excel(file.name)
        basarili_sayisi = 0
        
        for index, row in df.iterrows():
            url = str(row[url_col]).strip()
            if url:
                durum = url_resmini_beyazlat(url)
                if durum == "başarılı":
                    basarili_sayisi += 1
        
        preview_path = "Ajan_Medyalari/son_islenen.jpg"
        if os.path.exists(preview_path):
            return preview_path, f"📊 İşlem Tamamlandı! {basarili_sayisi} adet resim otonom ajan tarafından dekupe edildi."
        return None, "İşlenecek geçerli resim bulunamadı."
    except Exception as e:
        return None, f"Hata: {str(e)}"


# --- 🎨 GRADIO ULTIMATE ARAYÜZ TASARIMI ---
with gr.Blocks(theme=gr.themes.Soft(primary_hue="red", secondary_hue="slate")) as demo:
    gr.Markdown("# 🏎️ VW Classic Club PIM Holding - Ultimate Gemini Agent AI Engine")
    
    with gr.Row():
        api_box = gr.Textbox(label="Google Gemini API Key", type="password", placeholder="Ajan bilincini aktif etmek için anahtarınızı girin...")
        btn_api = gr.Button("🔑 Ajanı Ateşle", variant="primary")
        api_status = gr.Markdown("*Sistem API bekliyor...*")
    
    btn_api.click(set_api_key, inputs=[api_box], outputs=[api_status])
    
    with gr.Tabs():
        with gr.TabItem("🤖 Ajan Komuta Odası"):
            gr.Markdown("### 🎯 Yapay Zeka Ajanına Doğrudan Türkçe Emir Ver")
            gorev_input = gr.Textbox(
                label="Ajanın Yapmasını İstediğiniz Görevi Yazın", 
                value="Şu linkteki arabanın arka planını temizle usta: https://images.unsplash.com/photo-1542282088-72c9c27ed0cd"
            )
            btn_ajan = gr.Button("🚀 Ajanı Operasyona Gönder", variant="primary")
            ajan_output = gr.Textbox(label="Ajanın Çalışma Günlüğü ve Sonuç Raporu", lines=10)
            btn_ajan.click(ajan_merkezi_calistir, inputs=[gorev_input], outputs=[ajan_output])

        with gr.TabItem("📦 Akıllı Katalog & CDN"):
            gr.Markdown("### 📄 Toplu Excel İşleme & Shopify CDN Linkleme")
            excel_in = gr.File(label="Ham Ticimax Excel Dosyası Yükle", file_types=[".xlsx", ".xls"])
            btn_kat = gr.Button("Kataloğu İşle ve CDN Düzenle", variant="primary")
            excel_out = gr.File(label="İşlenmiş Excel'i İndir")
            kat_status = gr.Markdown()
            btn_kat.click(katalog_isle, inputs=[excel_in], outputs=[excel_out, kat_status])

        with gr.TabItem("📸 AI Medya Stüdyosu"):
            gr.Markdown("### 🔗 Excel'deki Tüm URL'leri Otonom Ajanlarla Beyazlat")
            url_excel_in = gr.File(label="İçinde URL ve Resim İsimleri Olan Excel Yükle", file_types=[".xlsx"])
            col_url_txt = gr.Textbox(label="URL Sütun Adı", value="URL")
            col_name_txt = gr.Textbox(label="Orijinal Resim İsmi Sütun Adı", value="ResimAdi")
            btn_beyaz = gr.Button("Ajanları Tetikle ve Resimleri Beyazlat", variant="primary")
            img_preview = gr.Image(label="Son İşlenen Resmin Stüdyo Önizlemesi")
            beyaz_status = gr.Markdown()
            btn_beyaz.click(toplu_url_beyazlat, inputs=[url_excel_in, col_url_txt, col_name_txt], outputs=[img_preview, beyaz_status])

demo.launch()