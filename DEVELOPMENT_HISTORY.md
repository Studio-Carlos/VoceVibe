# Development History

## Overview
This document consolidates the full chronological history of the **VoceVibe4** project migration from the MLX‑based STT backend to the official PyTorch `kyutai/stt-1b-en_fr` model.

It combines the original implementation plan, the detailed walkthrough, and the task checklist, providing a single reference for future maintenance.

---

### Implementation Plan (original)

* **Objective**: Migrate to PyTorch STT model for deterministic, hallucination‑free French transcription.
* **Key Steps**:
  1. Remove MLX dependencies and install PyTorch, Moshi, and related packages.
  2. Create `download_stt.py` to fetch model files from HuggingFace.
  3. Rewrite `src/audio_engine.py` to load the model via Moshi, handle audio encoding with Mimi, and enforce `temp=0.0`.
  4. Verify on CPU, ensure correct sample rate (24 kHz), and maintain producer‑consumer queue.

---

### Walkthrough (summary)

* **Dependencies**: Uninstalled `moshi_mlx`, `mlx`, `rustymimi`; installed `torch==2.5.1`, `torchaudio==2.5.1`, `moshi`, `huggingface‑hub`, `sentencepiece`, `sounddevice`.
* **Model Download**: `download_stt.py` successfully retrieves `model.safetensors`, `config.json`, `tokenizer_spm_32k_3.model`, and related files.
* **Audio Engine Rewrite**:
  * Loaded model configuration, filtered incompatible keys, and instantiated via `loaders.get_moshi_lm`.
  * Initialized Mimi with `num_codebooks=32`.
  * Implemented streaming context (`with self.lm_gen.streaming(batch_size=1):`).
  * Fixed gradient error by removing `torch.no_grad()` around `lm_gen.step`.
  * **System Prompt Optimization**: Updated `BrainEngine` system prompt to enforce English output, specific SDXL-Turbo syntax (`[Style], [Subject], ...`), and strict JSON format for better visual generation.
* **Verification**:
  * `test_stt_final.py` confirmed model loads and processes dummy audio chunks.
  * `main.py` runs without errors, providing French transcriptions.

---

### Task Checklist (final state)

```
- [x] Uninstall MLX dependencies
- [x] Install PyTorch dependencies (torch 2.5.1, torchaudio 2.5.1, moshi, etc.)
- [x] Update requirements.txt
- [x] Create and run download_stt.py
- [x] Rewrite audio_engine.py for PyTorch CPU
- [x] Configure deterministic decoding (temp=0.0)
- [x] Fix streaming context and Mimi codebook count
- [x] Remove erroneous torch.no_grad() wrapper
- [x] Verify with test script and main application
- [x] Clean up repository (remove tests, add README, update .gitignore, set main branch)
```

---

## Future Work
* Explore GPU acceleration (if compatible hardware becomes available).
* Add unit tests for audio processing pipeline.
* Integrate UI improvements and dynamic visual feedback.
# 📜 Historique d'Implémentation - Kyutai STT (Moshi/Moshika) sur macOS

## 🎯 Contexte du Projet

### VoiceVibe4 - Performance Visuelle en Temps Réel

**Objectif** : Créer une application macOS native qui transforme la voix en performances visuelles en temps réel.

**Architecture** :
- **AudioEngine** : Capture microphone → Transcription STT → Queue texte
- **BrainEngine** : Analyse texte (LLM local) → Génération prompts visuels → OSC vers PC distant
- **Interface** : GUI customtkinter avec visualisation temps réel

**Exigence STT** :
- Transcription bilingue français/anglais en temps réel
- Optimisé Apple Silicon (M1/M2/M3)
- Latence minimale pour performance live
- Pas de Whisper (trop lent, pas de streaming natif)

**Choix initial** : **Kyutai Moshi** (modèle 1B bilingue fr/en, streaming natif, optimisé Apple Silicon)

---

## 🗺️ Parcours d'Implémentation - Étape par Étape

### **Étape 1 : Implémentation PyTorch Initiale**

#### Configuration
- **Modèle** : `kyutai/moshiko-pytorch-bf16`
- **Backend** : PyTorch avec MPS (Metal Performance Shaders)
- **Sample Rate** : 24000 Hz
- **Chunk Size** : 1920 samples (80 ms @ 24 kHz)
- **Device** : MPS avec fallback CPU

#### Problème #1 : API Incorrecte
```
ImportError: cannot import name 'MoshiLoader' from 'moshi.models.loaders'
```

**Cause** : Tentative d'utiliser une API inexistante (`MoshiLoader`, `get_worker()`)

**Solution tentée** : Recherche de la bonne API dans la documentation

**Résultat** : Découverte de `moshi.models.loaders.get_moshi_lm` et `LMGen`

---

### **Étape 2 : Correction API PyTorch**

#### Configuration
- **Modèle** : `kyutai/moshiko-pytorch-bf16`
- **API** : `get_moshi_lm()` + `LMGen` pour streaming
- **Architecture** : Callback audio direct → Encodage → Inférence ML

#### Problème #2 : Crash PyTorch MPS
```
SIGABRT: libtorch_python.dylib
c10::StorageImpl::~StorageImpl()
```

**Cause** : Gestion mémoire PyTorch MPS défaillante, tensors non libérés correctement

**Solutions tentées** :
1. Ajout de `torch.no_grad()` autour de l'inférence
2. `.detach()` sur tous les tensors
3. `del` explicite des tensors
4. `torch.mps.empty_cache()` après chaque batch
5. `non_blocking=True` pour les transfers device

**Résultat** : Crash toujours présent, instabilité MPS

---

### **Étape 3 : Fallback CPU PyTorch**

#### Configuration
- **Modèle** : `kyutai/moshiko-pytorch-bf16`
- **Device** : CPU (fallback forcé)
- **Variable** : `PYTORCH_ENABLE_MPS_FALLBACK=1`

#### Problème #3 : Opérateur MPS Non Implémenté
```
The operator 'aten::index_copy.out' is not currently implemented for the MPS device.
```

**Cause** : PyTorch MPS ne supporte pas tous les opérateurs nécessaires à Moshi

**Solution** : Forcer CPU avec `PYTORCH_ENABLE_MPS_FALLBACK=1`

**Résultat** : Fonctionne mais **performance terrible** (CPU trop lent pour temps réel)

---

### **Étape 4 : Problème de Transcription**

#### Configuration
- **Modèle** : `kyutai/moshiko-pytorch-bf16`
- **Device** : CPU (fallback)
- **Performance** : Lente mais fonctionnelle

#### Problème #4 : Transcription Inexacte
- Transcription en anglais alors que l'input est français (France Culture)
- Hallucinations : "Hey there, how is it going?" au lieu de transcription
- Modèle refuse de transcrire en français

**Cause** : 
1. Biais linguistique vers l'anglais par défaut
2. Pas de conditionnement linguistique
3. Signal audio peut-être trop faible

**Solutions tentées** :
1. Vérification du modèle : `kyutai/stt-1b-en_fr` (bilingue confirmé)
2. Augmentation du volume source
3. Tentative de conditionnement français (échec - crash dimensions)

**Résultat** : Modèle transcrit mais avec biais anglais fort

---

### **Étape 5 : Migration vers Moshi MLX**

#### Décision
**Raison** : PyTorch MPS instable, CPU trop lent → Passage à **MLX** (framework natif Apple Silicon)

#### Configuration Initiale
- **Modèle** : `kyutai/moshiko-mlx-q4` (4-bit quantization)
- **Backend** : MLX (Metal optimisé)
- **Packages** : `moshi_mlx`, `rustymimi`, `mlx.core`
- **Sample Rate** : 24000 Hz
- **Chunk Size** : 1920 samples

#### Implémentation
- Architecture producteur-consommateur (queue audio)
- Encodage avec `rustymimi.StreamTokenizer`
- Inférence avec `models.LmGen.step()`
- Décodage avec `sentencepiece.SentencePieceProcessor`

#### Problème #5 : Hallucinations et Réponses IA
```
STT: "How can I help you"
STT: "That's correct"
```

**Cause** : 
1. Le modèle génère à la fois transcription ET réponses IA
2. Pas de filtrage des tokens (on capture tout)
3. Température trop élevée (défaut ~0.8)

**Solutions tentées** :
1. Réduction température : `temp=0.2` → `temp=0.1`
2. Ajout `top_p=0.9` pour éliminer tokens improbables
3. Noise gate strict : seuil 0.04 (ignore bruit de fond)

**Résultat** : Moins d'hallucinations mais toujours des réponses IA mélangées

---

### **Étape 6 : Filtrage des Tokens**

#### Configuration
- **Modèle** : `kyutai/moshiko-mlx-q4`
- **Sampling** : `temp=0.1`, `top_p=0.9`
- **Noise Gate** : 0.04

#### Problème #6 : Mélange Transcription/Réponses IA
Le modèle génère deux types de tokens :
- **Tokens transcription** : Ce que l'utilisateur dit
- **Tokens réponse IA** : Réponses de Moshi ("How can I help you", etc.)

**Cause** : Pas de distinction dans le code entre les deux types de tokens

**Solution** : **Découverte cruciale** - Dans `moshi_mlx.local`, les tokens 0 et 3 sont filtrés :
```python
if text_token_id not in (0, 3):
    # C'est un token de transcription valide
```

**Résultat** : Filtrage implémenté, mais problème persiste (tokens IA passent quand même)

---

### **Étape 7 : Conditionnement Français (Échec)**

#### Configuration
- **Modèle** : `kyutai/moshiko-mlx-q4`
- **Objectif** : Forcer le modèle en mode français

#### Problème #7 : Biais Anglais Persistant
Le modèle refuse de transcrire en français, même avec France Culture

**Solution tentée** : Conditionnement français
```python
# Pré-remplir le contexte avec du français
prompt_text = "Transcription en français : "
# Encoder et injecter dans le modèle
```

#### Problème #8 : Crash Dimensions
```
Error: (1,8,1,1) vs (1,8,1) - dimension mismatch
```

**Cause** : Mauvaise forme des tensors MLX pour le conditionnement

**Résultat** : Conditionnement abandonné (trop complexe, instable)

---

### **Étape 8 : Passage à Moshika**

#### Décision
**Raison** : Moshika (voix féminine) souvent plus stable que Moshiko pour la transcription

#### Configuration
- **Modèle** : `kyutai/moshika-mlx-q4` (au lieu de `moshiko`)
- **Backend** : MLX
- **Quantization** : 4-bit (q4)

#### Problème #9 : Signal Audio Faible
Transcription instable, modèle hallucine à cause du bruit de fond

**Solutions** :
1. **AGC Plus Agressif** : `target_level=0.95` (au lieu de 0.8)
2. **Warning Signal Faible** : Alerte si `peak < 0.05`
3. **Noise Gate Strict** : Seuil 0.04 maintenu

**Résultat** : Meilleure normalisation, mais problème de tokens IA persiste

---

### **Étape 9 : Découverte du Pattern Officiel**

#### Réalisation
Le code manuel était instable → **Utiliser le pattern de `moshi_mlx.local`**

#### Analyse de `moshi_mlx.local`
- Architecture client-serveur avec queues
- Filtrage strict : `if text_token_id not in (0, 3)`
- Transposition exacte : `mx.array(data).transpose(1, 0)[:, :8]`
- Pas de conditionnement complexe

#### Problème #10 : Implémentation Manuelle Instable
- Lecture des mauvais tokens (réponses IA au lieu de transcription)
- Dimensions incorrectes
- Architecture trop complexe

**Solution** : **Réécriture complète** basée sur `moshi_mlx.local`

---

### **Étape 10 : Réécriture avec Pattern Officiel (Solution Finale)**

#### Configuration Finale
- **Modèle** : `kyutai/moshika-mlx-q4`
- **Pattern** : Basé sur `moshi_mlx.local` (référence officielle)
- **Architecture** : Producteur-consommateur avec queue
- **Filtrage** : Tokens 0 et 3 ignorés (filtre réponses IA)
- **Sampling** : `temp=0.1`, `top_p=0.9` (strict)
- **AGC** : `target_level=0.95` (agressif)
- **Noise Gate** : 0.04 (strict)

#### Implémentation Clé
```python
# Filtrage strict (pattern officiel)
if text_token_id not in (0, 3):
    # Token de transcription valide
    text_piece = text_tokenizer.id_to_piece(text_token_id)
    text_piece = text_piece.replace("▁", " ")
    # Ajouter à la queue
```

#### Transposition Exacte (Pattern Officiel)
```python
# Comme dans moshi_mlx.local
data = mx.array(encoded_data).transpose(1, 0)[:, :8]
text_token = self.gen.step(data)
```

**Résultat** : ✅ **Solution stable et fonctionnelle**

---

## 📊 Récapitulatif des Configurations Testées

| Étape | Modèle | Backend | Device | Chunk Size | Sampling | Résultat |
|-------|--------|---------|--------|------------|----------|----------|
| 1 | moshiko-pytorch-bf16 | PyTorch | MPS | 1920 | Défaut | ❌ API incorrecte |
| 2 | moshiko-pytorch-bf16 | PyTorch | MPS | 1920 | Défaut | ❌ Crash MPS |
| 3 | moshiko-pytorch-bf16 | PyTorch | CPU | 1920 | Défaut | ⚠️ Trop lent |
| 4 | moshiko-pytorch-bf16 | PyTorch | CPU | 1920 | Défaut | ⚠️ Biais anglais |
| 5 | moshiko-mlx-q4 | MLX | MLX | 1920 | Défaut | ⚠️ Hallucinations |
| 6 | moshiko-mlx-q4 | MLX | MLX | 1920 | temp=0.1 | ⚠️ Tokens IA |
| 7 | moshiko-mlx-q4 | MLX | MLX | 1920 | temp=0.1 | ❌ Crash conditionnement |
| 8 | moshika-mlx-q4 | MLX | MLX | 1920 | temp=0.1 | ⚠️ Signal faible |
| 9 | moshika-mlx-q4 | MLX | MLX | 1920 | temp=0.1 | ⚠️ Pattern incorrect |
| 10 | **moshika-mlx-q4** | **MLX** | **MLX** | **1920** | **temp=0.1, top_p=0.9** | ✅ **Stable** |

---

## 🔑 Leçons Apprises

### 1. **PyTorch MPS n'est pas prêt pour Moshi**
- Opérateurs manquants (`aten::index_copy.out`)
- Gestion mémoire instable
- **Solution** : MLX (framework natif Apple Silicon)

### 2. **Le Filtrage des Tokens est Critique**
- Tokens 0 et 3 = tokens spéciaux (padding, etc.)
- Sans filtrage → réponses IA mélangées avec transcription
- **Solution** : Pattern officiel avec `if text_token_id not in (0, 3)`

### 3. **L'Architecture Producteur-Consommateur est Essentielle**
- Callback audio doit être ultra-léger
- Traitement ML dans thread séparé
- **Solution** : Queue pour découpler capture et inférence

### 4. **Le Pattern Officiel est la Référence**
- `moshi_mlx.local` = implémentation de référence
- Transposition exacte : `.transpose(1, 0)[:, :8]`
- **Solution** : Suivre le pattern officiel à la lettre

### 5. **Moshika est Plus Stable que Moshiko**
- Moshika (voix féminine) = meilleure transcription
- Moshiko = plus de réponses IA parasites
- **Solution** : Utiliser Moshika pour STT pur

### 6. **Le Sampling Strict Réduit les Hallucinations**
- Température basse (0.1) = déterministe
- `top_p=0.9` = élimine tokens improbables
- **Solution** : Sampling strict pour STT

### 7. **L'AGC Agressif Améliore la Transcription**
- Signal faible → hallucinations
- `target_level=0.95` = meilleure normalisation
- **Solution** : AGC agressif avec warning signal faible

### 8. **Le Noise Gate Strict Évite le Bruit**
- Bruit de fond → hallucinations
- Seuil 0.04 = ignore bruit, garde voix
- **Solution** : Noise gate strict avec `continue` (skip chunk)

---

## 🎯 Configuration Finale Recommandée

### Modèle
- **Repo** : `kyutai/moshika-mlx-q4`
- **Quantization** : 4-bit (q4) - bon compromis vitesse/qualité
- **Backend** : MLX (Metal optimisé)

### Audio
- **Sample Rate** : 24000 Hz (requis par Mimi)
- **Chunk Size** : 1920 samples (80 ms @ 24 kHz)
- **Channels** : 1 (mono)

### Traitement
- **AGC** : `target_level=0.95`, `max_gain=8.0`
- **Noise Gate** : `threshold=0.04`
- **Warning** : Si `peak < 0.05` → alerte utilisateur

### Modèle MLX
- **Sampling** : `temp=0.1`, `top_p=0.9` (strict)
- **Filtrage** : Tokens 0 et 3 ignorés
- **Pattern** : Basé sur `moshi_mlx.local`

### Architecture
- **Producteur** : Callback audio → Queue (ultra-léger)
- **Consommateur** : Queue → Encodage → Inférence → Filtrage → Queue texte

---

## 📝 Notes Finales

### Ce qui Fonctionne ✅
- Transcription bilingue fr/en en temps réel
- Latence acceptable pour performance live
- Stable sur Apple Silicon (MLX)
- Filtrage correct des tokens (pas de réponses IA)

### Limitations Actuelles ⚠️
- Biais linguistique vers l'anglais (pas de conditionnement linguistique)
- Nécessite signal audio fort (AGC + noise gate)
- Pas de support multilingue explicite (détection auto)

### Améliorations Futures 🔮
- Conditionnement linguistique stable (français/anglais)
- Détection automatique de langue
- Support de plus de langues
- Optimisation mémoire pour sessions longues

---

## 📚 Références

- **Moshi MLX** : https://github.com/kyutai/moshi-mlx
- **Pattern Officiel** : `moshi_mlx.local` (dans package installé)
- **Documentation Kyutai** : https://huggingface.co/kyutai
- **MLX Framework** : https://github.com/ml-explore/mlx

---

**Date de dernière mise à jour** : 2024-11-24  
**Version** : Finale (basée sur pattern officiel)  
**Statut** : ✅ Stable et fonctionnel

