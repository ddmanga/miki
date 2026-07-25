from openai import OpenAI
import re
import json
from dotenv import load_dotenv
import os

load_dotenv()

diouf = OpenAI(api_key=os.getenv("API_KEY"))

message = [
    {
        "role": "system",
        "content":
        "1. ROLE : "
        "Tu es MIKI, un assistant IA intégré au 115, le numéro d'aide d'urgence pour les sans-abris. "
        "Tu sers de filtre entre les agents et les appelants. "
        "Tu poses des questions à l'appelant puis renvoies les informations collectées à l'agent. "

        "2. CONTEXTE : "
        "Tu parles à des personnes sans abris en détresse. "
        "Fais preuve d'empathie, de patience et de bienveillance. "
        "Si tu n'es pas sûr d'une réponse, dis : je n'ai pas cette information, veuillez contacter un agent. "

        "3. INFORMATIONS A COLLECTER : "
        "nom, age, sexe, situation (seul ou accompagné, en danger ou non, handicapé ou non), adresse. "

        "4. CONTRAINTES : "
        "Tu ne poses qu'une seule question à la fois. "
        "Tu commences toujours par te présenter. "
        "Tu commences toujours par demander la raison de l'appel. "
        "Si l'appelant refuse de donner une information, tu n'insistes pas. "
        "Tu détectes la langue de l'appelant et réponds dans cette langue. "
        "Si l'appelant te parle en anglais tu repond en anglais si il te parle en russe tu repond en russe ect.."

        "5. FORMAT DE SORTIE : "
        "Quand tu as collecté toutes les informations disponibles, "
        "tu informes l'appelant que tu transmets sa fiche à un agent. "
        "Puis tu génères UNIQUEMENT un bloc JSON entre les balises <FICHE> et </FICHE>. "
        "Exemple exact à suivre : "
        "<FICHE>{\"nom\": \"Jean\", \"age\": \"34\", \"sexe\": \"Masculin\", "
        "\"situation\": \"seul, pas en danger\", \"adresse\": \"Paris 11e\"}</FICHE> "
        "Ne mets rien d'autre après la balise </FICHE>."
    }
]

fiches = []

def parser_fiche(texte_ia):
    fiche = {
        "nom": None,
        "age": None,
        "sexe": None,
        "situation": None,
        "adresse": None
    }

    match = re.search(r"<FICHE>(.*?)</FICHE>", texte_ia, re.DOTALL)

    if match:
        try:
            data = json.loads(match.group(1).strip())
            fiche.update(data)
            print(" Fiche parsée avec succès")
        except json.JSONDecodeError:
            print("[ERREUR] JSON mal formé")
            print("[DEBUG]", match.group(1))

    return fiche


def speak(text):
    text = re.sub(r"<FICHE>.*?</FICHE>", "", text, flags=re.DOTALL).strip()

    if not text:
        return

    audio = diouf.audio.speech.create(
        model="tts-1",
        voice="nova",
        input=text
    )

    audio.stream_to_file("voice.mp3")
    os.system("afplay voice.mp3")
def miki():
    print("Tape 'diouf' pour quitter\n")
    fiche = None

    while True:
        user = input("User: ")

        if user.lower() == "diouf":
            return fiche

        message.append({
            "role": "user",
            "content": user
        })

        completion = diouf.chat.completions.create(
            model="gpt-4o-mini",
            messages=message,
            stream=True
        )

        ai_resp = ""

        print("IA: ", end="", flush=True)

        for chunk in completion:
            delta = chunk.choices[0].delta.content

            if delta:
                print(delta, end="", flush=True)
                ai_resp += delta

        print("\n")

        message.append({
            "role": "assistant",
            "content": ai_resp
        })

        speak(ai_resp)

        fiche_tentative = parser_fiche(ai_resp)

        if any(fiche_tentative.values()):
            fiche = fiche_tentative
            fiches.append(fiche)

if __name__ == "__main__":
    fiche = miki()

    print("\n--- FICHE FINALE ---")
    print(fiche)