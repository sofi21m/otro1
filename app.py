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

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="OCR & Traductor de Voz",
    page_icon="📷",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Si Tesseract no está en el PATH del sistema (por ejemplo, en Windows), especifica su ruta aquí:
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Creación de carpetas necesarias
os.makedirs("temp", exist_ok=True)

# --- FUNCIONES DE APOYO ---
def cleanup_temp_files(days=7):
    """Elimina archivos de audio antiguos."""
    mp3_files = glob.glob("temp/*.mp3")
    now = time.time()
    threshold = days * 86400
    for f in mp3_files:
        if os.stat(f).st_mtime < now - threshold:
            try:
                os.remove(f)
            except Exception as e:
                pass

cleanup_temp_files(7)

def extract_text_from_image(image_np):
    """Extrae texto de una imagen en formato NumPy array."""
    img_rgb = cv2.cvtColor(image_np, cv2.COLOR_BGR2RGB)
    text = pytesseract.image_to_string(img_rgb)
    return text.strip()

def generate_audio(text, src_lang, dest_lang, tld):
    """Traduce el texto y genera un archivo MP3."""
    translator = Translator()
    translation = translator.translate(text, src=src_lang, dest=dest_lang)
    trans_text = translation.text
    
    # Nombre de archivo único usando UUID para evitar problemas con caracteres especiales
    unique_id = uuid.uuid4().hex[:8]
    filename = f"audio_{unique_id}.mp3"
    filepath = os.path.join("temp", filename)
    
    tts = gTTS(text=trans_text, lang=dest_lang, tld=tld, slow=False)
    tts.save(filepath)
    
    return filepath, trans_text

# Inicializar estado de sesión
if "extracted_text" not in st.session_state:
    st.session_state["extracted_text"] = ""

# --- BARRA LATERAL (CONFIGURACIÓN) ---
with st.sidebar:
    st.header("⚙️ Configuración")
    
    st.subheader("1. Procesamiento de Imagen")
    filtro_cam = st.radio(
        "Filtro para foto de Cámara",
        ("Sin Filtro", "Invertir Colores (Negativo)"),
        help="Aplica un filtro simple si la iluminación o contraste dificultan la lectura."
    )

    st.markdown("---")
    st.subheader("2. Idiomas y Voz")
    
    lang_map = {
        "Español": "es",
        "Inglés": "en",
        "Bengalí": "bn",
        "Coreano": "ko",
        "Mandarín": "zh-cn",
        "Japonés": "ja"
    }
    
    in_lang_label = st.selectbox("Idioma de origen (OCR/Texto)", list(lang_map.keys()), index=0)
    input_language = lang_map[in_lang_label]

    out_lang_label = st.selectbox("Idioma de destino (Traducción)", list(lang_map.keys()), index=1)
    output_language = lang_map[out_lang_label]

    accents = {
        "Predeterminado": "com",
        "Estados Unidos": "com",
        "Reino Unido": "co.uk",
        "India": "co.in",
        "Canadá": "ca",
        "Australia": "com.au",
        "Irlanda": "ie",
        "Sudáfrica": "co.za"
    }
    english_accent = st.selectbox("Acento de Voz", list(accents.keys()))
    tld = accents[english_accent]

# --- CUERPO PRINCIPAL ---
st.title("🔍 OCR & Reader de Texto a Voz")
st.caption("Extrae texto de tus imágenes o cámara, tradúcelo y escúchalo en tiempo real.")

tab1, tab2 = st.tabs(["📷 Capturar / Cargar Imagen", "🔊 Traducción y Audio"])

with tab1:
    col1, col2 = st.columns([1, 1], gap="large")
    
    with col1:
        st.subheader("Entrada de Imagen")
        use_camera = st.toggle("Usar cámara web", value=False)
        
        img_np = None
        
        if use_camera:
            img_buffer = st.camera_input("Toma una fotografía")
            if img_buffer is not None:
                bytes_data = img_buffer.getvalue()
                img_np = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
                if filtro_cam == "Invertir Colores (Negativo)":
                    img_np = cv2.bitwise_not(img_np)
        else:
            uploaded_file = st.file_uploader("Selecciona una imagen (PNG, JPG, JPEG)", type=["png", "jpg", "jpeg"])
            if uploaded_file is not None:
                file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
                img_np = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                st.image(img_np, channels="BGR", caption="Imagen cargada", use_container_width=True)

        if img_np is not None:
            if st.button("🚀 Extraer Texto de la Imagen", type="primary"):
                with st.spinner("Procesando la imagen con OCR..."):
                    extracted = extract_text_from_image(img_np)
                    st.session_state["extracted_text"] = extracted
                    if extracted:
                        st.success("¡Texto extraído correctamente!")
                    else:
                        st.warning("No se detectó texto legible en la imagen.")

    with col2:
        st.subheader("Texto Detectado")
        text_area_content = st.text_area(
            "Puedes editar el texto extraído antes de traducirlo:",
            value=st.session_state["extracted_text"],
            height=280
        )
        st.session_state["extracted_text"] = text_area_content

with tab2:
    st.subheader("Generación de Audio y Traducción")
    
    current_text = st.session_state["extracted_text"]
    
    if not current_text.strip():
        st.info("💡 Primero carga una imagen con texto o escribe algo en el cuadro de texto para comenzar.")
    else:
        st.markdown("**Texto a procesar:**")
        st.info(current_text)
        
        show_translated_text = st.checkbox("Mostrar texto traducido", value=True)
        
        if st.button("🎧 Traducir y Generar Audio", type="primary"):
            with st.spinner("Traduciendo y generando voz..."):
                try:
                    audio_path, translated_text = generate_audio(
                        current_text, input_language, output_language, tld
                    )
                    
                    st.success("¡Audio generado con éxito!")
                    
                    if show_translated_text:
                        st.markdown("### 📝 Texto Traducido:")
                        st.write(translated_text)
                        
                    st.markdown("### 🔊 Reproductor:")
                    with open(audio_path, "rb") as f:
                        audio_bytes = f.read()
                    st.audio(audio_bytes, format="audio/mp3")
                    
                except Exception as e:
                    st.error(f"Ocurrió un error al procesar el audio/traducción: {e}")

 
    
    
