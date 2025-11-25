# VoiceVibe4

Application macOS native pour la performance visuelle en temps réel. VoiceVibe4 agit comme un "cerveau" qui écoute le microphone, transcrit en temps réel avec Moshi, analyse le texte avec un LLM local (Ollama), et envoie des prompts visuels via OSC vers un PC distant.

## 🎯 Fonctionnalités

- **Capture audio en temps réel** via microphone (sounddevice)
- **Transcription temps réel** avec Moshi (Kyutai) optimisé Apple Silicon
- **Analyse intelligente** du texte avec Ollama (qwen2.5)
- **Génération de prompts visuels** pour SDXL
- **Communication OSC** vers un PC distant sur le réseau
- **Interface moderne** avec customtkinter

## 📋 Prérequis

- macOS (Apple Silicon M1/M2/M3 recommandé)
- Python 3.9+
- Ollama installé et configuré avec le modèle `qwen2.5`
- Moshi installé (voir section Installation)

## 🚀 Installation

### 1. Cloner le dépôt

```bash
git clone https://github.com/Studio-Carlos/VoceVibe4.git
cd VoceVibe4
```

### 2. Créer un environnement virtuel

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Installer Moshi

**Note:** L'intégration Moshi nécessite l'installation du package approprié. Consultez la documentation officielle de Moshi pour l'installation sur macOS.

```bash
# Exemple (à ajuster selon la documentation officielle)
# pip install moshi-python
# ou
# pip install git+https://github.com/kyutai/moshi.git
```

### 5. Configurer Ollama

Assurez-vous qu'Ollama est installé et que le modèle `qwen2.5` est disponible :

```bash
# Installer Ollama (si pas déjà fait)
# brew install ollama

# Télécharger le modèle
ollama pull qwen2.5

# Vérifier que le modèle est disponible
ollama list
```

### 6. Configuration

Copiez le fichier `.env.example` vers `.env` et ajustez les valeurs :

```bash
cp .env.example .env
```

Éditez `.env` avec vos paramètres (IP du PC cible, port OSC, etc.).

## 🎮 Utilisation

### Lancer l'application

```bash
python main.py
```

### Interface

1. **Configuration OSC** : Entrez l'IP et le port du PC cible recevant les messages OSC
2. **Cliquez sur START** : Démarre la capture audio et l'analyse
3. **Parlez dans le microphone** : Le texte est transcrit et analysé
4. **Consultez les logs** : La console affiche les transcriptions et les prompts générés
5. **Cliquez sur STOP** : Arrête proprement tous les processus

## 🏗️ Architecture

```
VoceVibe4/
├── src/
│   ├── __init__.py
│   ├── config.py          # Gestion de la configuration
│   ├── osc_client.py      # Client OSC thread-safe
│   ├── audio_engine.py    # Thread audio + Moshi
│   └── brain_engine.py    # Thread LLM + OSC
├── main.py                # Point d'entrée + UI
├── requirements.txt       # Dépendances Python
├── .env.example          # Template de configuration
└── README.md             # Documentation
```

### Flux de données

1. **AudioEngine** capture l'audio du microphone
2. Moshi transcrit l'audio en texte en temps réel
3. Le texte est ajouté à une queue thread-safe
4. **BrainEngine** collecte le texte toutes les 6-8 secondes
5. Ollama analyse le texte et génère un prompt visuel (JSON)
6. Le prompt est envoyé via OSC au PC distant

## ⚙️ Configuration

Les paramètres sont configurables via le fichier `.env` :

- `OSC_TARGET_IP` : IP du PC cible (par défaut: 127.0.0.1)
- `OSC_TARGET_PORT` : Port OSC (par défaut: 5005)
- `OLLAMA_MODEL` : Modèle Ollama à utiliser (par défaut: qwen2.5)
- `BRAIN_ANALYSIS_INTERVAL` : Intervalle d'analyse en secondes (par défaut: 6.0)

## 🔧 Développement

### Structure du code

- **Clean Architecture** : Code modulaire dans `src/`
- **Threading** : AudioEngine et BrainEngine s'exécutent dans des threads séparés
- **Thread-safe** : Communication via `queue.Queue`
- **Configuration centralisée** : Singleton Config avec support dotenv

### Format OSC

Les messages OSC sont envoyés aux adresses suivantes :

- `/visual/prompt` : Le prompt visuel (string)
- `/visual/style` : Le style artistique (string)
- `/visual/mood` : L'ambiance émotionnelle (string)
- `/visual/json` : JSON complet avec toutes les données

## 📝 Notes

- **Moshi** : L'intégration actuelle est un placeholder. Ajustez `src/audio_engine.py` selon l'API réelle de Moshi.
- **Performance** : Optimisé pour Apple Silicon (MPS). Assurez-vous que PyTorch utilise MPS.
- **Réseau** : Vérifiez que le firewall autorise les connexions UDP sur le port OSC.

## 🐛 Dépannage

### Ollama ne répond pas

- Vérifiez qu'Ollama est démarré : `ollama serve`
- Vérifiez que le modèle est installé : `ollama list`
- Vérifiez l'URL dans `.env` : `OLLAMA_BASE_URL`

### Audio ne fonctionne pas

- Vérifiez les permissions microphone dans Préférences Système
- Testez avec `sounddevice` directement : `python -m sounddevice`

### OSC ne fonctionne pas

- Vérifiez l'IP et le port dans l'interface
- Testez avec un client OSC comme `OSCulator` ou `TouchOSC`
- Vérifiez le firewall macOS

## 📄 Licence

[À définir]

## 👤 Auteur

Studio Carlos

