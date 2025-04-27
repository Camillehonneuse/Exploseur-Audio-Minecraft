# 🎤 MCRecog-FR (Minecraft Speech Commands en Français)

**MCRecog-FR** est un projet de reconnaissance vocale pour contrôler Minecraft à la voix,  
spécialement adapté pour le français 🇫🇷, avec intégration OBS-ready (overlay fond vert).

---

## 🚀 Fonctionnalités principales

- 🎙️ Reconnaissance vocale **en français** via **Google Speech Recognition** API.
- 🎯 Détection de **mots-clés** (ex: "creeper", "cochon", "or") même **intégrés dans un mot** (ex: "Orangina").
- 💥 **Déclenche des explosions** dans Minecraft via socket.
- 🖥️ **Fenêtre fond vert** (overlay) affichant la dernière phrase reconnue.
- 🔴 **Surbrillance rouge** uniquement sur la partie du mot détectée dans le texte.
- ✅ **Connexion obligatoire** à Minecraft (sinon arrêt immédiat).
- ⚡ Optimisations de la qualité micro pour une détection plus précise.

---

## 📋 Prérequis

- **Python 3.8+**
- **Minecraft** avec le mod **MCRecog** installé et lancé.
- Microphone configuré et fonctionnel.

---

## 📦 Installation

1. **Installer les dépendances :**

```bash
pip install SpeechRecognition
pip install PyAudio
