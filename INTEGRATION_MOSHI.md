# 🎤 Intégration Moshi - Documentation Technique

## ✅ Modifications Réalisées

### 1. `src/audio_engine.py` - Réécriture Complète

**Changements majeurs :**
- ✅ Intégration de l'API Moshi officielle avec `moshi.models.loaders.MoshiLoader`
- ✅ Utilisation du worker pour le streaming avec `feed_audio()` et `get_output()`
- ✅ Sample rate fixé à **24000 Hz** (standard Moshi)
- ✅ Device MPS (Metal) avec fallback automatique sur CPU
- ✅ Conversion numpy → torch tensor pour Moshi
- ✅ Gestion robuste des erreurs avec fallback device

**Structure clé :**
```python
from moshi.models import loaders

# Chargement du modèle
self.loader = loaders.MoshiLoader(
    repo_id="kyutai/moshiko-pytorch-bf16",
    device=self.device,  # "mps" ou "cpu"
)
self.model = self.loader.load()
self.worker = self.model.get_worker()

# Streaming audio
tensor = torch.from_numpy(audio_data).to(self.device)
self.worker.feed_audio(tensor)
packet = self.worker.get_output()
```

### 2. `src/config.py` - Mise à Jour Audio

**Changements :**
- ✅ `sample_rate` : **24000 Hz** par défaut (au lieu de 16000)
- ✅ `chunk_size` : **1920** par défaut (optimisé pour 24000 Hz)

### 3. `src/brain_engine.py` - Améliorations Critiques

**Nouvelles fonctionnalités :**
- ✅ **Accumulation intelligente** : Ne pas envoyer chaque mot, accumule jusqu'à phrase complète ou timeout 5s
- ✅ **Buffer glissant 60 secondes** : Maintient le contexte des dernières 60 secondes
- ✅ **Format JSON strict** : Utilise `format='json'` dans l'appel Ollama
- ✅ **Context window** : `num_ctx: 4096` pour plus de contexte
- ✅ **Détection de phrase complète** : Analyse quand phrase se termine (., !, ?)

**Structure :**
```python
# Accumulation avec timeout
self._accumulation_timeout = 5.0  # seconds
self._context_window_seconds = 60.0  # Buffer glissant

# Appel Ollama avec JSON strict
response = ollama.chat(
    model=self.config.ollama_model,
    messages=[...],
    format='json',  # Force JSON
    options={'num_ctx': 4096}
)
```

### 4. `src/osc_client.py` - Vérifié ✅

**Déjà conforme :**
- ✅ Envoie `/visual/prompt` (string)
- ✅ Envoie `/visual/json` (string JSON complet)
- ✅ Thread-safe avec verrous

### 5. `requirements.txt` - Mise à Jour

**Ajout :**
```txt
moshi>=0.1.0
```

### 6. `main.py` - Vérifié ✅

**Déjà conforme :**
- ✅ Threads daemon (`daemon=True` dans AudioEngine et BrainEngine)
- ✅ Queue partagée entre AudioEngine et BrainEngine
- ✅ Intégration complète avec UI

## 📋 Configuration Requise

### Variables d'environnement (.env)

```env
# Audio Configuration (CRITIQUE pour Moshi)
AUDIO_SAMPLE_RATE=24000  # ⚠️ DOIT être 24000 Hz
AUDIO_CHANNELS=1
AUDIO_CHUNK_SIZE=1920

# Moshi Configuration
MOSHI_DEVICE=mps  # "mps" pour Apple Silicon, "cpu" pour fallback

# Ollama Configuration
OLLAMA_MODEL=qwen2.5
BRAIN_ANALYSIS_INTERVAL=6.0
```

## 🚀 Installation

### 1. Installer Moshi

```bash
# Option 1: Via pip (si disponible)
pip install moshi

# Option 2: Depuis GitHub
pip install git+https://github.com/kyutai-labs/moshi.git

# Option 3: Vérifier la documentation officielle
# https://github.com/kyutai-labs/moshi
```

### 2. Vérifier PyTorch avec MPS

```bash
python -c "import torch; print(torch.backends.mps.is_available())"
# Doit afficher: True
```

### 3. Installer toutes les dépendances

```bash
pip install -r requirements.txt
```

## 🔧 Points d'Attention

### 1. API Moshi - Format du Packet

L'API Moshi peut retourner le packet sous différents formats :
- Objet avec attribut `.text`
- Dictionnaire avec clé `'text'`
- String directe

Le code gère ces trois cas dans `_audio_callback()`.

### 2. Device Fallback

Le code tente automatiquement MPS, puis CPU si MPS échoue :
```python
if device_preference == "mps":
    if torch.backends.mps.is_available():
        return "mps"
    else:
        return "cpu"  # Fallback automatique
```

### 3. Sample Rate Critique

⚠️ **IMPORTANT** : Moshi nécessite **24000 Hz**. Ne pas utiliser 16000 Hz.

### 4. Chunk Size Optimisé

Pour 24000 Hz, un chunk de 1920 samples = 80ms, ce qui est optimal pour le streaming.

## 🐛 Dépannage

### Erreur: "moshi package not found"

```bash
pip install moshi
# ou
pip install git+https://github.com/kyutai-labs/moshi.git
```

### Erreur: "MPS not available"

Vérifier PyTorch avec support MPS :
```bash
pip install torch torchaudio
python -c "import torch; print(torch.backends.mps.is_available())"
```

### Erreur: "Failed to load Moshi model"

1. Vérifier la connexion internet (téléchargement du modèle)
2. Vérifier l'espace disque (modèle ~2-3 GB)
3. Essayer avec device="cpu" en fallback

### Transcription ne fonctionne pas

1. Vérifier les permissions microphone dans macOS
2. Vérifier que `sample_rate=24000` dans la config
3. Vérifier les logs dans la console pour erreurs Moshi

## 📊 Flux de Données

```
Microphone (24000 Hz)
    ↓
sounddevice callback
    ↓
numpy array → torch tensor
    ↓
worker.feed_audio(tensor)
    ↓
worker.get_output() → packet.text
    ↓
text_queue (thread-safe)
    ↓
BrainEngine (accumulation + buffer 60s)
    ↓
Ollama (format='json', num_ctx=4096)
    ↓
OSC Client (/visual/prompt, /visual/json)
```

## ✅ Checklist de Test

- [ ] Moshi installé et importable
- [ ] PyTorch avec MPS disponible
- [ ] Sample rate configuré à 24000 Hz
- [ ] Permissions microphone accordées
- [ ] Ollama installé avec modèle qwen2.5
- [ ] Test audio callback fonctionne
- [ ] Test transcription Moshi fonctionne
- [ ] Test OSC envoi fonctionne
- [ ] Buffer glissant 60s fonctionne
- [ ] Format JSON strict fonctionne

## 📚 Ressources

- [Moshi GitHub](https://github.com/kyutai-labs/moshi)
- [PyTorch MPS](https://pytorch.org/docs/stable/notes/mps.html)
- [Ollama Python](https://github.com/ollama/ollama-python)

