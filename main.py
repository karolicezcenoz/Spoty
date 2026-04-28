import os
import re
from flask import Flask, render_template, request, jsonify, session
from groq import Groq
from dotenv import load_dotenv

# -----------------------------
# CONFIGURACIÓN INICIAL
# -----------------------------

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev_key_inseguro")

# -----------------------------
# FUNCIONES CORE
# -----------------------------

def cargar_api_key():
    load_dotenv()
    api_key = os.environ.get("GROQ_API_KEY")

    if not api_key:
        raise ValueError("❌ API KEY no encontrada en .env")

    return api_key


def crear_cliente_groq(api_key):
    return Groq(api_key=api_key)

# -----------------------------
# LIMPIADOR DE TEXTO (IMPORTANTE)
# -----------------------------

def limpiar_respuesta(texto):
    """
    Elimina Markdown y formatos raros de la IA
    """
    texto = re.sub(r"\*\*(.*?)\*\*", r"\1", texto)  # negrita
    texto = re.sub(r"\*(.*?)\*", r"\1", texto)      # cursiva
    texto = texto.replace("#", "")                 # headers
    return texto

# -----------------------------
# PERSONALIDAD DE LA IA (SPOTY)
# -----------------------------

def obtener_prompt_personalidad():
    return """
Eres "Spoty", un DJ y asistente musical inteligente.

IDENTIDAD:
- Eres experto en música global
- Conoces pop, rap, electrónica, rock, indie y K-pop
- Tu objetivo es recomendar música según el mood del usuario

COMPORTAMIENTO:
- Detectas el estado de ánimo o intención del usuario
- Recomiendas canciones reales y conocidas
- Siempre das playlists rápidas (3 a 5 canciones)
- Puedes mezclar géneros si encaja

MOODS:
- gym / entrenamiento → música energética
- chill / relajación → música suave
- fiesta / party → música bailable
- triste / sad → música emocional
- kpop → solo si el usuario lo pide o lo menciona

K-POP:
- Es un género más dentro de la música global
- Puedes recomendar BTS, BLACKPINK, Stray Kids, NewJeans, etc.
- No lo priorices salvo que el usuario lo indique

ESTILO:
- Cercano, natural y con energía 🎧🔥
- Respuestas cortas
- Formato tipo playlist

FORMATO OBLIGATORIO:
Playlist:
- Canción – Artista → breve explicación
- Canción – Artista → breve explicación

REGLAS:
- Nada de respuestas genéricas
- Siempre ejemplos concretos
- No uses asteriscos ni Markdown
- No hables como robot
"""

def detectar_modo(mensaje):
    m = mensaje.lower()

    if "gym" in m or "entrenar" in m:
        return "gym"
    if "chill" in m or "relajar" in m:
        return "chill"
    if "fiesta" in m:
        return "party"
    if "sad" in m or "triste" in m:
        return "sad"
    if "kpop" in m or "k-pop" in m:
        return "kpop_context"

    return "normal"


def obtener_respuesta_ia(cliente, historial):
    try:
        response = cliente.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=historial,
            temperature=0.8,
            max_tokens=700
        )

        texto = response.choices[0].message.content
        return limpiar_respuesta(texto)

    except Exception as e:
        return f"⚠️ Error IA: {str(e)}"


# -----------------------------
# RUTAS
# -----------------------------

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        mensaje_usuario = data.get("mensaje")

        if not mensaje_usuario:
            return jsonify({"error": "Mensaje vacío"}), 400

        # -------------------------
        # HISTORIAL
        # -------------------------
        if "historial" not in session:
            session["historial"] = [
                {"role": "system", "content": obtener_prompt_personalidad()}
            ]

        historial = session["historial"]

        modo = detectar_modo(mensaje_usuario)

        contexto_extra = f"""
CONTEXTO:
- Modo detectado: {modo}
- Usuario pide música personalizada

INSTRUCCIONES:
- Devuelve playlist de 3 a 5 canciones
- Adapta todo al mood
- Mezcla géneros si encaja
- K-pop solo si el usuario lo menciona
- NO uses asteriscos ni Markdown
"""

        historial[0]["content"] = obtener_prompt_personalidad() + contexto_extra

        historial.append({
            "role": "user",
            "content": mensaje_usuario
        })

        api_key = cargar_api_key()
        cliente = crear_cliente_groq(api_key)

        respuesta_ia = obtener_respuesta_ia(cliente, historial)

        historial.append({
            "role": "assistant",
            "content": respuesta_ia
        })

        session["historial"] = historial

        return jsonify({"respuesta": respuesta_ia})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/reset", methods=["POST"])
def reset_chat():
    session.pop("historial", None)
    return jsonify({"mensaje": "Chat reiniciado"})


# -----------------------------
# MAIN
# -----------------------------

def main():
    print("🚀 Servidor corriendo en http://127.0.0.1:5001")
    app.run(host="0.0.0.0", port=5001, debug=True, use_reloader=False)


if __name__ == "__main__":
    main()