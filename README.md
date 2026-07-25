# MIKI — Assistant vocal IA pour le 115

MIKI est un assistant vocal conçu pour le 115 (numéro d'urgence pour les personnes sans-abri). Il sert de filtre entre les appelants et les agents : il répond au téléphone, pose les questions nécessaires à la prise en charge, puis transmet une fiche structurée aux agents via une interface web dédiée.

## Fonctionnalités

- **Conversation vocale en temps réel** : transcription de la voix de l'appelant (RealtimeSTT / Whisper), génération de réponse par IA (OpenAI GPT-4o-mini), synthèse vocale de la réponse (OpenAI TTS)
- **Extraction automatique des informations** : nom, prénom, âge, sexe, situation, adresse, collectés au fil de la conversation et structurés en JSON
- **Interface agents en temps réel** : dashboard web affichant les dossiers reçus, avec code couleur par niveau d'urgence, consultable en direct pendant que les appels se déroulent
- **Filtrage des hallucinations** : détection des transcriptions parasites générées par Whisper sur du silence/bruit de fond
- **Résilience réseau** : nouvelle tentative automatique en cas d'erreur serveur ponctuelle (OpenAI)

## Architecture

```
Appelant (voix)
     │
     ▼
RealtimeSTT (Whisper) ──► Transcription texte
     │
     ▼
OpenAI GPT-4o-mini ──► Réponse + extraction de fiche
     │
     ├──► OpenAI TTS ──► Réponse vocale à l'appelant
     │
     └──► Serveur Flask ──► Interface web agents (temps réel)
```

Le serveur web (Flask) et l'assistant vocal tournent dans le même process, sur deux threads séparés : l'un ne bloque pas l'autre.

## Prérequis

- Python 3.9 ou plus récent
- macOS (le script utilise `afplay` pour la lecture audio ; à adapter pour Linux/Windows)
- Une clé API OpenAI

## Installation

```bash
# Cloner ou récupérer le projet, puis se placer dans le dossier
cd mikiAI

# Créer et activer un environnement virtuel
python3 -m venv venv
source venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt
```

## Configuration

Crée un fichier `.env` à la racine du projet (au même niveau que `miki.py`) :

```
API_KEY=ta_clé_api_openai
```

⚠️ Ne partage jamais ce fichier ni son contenu (dépôt Git, message, capture d'écran) — une clé API exposée doit être révoquée et régénérée immédiatement.

## Structure du projet

```
mikiAI/
├── miki.py              # Script principal (assistant vocal + serveur web)
├── requirements.txt      # Dépendances Python
├── .env                   # Clés API (à créer, jamais versionné)
└── templates/
    └── index.html         # Interface web agents
```

## Lancer le projet

```bash
source venv/bin/activate
python3 miki.py
```

Au démarrage, le script :
1. lance le serveur web en arrière-plan (`http://localhost:5000`)
2. initialise le micro et le modèle de transcription
3. attend que tu parles (`🎤 Parlez...`)

### Accéder à l'interface agents

- **Sur la même machine** : ouvre `http://localhost:5000` dans un navigateur
- **Depuis un autre poste du réseau local** : récupère l'IP locale de la machine (`ipconfig getifaddr en0` sur macOS) et ouvre `http://<IP>:5000`

L'interface se met à jour automatiquement toutes les 3 secondes, sans rechargement manuel.

### Terminer une conversation

Dis **« Diouf »** à voix haute pour mettre fin à l'appel en cours et arrêter proprement l'enregistrement.

## Personnalisation

| Paramètre | Où | Effet |
|---|---|---|
| `model` (RealtimeSTT) | `miki.py` | Taille du modèle Whisper (`tiny`, `small`, `medium`...) — plus gros = plus précis mais plus lent |
| `silero_sensitivity` | `miki.py` | Sensibilité de détection de la voix — plus bas = moins sensible au bruit de fond |
| `post_speech_silence_duration` | `miki.py` | Durée de silence avant de considérer que l'appelant a fini de parler |
| `HALLUCINATIONS_CONNUES` | `miki.py` | Liste des phrases parasites à ignorer si générées par erreur |
| Palette de couleurs / textes | `templates/index.html` | Apparence de l'interface agents |

## Dépannage rapide

- **Le son ne joue pas** : vérifie que la commande shell utilisée est bien `afplay` (macOS uniquement)
- **`ModuleNotFoundError`** : la venv n'est pas activée, ou les dépendances n'ont pas été installées — relance `pip install -r requirements.txt`
- **Erreur 500 OpenAI** : incident temporaire côté serveur OpenAI, généralement résolu par une nouvelle tentative (le script réessaie automatiquement)
- **L'interface web n'affiche rien** : vérifie que `miki.py` tourne toujours dans le terminal, et que le dossier `templates/` est bien au même niveau que `miki.py`
- **Transcription qui hallucine** (phrases du type « sous-titres par la communauté ») : ajoute la phrase concernée à `HALLUCINATIONS_CONNUES`

## Limitations connues

- Fonctionne actuellement pour un seul appel à la fois (pas de gestion de plusieurs conversations simultanées)
- Les dossiers sont stockés en mémoire : ils sont perdus si le script est redémarré (pas de base de données persistante)
- Testé sur macOS uniquement

LIEN:
https://youtube.com/shorts/0sY8w372ZbM+++
