import os
import time
import glob
import uuid
import cv2
import numpy as np
import pytesseract
from PIL import Image
from gtts import gTTS
from googletrans import Translator
import streamlit as st

# --- CONFIGURACIÓN Y ESTILOS ---
st.set_page_config(
    page_title="Studio OCR & Voice",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Crear directorio temporal si no existe
os.makedirs("temp", exist_ok=True)

# Limpieza de archivos temporales
def cleanup_temp_files(days=1):
    mp3_files = glob.glob("temp/*.mp3")
    now = time.time()
    threshold = days * 86400
    for f in mp3_files:
        if os.stat(f).st_mtime < now - threshold:
            try:
                os.remove(f)
            except Exception:
                pass

cleanup_temp_files(1)

# Inicializar sesión para persisencia de texto
if "ocr_text" not in st.session_state:
    st.session_state["ocr_text"] = ""
if "translated_text" not in st.session_state:
    st.session_state["translated_text"] = ""
if "audio_path" not in st.session_state:
    st.session_state["audio_path"] = None

# Mapeo de Idiomas
LANGUAGES = {
    "Español 🇪🇸": "es",
    "Inglés 🇺🇸": "en",
    "Japonés 🇯🇵": "ja",
    "Coreano 🇰🇷": "ko",
    "Mandarín 🇨🇳": "zh-cn",
    "Bengalí 🇧🇩": "bn"
}

ACCENTS = {
    "Predeterminado": "com",
    "Estados Unidos": "com",
    "Reino Unido": "co.uk",
    "India": "co.in",
    "Canadá": "ca",
    "Australia": "com.au"
}

# --- BARRA LATERAL (OPCIONES TÉCNICAS) ---
with st.sidebar:
    st.title("⚙️ Ajustes de Procesamiento")
    apply_filter = st.checkbox("Aplicar filtro de inversión (Negativo)")
    accent_choice = st.selectbox("Acento de Voz (Inglés)", list(ACCENTS.keys()))
    tld = ACCENTS[accent_choice]
    
    st.divider()
    if st.button("🗑️ Limpiar Todo", use_container_width=True):
        st.session_state["ocr_text"] = ""
        st.session_state["translated_text"] = ""
        st.session_state["audio_path"] = None
        st.rerun()

# --- HEADER PRINCIPAL ---
st.title("⚡ OCR & Reader Studio")
st.caption("Transforma imágenes en texto escaneado, tradúcelo y escúchalo al instante.")
st.divider()

# --- PASO 1 Y 2: ENTRADA Y RECONOCIMIENTO (GRID DE 2 COLUMNAS) ---
col_left, col_right = st.columns([1, 1], gap="medium")

with col_left:
    with st.container(border=True):
        st.subheader("1. Captura de Imagen")
        
        # Selector de modo de entrada
        source_mode = st.radio(
            "Selecciona la fuente de la imagen:",
            ["📁 Cargar Archivo", "📷 Usar Cámara Web"],
            horizontal=True,
            label_visibility="collapsed"
        )
        
        img_np = None
        
        if "Cargar Archivo" in source_mode:
            uploaded = st.file_uploader("Arrastra tu imagen o explora", type=["png", "jpg", "jpeg"])
            if uploaded:
                file_bytes = np.asarray(bytearray(uploaded.read()), dtype=np.uint8)
                img_np = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                st.image(img_np, channels="BGR", use_container_width=True)
        else:
            cam_buffer = st.camera_input("Toma una fotografía")
            if cam_buffer:
                bytes_data = cam_buffer.getvalue()
                img_np = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
                if apply_filter:
                    img_np = cv2.bitwise_not(img_np)

        # Botón de extracción
        if img_np is not None:
            if st.button("🔍 Escanear Texto con OCR", type="primary", use_container_width=True):
                with st.spinner("Procesando imagen con Tesseract..."):
                    img_rgb = cv2.cvtColor(img_np, cv2.COLOR_BGR2RGB)
                    extracted = pytesseract.image_to_string(img_rgb).strip()
                    st.session_state["ocr_text"] = extracted
                    if extracted:
                        st.toast("¡Texto detectado exitosamente!", icon="✅")
                    else:
                        st.toast("No se detectó texto legíble", icon="⚠️")

with col_right:
    with st.container(border=True):
        st.subheader("2. Texto Detectado / Editor")
        
        # Muestra la cantidad de palabras detectadas si hay texto
        words_count = len(st.session_state["ocr_text"].split()) if st.session_state["ocr_text"] else 0
        st.metric(label="Palabras extraídas", value=words_count)
        
        # Editor interactivo
        edited_text = st.text_area(
            "Texto escaneado (puedes corregirlo manualmente si es necesario):",
            value=st.session_state["ocr_text"],
            height=235,
            placeholder="El texto extraído de la imagen aparecerá aquí..."
        )
        st.session_state["ocr_text"] = edited_text

# --- PASO 3: TRADUCCIÓN Y AUDIO (PANEL INFERIOR TIPO TARJETA ANCHA) ---
st.write("")
with st.container(border=True):
    st.subheader("3. Traducción y Reproducción de Voz")
    
    c1, c2, c3 = st.columns([1, 1, 1], gap="medium")
    
    with c1:
        src_lang_label = st.selectbox("Idioma Origen", list(LANGUAGES.keys()), index=0)
    with c2:
        dest_lang_label = st.selectbox("Idioma Destino", list(LANGUAGES.keys()), index=1)
    with c3:
        st.write(" ") # Espaciador
        st.write(" ")
        btn_translate = st.button("🎧 Traducir & Generar Voz", type="primary", use_container_width=True)

    if btn_translate:
        text_to_process = st.session_state["ocr_text"]
        
        if not text_to_process.strip():
            st.warning("⚠️️ Primero debes escanear una imagen o escribir algún texto arriba.")
        else:
            with st.spinner("Generando traducción y archivo de voz..."):
                try:
                    src_code = LANGUAGES[src_lang_label]
                    dest_code = LANGUAGES[dest_lang_label]
                    
                    translator = Translator()
                    translated = translator.translate(text_to_process, src=src_code, dest=dest_code).text
                    st.session_state["translated_text"] = translated
                    
                    # Generar audio
                    audio_filename = f"audio_{uuid.uuid4().hex[:8]}.mp3"
                    audio_filepath = os.path.join("temp", audio_filename)
                    
                    tts = gTTS(text=translated, lang=dest_code, tld=tld, slow=False)
                    tts.save(audio_filepath)
                    st.session_state["audio_path"] = audio_filepath
                    
                    st.toast("¡Audio listo!", icon="🎉")
                except Exception as e:
                    st.error(f"Error durante el procesamiento: {e}")

    # Resultados si ya se procesó
    if st.session_state["translated_text"] or st.session_state["audio_path"]:
        st.divider()
        res_col1, res_col2 = st.columns([1, 1], gap="medium")
        
        with res_col1:
            st.markdown("**Traducción Resultante:**")
            st.info(st.session_state["translated_text"])
            
        with res_col2:
            st.markdown("**Reproductor de Audio:**")
            if st.session_state["audio_path"] and os.path.exists(st.session_state["audio_path"]):
                with open(st.session_state["audio_path"], "rb") as f:
                    st.audio(f.read(), format="audio/mp3")
