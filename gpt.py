from openai import OpenAI
from RealtimeSTT import AudioToTextRecorder
import re
import json
from dotenv import load_dotenv
import os
import threading
import subprocess

load_dotenv()

client = OpenAI(api_key=os.getenv("API_KEY"))

STT_INITIAL_PROMPT = (
    "Appel au 115, numéro d'urgence pour personnes sans-abri. "
    "L'appelant épelle son nom et son prénom lettre par lettre. "
    "Vocabulaire attendu : nom, prénom, âge, sexe masculin ou féminin, "
    "seul ou accompagné, en danger, handicap, adresse, rue, quartier, arrondissement."
)

messages = [
    {
        "role": "system",
        "content": """
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
    }
]
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
        audio = client.audio.speech.create(
            model="tts-1",
            voice="nova",
            input=text
        )

        audio.stream_to_file("voice.mp3")

        process = subprocess.Popen(["afplay", "voice.mp3"])
        process.wait()

    finally:
        recorder.clear_audio_queue()
        recorder.set_microphone(True)

def listen(recorder):

    print("\n🎤 Parlez...")

    text = recorder.text()

    print(f"\n👤 {text}")

    return text


def miki():
    print("debut")
    recorder = AudioToTextRecorder(
        model="small",  # "medium" est nettement plus lent à transcrire sur CPU :
        # c'est très probablement la vraie cause de tes 13 secondes, pas le VAD.
        language="fr",

        device="cpu",
        compute_type="int8",

        beam_size=1,

        initial_prompt=STT_INITIAL_PROMPT,

        silero_sensitivity=0.3,
        silero_deactivity_detection=True,
        webrtc_sensitivity=3,
        post_speech_silence_duration=0.5,
        early_transcription_on_silence=300,

        print_transcription_time=True,  # affiche le temps réel pris par la transcription

        use_microphone=True,
    )
    print("fin")

    fiche = None

    while True:

        user = listen(recorder)

        if user.lower() == "diouf":
            recorder.shutdown()
            return fiche

        messages.append({
            "role": "user",
            "content": user
        })

        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            stream=True
        )

        response = ""

        print("\n🤖 ", end="", flush=True)

        for chunk in completion:

            delta = chunk.choices[0].delta.content

            if delta:
                print(delta, end="", flush=True)
                response += delta

        print()

        messages.append({
            "role": "assistant",
            "content": response
        })
        threading.Thread(
        target=speak,
        args=(response, recorder),
        daemon=True
        ).start()

        fiche_tmp = parser_fiche(response)

        if any(fiche_tmp.values()):
            fiche = fiche_tmp
            fiches.append(fiche)


if __name__ == "__main__":

    fiche = miki()

    print("\n===== FICHE =====")
    print(fiche)