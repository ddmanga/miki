from openai import OpenAI
from google import genai
from google.genai import types
from RealtimeSTT import AudioToTextRecorder
import re
import json
from dotenv import load_dotenv
import os

load_dotenv()

# OpenAI conservé uniquement pour la synthèse vocale (Gemma n'a pas de TTS)
openai_client = OpenAI(api_key=os.getenv("API_KEY"))

# Gemma 4 via l'API Gemini de Google
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL_GEMMA = "gemma-4-26b-a4b-it"  # bon compromis vitesse/qualité ; voir alternatives ci-dessous

STT_INITIAL_PROMPT = (
    "Appel au 115, numéro d'urgence pour personnes sans-abri. "
    "L'appelant épelle son nom et son prénom lettre par lettre. "
    "Vocabulaire attendu : nom, prénom, âge, sexe masculin ou féminin, "
    "seul ou accompagné, en danger, handicap, adresse, rue, quartier, arrondissement."
)

SYSTEM_PROMPT = """
1. ROLE :
Tu es MIKI, un assistant IA intégré au 115, le numéro d'aide d'urgence pour les sans-abris.
Tu sers de filtre entre les agents et les appelants.
Tu poses des questions à l'appelant puis renvoies les informations collectées à l'agent.

2. CONTEXTE :
Tu parles à des personnes sans abris en détresse.
Fais preuve d'empathie, de patience et de bienveillance.
Si tu n'es pas sûr d'une réponse, dis : je n'ai pas cette information, veuillez contacter un agent.

3. INFORMATIONS A COLLECTER :
nom, prenom, age, sexe, situation (seul ou accompagné, en danger ou non, handicapé ou non), adresse.

4. CONTRAINTES :
Quand un appelant te donne une informations tu lui redemande toujours si l'information que tu a est bonne 
exemple : (IA: Quel est votre prenom? , User: Louis, IA: Vous vous appelez louis c'est bien sa)
Pour le nom et prenom demande toujour a l'appelant d'epeller
Si l'information que tu a est fausse repose la question
Tu ne poses qu'une seule question à la fois.
Tu commences toujours par te présenter.
Tu commences toujours par demander la raison de l'appel.
Tu détectes la langue de l'appelant et réponds dans cette langue.
Si l'appelant te parle en anglais tu réponds en anglais.
Si l'appelant te parle en russe tu réponds en russe, etc..

5. FORMAT DE SORTIE :
Quand tu as collecté toutes les informations disponibles,
tu informes l'appelant que tu transmets sa fiche à un agent.
Puis tu génères UNIQUEMENT un bloc JSON entre les balises <FICHE> et </FICHE>.

Exemple exact à suivre :
<FICHE>{
    "nom": "DELFORGE",
    "prenom": "Louis",
    "age": "34",
    "sexe": "Masculin",
    "situation": "seul, pas en danger",
    "adresse": "Paris 11e"
}</FICHE>

Ne mets rien d'autre après la balise </FICHE>.
"""

fiches = []


def parser_fiche(text):

    fiche = {
        "nom": None,
        "age": None,
        "sexe": None,
        "situation": None,
        "adresse": None
    }

    match = re.search(r"<FICHE>(.*?)</FICHE>", text, re.DOTALL)

    if match:
        try:
            data = json.loads(match.group(1).strip())
            fiche.update(data)
            print("✅ Fiche enregistrée")
        except json.JSONDecodeError:
            print("JSON invalide")

    return fiche
def speak(text, recorder):
    text = re.sub(r"<FICHE>.*?</FICHE>", "", text, flags=re.DOTALL).strip()

    if not text:
        return

    recorder.set_microphone(False)

    try:
        audio = openai_client.audio.speech.create(
            model="tts-1",
            voice="nova",
            input=text
        )

        audio.stream_to_file("voice.mp3")
        os.system("afplay voice.mp3")

    finally:
        recorder.clear_audio_queue()  # vide tout résidu audio accumulé pendant le TTS
        recorder.set_microphone(True)

def listen(recorder):

    print("\n🎤 Parlez...")

    text = recorder.text()

    print(f"\n👤 {text}")

    return text


def miki():
    print("debut")
    recorder = AudioToTextRecorder(
        model="small",
        language="fr",
        early_transcription_on_silence=300,

        device="cpu",
        compute_type="int8",

        beam_size=8,

        initial_prompt=STT_INITIAL_PROMPT,

        silero_sensitivity=0.4,
        silero_deactivity_detection=True,
        post_speech_silence_duration=0.8,

        use_microphone=True,
    )
    print("fin")

    # Session de chat Gemma : l'historique est géré automatiquement par le SDK
    chat = gemini_client.chats.create(
        model=MODEL_GEMMA,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
        ),
    )

    fiche = None

    while True:

        user = listen(recorder)

        if user.lower() == "diouf":
            recorder.shutdown()
            return fiche

        response = ""

        print("\n🤖 ", end="", flush=True)

        for chunk in chat.send_message_stream(user):
            if chunk.text:
                print(chunk.text, end="", flush=True)
                response += chunk.text

        print()

        speak(response, recorder)

        fiche_tmp = parser_fiche(response)

        if any(fiche_tmp.values()):
            fiche = fiche_tmp
            fiches.append(fiche)


if __name__ == "__main__":

    fiche = miki()

    print("\n===== FICHE =====")
    print(fiche)