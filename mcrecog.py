import speech_recognition as sr
import mc_socket
from mc_socket import MCSocket
import tkinter as tk
from tkinter import font
import json

# Charger les items Minecraft
with open('items_fr.json', 'r', encoding='utf-8-sig') as f:
    items_fr = json.load(f)

# Socket Minecraft (connexion obligatoire)
try:
    mc = MCSocket(7777)
except SystemExit:
    print("Erreur : Impossible de se connecter à Minecraft. Script arrêté.")
    exit(1)

# Inverser items
nom_to_id = {v.lower(): k for k, v in items_fr.items()}

# Homophones / Variantes
homophones = {
    "corbeau": ["corbeau", "corbeaux"],
    "flèches": ["flèches", "flèche", "fleches", "fleche"],
    "ours": ["ours", "ourse", "oursse"],
    "axolotl": ["axolotl", "axolotol"],
    "zombie": ["zombie", "zombis"],
    "squelette": ["squelette", "skelette"],
    "cochon": ["cochon", "cochons", "cochant"],
    "surprise": ["surprise"],
    "creeper": ["creeper", "cripeur", "creepeur"],
    "blaze": ["blaze", "blaize"],
    "enderman": ["enderman", "endermen", "endermane"],
    "nether": ["nether", "nézer"],
    "caverne": ["caverne", "cavern"],
    "trou": ["trou", "trous"],
    "nuit": ["nuit", "nuits"],
    "fantôme": ["fantôme", "fantomes", "fantom"],
    "bateau": ["bateau", "bateaux"],
    "dragon": ["dragon", "dragons"],
    "supercreeper": ["supercreeper", "super creeper", "supercri peur"],
    "charbon": ["charbon", "charbons"],
    "fer": ["fer", "fers"],
    "or": ["or", "ors"],
    "diamant": ["diamant", "diamants"],
    "sac": ["sac", "sacs"],
    "portail": ["portail", "portails"],
    "noyade": ["noyade", "noyades"],
    "lapin": ["lapin", "lapins"],
    "voler": ["voler", "volé", "volée"],
    "obsidienne": ["obsidienne"],
    "sorcière": ["sorcière", "sorcières"],
    "minerai": ["minerai", "minerais"],
    "explosion": ["explosion", "explosions"],
    "éclair": ["éclair", "eclair", "éclairs"],
    "encre": ["encre", "encres"],
    "pousser": ["pousser", "poussée", "poussées"],
    "lave": ["lave", "laves"],
    "soin": ["soin", "soins"],
    "invincible": ["invincible", "invincibles"],
    "cauchemar": ["cauchemar", "cauchemars"],
    "ferraille": ["ferraille", "ferrailles"],
    "force": ["force", "forces"],
    "troll": ["troll", "trolls"]
}

# Interface Tkinter OBS
root = tk.Tk()
root.title("Stream Overlay")
root.geometry("1280x150+100+100")
root.configure(bg="#00FF00")
root.attributes('-topmost', True)
root.overrideredirect(True)

# Déplacement fenêtre
def start_move(event):
    root.x = event.x
    root.y = event.y

def stop_move(event):
    root.x = None
    root.y = None

def do_move(event):
    x = (event.x_root - root.x)
    y = (event.y_root - root.y)
    root.geometry(f"+{x}+{y}")

root.bind('<Button-1>', start_move)
root.bind('<ButtonRelease-1>', stop_move)
root.bind('<B1-Motion>', do_move)

canvas = tk.Canvas(root, bg="#00FF00", highlightthickness=0)
canvas.pack(fill="both", expand=True)

font_normal = font.Font(family="IMPACT", size=32)
font_bold = font.Font(family="IMPACT", size=32, weight="bold")

def mots_speciaux_dans_partie(mot):
    mot = mot.lower()
    for liste in homophones.values():
        for variante in liste:
            if variante in mot:
                return variante
    for nom in nom_to_id.keys():
        if nom in mot:
            return nom
    return None

def update_text(phrase):
    canvas.delete("all")
    mots = phrase.split()
    x = 50
    y = 75
    for mot in mots:
        clean_mot = mot.lower().replace(",", "").replace(".", "").replace("!", "").replace("?", "")
        found = mots_speciaux_dans_partie(clean_mot)

        if found:
            idx = clean_mot.find(found)
            part1 = mot[:idx]
            part2 = mot[idx:idx+len(found)]
            part3 = mot[idx+len(found):]

            if part1:
                id = canvas.create_text(x, y, text=part1, fill="white", font=font_normal, anchor="w")
                bbox = canvas.bbox(id)
                if bbox:
                    x = bbox[2]

            if part2:
                id = canvas.create_text(x, y, text=part2, fill="red", font=font_bold, anchor="w")
                bbox = canvas.bbox(id)
                if bbox:
                    x = bbox[2]

            if part3:
                id = canvas.create_text(x, y, text=part3, fill="white", font=font_normal, anchor="w")
                bbox = canvas.bbox(id)
                if bbox:
                    x = bbox[2]

            x += 20  # Espace entre mots
        else:
            id = canvas.create_text(x, y, text=mot, fill="white", font=font_normal, anchor="w")
            bbox = canvas.bbox(id)
            if bbox:
                x = bbox[2] + 20

# Reconnaissance vocale Google
r = sr.Recognizer()
r.energy_threshold = 400
r.pause_threshold = 2
r.dynamic_energy_threshold = True

mic = sr.Microphone()

print("🎙️ Prêt à écouter avec Google Speech Recognition")

while True:
    try:
        with mic as source:
            r.adjust_for_ambient_noise(source)
            audio = r.listen(source)
        try:
            resp = r.recognize_google(audio, language="fr-FR")
            print(f"Reconnu : {resp}")

            if resp.strip() != "":
                update_text(resp)

                texte_clean = resp.replace(" ", "").lower()
                triggered = False

                for variantes in homophones.values():
                    for variante in variantes:
                        if variante in texte_clean:
                            triggered = True
                            break
                    if triggered:
                        break

                if not triggered:
                    for nom in nom_to_id.keys():
                        if nom in texte_clean:
                            triggered = True
                            break

                if triggered:
                    mc.stream(["Random explosion"])

        except sr.UnknownValueError:
            pass
        except sr.RequestError:
            print("Erreur avec l'API Google ! (connexion perdue ?)")

        root.update_idletasks()
        root.update()

    except KeyboardInterrupt:
        print("Fermeture du programme.")
        break
