# 🚀 VoiceVibe4 - Guide de Configuration Initiale

## Commandes Git à exécuter

Une fois que vous êtes satisfait du code, exécutez ces commandes pour initialiser le dépôt Git et pousser vers GitHub :

```bash
# Ajouter tous les fichiers
git add .

# Créer le premier commit
git commit -m "Initial commit: VoiceVibe4 - Real-time audio transcription and visual performance brain"

# Renommer la branche en 'main' (optionnel, mais recommandé)
git branch -M main

# Pousser vers GitHub
git push -u origin main
```

## Installation Rapide

### Option 1 : Script automatique

```bash
./install.sh
```

### Option 2 : Installation manuelle

```bash
# Créer l'environnement virtuel
python3 -m venv .venv
source .venv/bin/activate

# Installer les dépendances
pip install --upgrade pip
pip install torch torchaudio  # PyTorch avec MPS pour Apple Silicon
pip install -r requirements.txt

# Configurer l'environnement
cp .env.example .env
# Éditer .env avec vos paramètres

# Installer Ollama et le modèle
brew install ollama  # Si pas déjà installé
ollama pull qwen2.5
```

## Configuration Moshi

**Important** : L'intégration Moshi nécessite l'installation du package approprié. 

1. Consultez la documentation officielle de Moshi/Kyutai
2. Installez le package Python correspondant
3. Mettez à jour `src/audio_engine.py` dans la méthode `_load_moshi_model()` avec l'API réelle

Exemple de structure attendue (à adapter) :
```python
from moshi import MoshiModel  # À ajuster selon l'API réelle

self._moshi_model = MoshiModel.from_pretrained(
    self.config.moshi_model_path or "default",
    device=self.config.moshi_device  # "mps" pour Apple Silicon
)
```

## Vérification

Avant de lancer l'application, vérifiez :

- ✅ Python 3.9+ installé
- ✅ Environnement virtuel activé
- ✅ Toutes les dépendances installées
- ✅ Ollama installé et modèle `qwen2.5` disponible
- ✅ Fichier `.env` configuré
- ✅ Permissions microphone accordées dans macOS

## Lancement

```bash
source .venv/bin/activate
python main.py
```

## Structure du Projet

```
VoceVibe4/
├── src/
│   ├── __init__.py          # Package init
│   ├── config.py            # Configuration (dotenv)
│   ├── osc_client.py        # Client OSC thread-safe
│   ├── audio_engine.py     # Thread audio + Moshi
│   └── brain_engine.py     # Thread LLM + OSC
├── main.py                  # Point d'entrée + UI customtkinter
├── requirements.txt         # Dépendances Python
├── .env.example            # Template de configuration
├── .gitignore              # Fichiers ignorés par Git
├── install.sh              # Script d'installation
├── README.md               # Documentation principale
└── SETUP.md                # Ce fichier
```

## Prochaines Étapes

1. **Intégrer Moshi** : Mettre à jour `src/audio_engine.py` avec l'API réelle
2. **Tester l'audio** : Vérifier que la capture microphone fonctionne
3. **Tester Ollama** : Vérifier que les appels LLM fonctionnent
4. **Tester OSC** : Vérifier la communication avec le PC distant
5. **Ajuster les paramètres** : Modifier les intervalles et prompts selon vos besoins

## Support

Pour toute question ou problème, consultez le `README.md` ou ouvrez une issue sur GitHub.

