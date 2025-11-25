# 🎨 Interface de Visualisation - Documentation

## ✅ Modifications Réalisées

### 1. Interface Graphique (`main.py`)

**Nouvelles fonctionnalités :**

#### Zone STT (Speech-to-Text)
- ✅ **Textbox défilante** : Affiche les 2-3 dernières phrases transcrites
- ✅ **Effet "Rolling Text"** : Le texte se met à jour en temps réel
- ✅ **Limite de 500 caractères** : Évite le lag de l'interface
- ✅ **Style cyberpunk** : Police Monaco, couleur Matrix green (#00ff41)

#### Zone Brain (Prompt LLM)
- ✅ **Affichage du dernier prompt** : Prompt, Style, Mood
- ✅ **Mise à jour en temps réel** : Se met à jour dès qu'un nouveau prompt est généré
- ✅ **Style cyberpunk** : Couleur neon pink (#ff0080)

#### Console Logs
- ✅ **Color coding** : 
  - `[AUDIO]` en bleu cyan (#00d9ff)
  - `[BRAIN]` en magenta (#ff0080)
  - `[OSC]` en vert (#00ff41)
  - `[ERROR]` en rouge (#ff4444)
- ✅ **Timestamps** : Chaque log inclut l'heure

#### Contrôles
- ✅ **Boutons START/STOP** : Style cyberpunk avec couleurs vives
- ✅ **Statut visuel** : Indicateur de statut avec couleur dynamique
- ✅ **Configuration OSC** : Interface compacte pour IP/Port

### 2. Dashboard Terminal (`rich`)

**Fonctionnalités :**
- ✅ **Layout structuré** : Header, STT, Brain, Status
- ✅ **Mise à jour en temps réel** : Rafraîchissement toutes les 500ms
- ✅ **Couleurs distinctes** :
  - STT en bleu
  - Brain en magenta
  - Status en vert/rouge selon l'état
- ✅ **Détection terminal** : Ne s'affiche que dans un vrai terminal (pas dans IDE)

### 3. Thread-Safety

**Implémentation :**
- ✅ **`.after()` de Tkinter** : Toutes les mises à jour UI passent par le thread principal
- ✅ **Callbacks thread-safe** :
  - `on_audio_data()` → `_update_transcript_ui()`
  - `on_brain_prompt()` → `_update_prompt_ui()`
- ✅ **Pas de blocage** : Les threads secondaires ne touchent jamais directement l'UI

### 4. Style Cyberpunk

**Palette de couleurs :**
```python
CYBERPUNK_BG = "#0a0a0a"        # Fond noir profond
CYBERPUNK_FG = "#00ff41"        # Vert Matrix
CYBERPUNK_ACCENT = "#ff0080"    # Rose néon
CYBERPUNK_BLUE = "#00d9ff"      # Cyan
CYBERPUNK_PURPLE = "#9d00ff"    # Violet
```

**Éléments stylisés :**
- Titre avec police grande et gras
- Bordures arrondies (corner_radius=10)
- Fond sombre (#1a1a1a) pour les frames
- Couleurs vives pour les accents

## 📋 Structure du Code

### Callbacks Thread-Safe

```python
# Dans AudioEngine thread
def on_audio_data(self, text: str):
    self.after(0, self._update_transcript_ui, text)

# Dans BrainEngine thread  
def on_brain_prompt(self, prompt_data: Dict):
    self.after(0, self._update_prompt_ui, prompt_data)
```

### Mise à Jour UI

```python
def _update_transcript_ui(self, text: str):
    # Ajouter au buffer rolling
    self.stt_text_buffer.append(text)
    if len(self.stt_text_buffer) > 4:
        self.stt_text_buffer.pop(0)
    
    # Mettre à jour textbox
    display_text = " ".join(self.stt_text_buffer)
    if len(display_text) > 500:
        display_text = "..." + display_text[-500:]
    
    self.stt_textbox.insert("1.0", display_text)
```

## 🚀 Utilisation

### Lancer l'application

```bash
python main.py
```

### Interface Graphique

1. **Zone STT** : Affiche la transcription en temps réel (mot par mot)
2. **Zone Brain** : Affiche le dernier prompt généré par le LLM
3. **Console** : Logs colorés de tous les événements
4. **Contrôles** : START/STOP pour démarrer/arrêter les engines

### Terminal Dashboard

Le dashboard s'affiche automatiquement dans le terminal si :
- `rich` est installé
- L'application tourne dans un vrai terminal (pas IDE)

**Format :**
```
┌─────────────────────────────────────────┐
│ 🎤 VoiceVibe4 - Real-Time Dashboard     │
├─────────────────────────────────────────┤
│ [STT] Speech-to-Text                    │
│ [AUDIO] Texte transcrit en temps réel...│
├─────────────────────────────────────────┤
│ [LLM] Visual Prompt                     │
│ [BRAIN] Prompt: A futuristic city...   │
│         Style: cyberpunk | Mood: dark   │
├─────────────────────────────────────────┤
│ Status: RUNNING                         │
└─────────────────────────────────────────┘
```

## 🔧 Configuration

### Couleurs Personnalisées

Modifier les constantes dans `main.py` :
```python
CYBERPUNK_BG = "#0a0a0a"
CYBERPUNK_FG = "#00ff41"
CYBERPUNK_ACCENT = "#ff0080"
CYBERPUNK_BLUE = "#00d9ff"
CYBERPUNK_PURPLE = "#9d00ff"
```

### Taille du Buffer STT

Modifier dans `_update_transcript_ui()` :
```python
if len(self.stt_text_buffer) > 4:  # Nombre de phrases à garder
    self.stt_text_buffer.pop(0)
```

### Limite de Caractères

Modifier dans `_update_transcript_ui()` :
```python
if len(display_text) > 500:  # Limite de caractères
    display_text = "..." + display_text[-500:]
```

## 🐛 Dépannage

### Le dashboard terminal ne s'affiche pas

1. Vérifier que `rich` est installé : `pip install rich`
2. Lancer depuis un vrai terminal (pas depuis IDE)
3. Vérifier que `sys.stdout.isatty()` retourne `True`

### L'UI se fige lors de la transcription

1. Vérifier que tous les callbacks utilisent `.after()`
2. Vérifier qu'aucun thread secondaire ne touche directement l'UI
3. Réduire la limite de caractères dans le buffer STT

### Les couleurs ne s'affichent pas correctement

1. Vérifier que customtkinter est à jour : `pip install --upgrade customtkinter`
2. Vérifier les permissions d'affichage macOS
3. Tester avec un thème différent

## 📊 Flux de Données

```
AudioEngine Thread
    ↓ (callback)
on_audio_data(text)
    ↓ (.after() thread-safe)
_update_transcript_ui(text)
    ↓
STT Textbox (UI)
    ↓
Terminal Dashboard (rich)

BrainEngine Thread
    ↓ (callback)
on_brain_prompt(prompt_data)
    ↓ (.after() thread-safe)
_update_prompt_ui(prompt_data)
    ↓
Prompt Label (UI)
    ↓
Terminal Dashboard (rich)
```

## ✅ Checklist de Test

- [ ] Interface graphique s'affiche correctement
- [ ] Zone STT se met à jour en temps réel
- [ ] Zone Brain affiche les prompts
- [ ] Console logs avec couleurs
- [ ] Dashboard terminal s'affiche (si terminal)
- [ ] Pas de freeze de l'UI
- [ ] Thread-safety vérifiée (pas d'erreurs)
- [ ] Boutons START/STOP fonctionnent
- [ ] Configuration OSC fonctionne

## 📚 Dépendances Ajoutées

```txt
rich>=13.0.0  # Terminal dashboard
```

## 🎨 Aperçu Visuel

### Interface Graphique

```
┌─────────────────────────────────────────┐
│         VOICEVIBE4                       │
│  Real-Time Audio → Visual Brain          │
├─────────────────────────────────────────┤
│ [STT] Speech Transcription              │
│ ┌─────────────────────────────────────┐ │
│ │ Texte transcrit en temps réel...    │ │
│ └─────────────────────────────────────┘ │
├─────────────────────────────────────────┤
│ [BRAIN] Last Visual Prompt             │
│ Prompt: A futuristic city...          │
│ Style: cyberpunk | Mood: dark         │
├─────────────────────────────────────────┤
│ OSC Configuration                       │
│ IP: [127.0.0.1] Port: [5005] [Update]  │
├─────────────────────────────────────────┤
│ [▶ START]        [⏹ STOP]            │
│ ● Status: RUNNING                      │
├─────────────────────────────────────────┤
│ [LOG] System Console                   │
│ [12:34:56] [AUDIO] Transcription...    │
│ [12:34:57] [BRAIN] Generated prompt... │
└─────────────────────────────────────────┘
```

### Terminal Dashboard

```
╔═════════════════════════════════════════╗
║ 🎤 VoiceVibe4 - Real-Time Dashboard     ║
╠═════════════════════════════════════════╣
║ [STT] Speech-to-Text                    ║
║ [AUDIO] Texte transcrit...              ║
╠═════════════════════════════════════════╣
║ [LLM] Visual Prompt                     ║
║ [BRAIN] Prompt: A futuristic city...   ║
║         Style: cyberpunk | Mood: dark  ║
╠═════════════════════════════════════════╣
║ Status: RUNNING                          ║
╚═════════════════════════════════════════╝
```

## 🚀 Prochaines Améliorations Possibles

- [ ] Graphique de visualisation audio (waveform)
- [ ] Historique des prompts (scrollable)
- [ ] Export des logs
- [ ] Thèmes personnalisables
- [ ] Mode plein écran
- [ ] Statistiques en temps réel (mots/min, prompts/min)

