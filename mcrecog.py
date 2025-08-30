import json
import queue
import threading
import time
import numpy as np
import sounddevice as sd
import tkinter as tk
from tkinter import font
from faster_whisper import WhisperModel

# ====== CONFIG ======
MODEL_SIZE = "small"        # "tiny", "base", "small", "medium"
DEVICE = "cpu"              # "cpu" ou "cuda"
COMPUTE_TYPE = "int8"       # "int8" (cpu), "float16" (gpu), "int8_float16" (mixte)
SAMPLE_RATE = 16000
CHUNK_MS = 200              # taille des chunks micro (ms)
INFER_EVERY_MS = 900        # fréquence d'inférence
WINDOW_SEC = 4.0            # fenêtre d'audio analysée (secondes récentes)
VAD_FILTER = True           # filtre VAD pour couper le silence

# ====== TES IMPORTS MINECRAFT ======
import mc_socket
from mc_socket import MCSocket

# ====== CHARGEMENT ITEMS ======
with open('items_fr.json', 'r', encoding='utf-8-sig') as f:
    items_fr = json.load(f)

# Inverser items
nom_to_id = {v.lower(): k for k, v in items_fr.items()}

# Homophones / Variantes (reprend ta liste)
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

# ====== CONNEXION MINECRAFT ======
try:
    mc = MCSocket(7777)
except SystemExit:
    print("Erreur : Impossible de se connecter à Minecraft. Script arrêté.")
    raise SystemExit(1)

# ====== MODELE WHISPER ======
print("Chargement du modèle faster-whisper… (premier run = téléchargement)")
model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)

# ====== CAPTURE MICRO ======
audio_q = queue.Queue()
blocksize = int(SAMPLE_RATE * (CHUNK_MS / 1000.0))
last_infer_time = 0.0
audio_buffer = np.zeros(0, dtype=np.float32)

def audio_callback(indata, frames, time_info, status):
    if status:
        # print(status)  # debug si besoin
        pass
    # indata est float32 [-1,1], mono (channels=1)
    audio_q.put(indata.copy())

def mic_stream_start():
    stream = sd.InputStream(
        channels=1,
        samplerate=SAMPLE_RATE,
        dtype='float32',
        blocksize=blocksize,
        callback=audio_callback
    )
    stream.start()
    return stream

# ====== UI TKINTER (Overlay amélioré) ======
class Overlay:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Stream Overlay")
        self.root.geometry("900x160+100+100")
        self.root.configure(bg="#00FF00")  # chroma key green
        self.root.attributes('-topmost', True)
        self.borderless = True

        # Fenêtre sans bord pour chroma key propre, mais on garde le redim custom
        self.root.overrideredirect(True)

        # Canvas + padding + wrap
        self.PAD_X = 24
        self.PAD_Y = 18

        # Fonts
        self.font_size = 32
        self.font_normal = font.Font(family="IMPACT", size=self.font_size)
        self.font_bold = font.Font(family="IMPACT", size=self.font_size, weight="bold")

        self.canvas = tk.Canvas(self.root, bg="#00FF00", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # Déplacement (drag n'importe où)
        self.root.bind('<Button-1>', self._start_move)
        self.root.bind('<ButtonRelease-1>', self._stop_move)
        self.root.bind('<B1-Motion>', self._do_move)

        # Redimensionnement : grip bas-droit + drag des bords
        self.resize_grip_size = 18
        self.canvas.bind("<Motion>", self._cursor_feedback)
        self.canvas.bind("<ButtonPress-3>", self._start_resize)    # clic droit pour saisir le redim
        self.canvas.bind("<B3-Motion>", self._do_resize)
        self.canvas.bind("<ButtonRelease-3>", self._stop_resize)

        # Molette: change taille police
        self.root.bind("<MouseWheel>", self._on_wheel)             # Windows
        self.root.bind("<Button-4>", self._on_wheel_up)            # Linux
        self.root.bind("<Button-5>", self._on_wheel_down)          # Linux

        # Raccourcis utiles
        self.root.bind("<Escape>", lambda e: self.toggle_border())
        self.root.bind("<F5>", lambda e: self.toggle_topmost())

        # Redraw sur resize
        self.root.bind("<Configure>", self._on_configure)

        # Texte courant
        self.current_text = ""

        # Etat redim
        self.resizing = False
        self.resize_anchor = None  # (x0, y0, w0, h0, mouse_x0, mouse_y0)

        # Dessine le grip initial
        self._draw_grip()

    # ---- Move window ----
    def _start_move(self, event):
        self.root._x = event.x_root - self.root.winfo_x()
        self.root._y = event.y_root - self.root.winfo_y()

    def _stop_move(self, event):
        self.root._x = None
        self.root._y = None

    def _do_move(self, event):
        if getattr(self.root, "_x", None) is not None:
            x = event.x_root - self.root._x
            y = event.y_root - self.root._y
            self.root.geometry(f"+{x}+{y}")

    # ---- Resize window ----
    def _cursor_feedback(self, event):
        # change le curseur si on est sur le grip
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        if (w - event.x) <= self.resize_grip_size and (h - event.y) <= self.resize_grip_size:
            self.canvas.config(cursor="bottom_right_corner")
        else:
            self.canvas.config(cursor="arrow")

    def _start_resize(self, event):
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        # active si clic dans le grip
        if (w - event.x) <= self.resize_grip_size and (h - event.y) <= self.resize_grip_size:
            self.resizing = True
            self.resize_anchor = (self.root.winfo_x(), self.root.winfo_y(), w, h, event.x_root, event.y_root)

    def _do_resize(self, event):
        if not self.resizing or self.resize_anchor is None:
            return
        _, _, w0, h0, mx0, my0 = self.resize_anchor
        dw = event.x_root - mx0
        dh = event.y_root - my0
        new_w = max(400, w0 + dw)
        new_h = max(120, h0 + dh)
        self.root.geometry(f"{int(new_w)}x{int(new_h)}")

    def _stop_resize(self, event):
        self.resizing = False
        self.resize_anchor = None
        self._draw_grip()
        self.redraw()

    def _draw_grip(self):
        # petit triangle/grip en bas à droite
        self.canvas.delete("grip")
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        s = self.resize_grip_size
        self.canvas.create_polygon(
            (w-s, h, w, h, w, h-s),
            fill="#00CC00", outline="", tags="grip"
        )

    # ---- Font size via wheel ----
    def _on_wheel(self, event):
        # Windows: event.delta
        if event.delta > 0:
            self._bump_font(2)
        else:
            self._bump_font(-2)

    def _on_wheel_up(self, event):     # Linux
        self._bump_font(2)

    def _on_wheel_down(self, event):   # Linux
        self._bump_font(-2)

    def _bump_font(self, delta):
        self.font_size = max(14, min(96, self.font_size + delta))
        self.font_normal.configure(size=self.font_size)
        self.font_bold.configure(size=self.font_size)
        self.redraw()

    # ---- Window options ----
    def toggle_border(self):
        self.borderless = not self.borderless
        self.root.overrideredirect(self.borderless)

    def toggle_topmost(self):
        self.root.attributes("-topmost", not self.root.attributes("-topmost"))

    def _on_configure(self, event):
        # redraw tout + grip quand la fenêtre change
        self.redraw()
        self._draw_grip()

    # ---- Texte / Rendering ----
    def set_text(self, phrase: str):
        self.current_text = phrase
        self.redraw()

    def redraw(self):
        c = self.canvas
        c.delete("all")
        # fond vert pour chroma key
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        c.create_rectangle(0, 0, w, h, fill="#00FF00", outline="")

        if not self.current_text:
            return

        # wrap & highlight
        self._draw_text_wrapped(self.current_text, self.PAD_X, self.PAD_Y, w - 2*self.PAD_X)

        # grip
        self._draw_grip()

    def _draw_text_wrapped(self, phrase: str, x0: int, y0: int, max_width: int):
        # On découpe en mots, on wrap quand on dépasse max_width
        words = phrase.split(" ")
        x = x0
        y = y0
        line_height = self.font_normal.metrics("linespace") + 4

        for word in words:
            # ponctuation: on la rend non bloquante
            raw = word
            clean = raw.lower().replace(",", "").replace(".", "").replace("!", "").replace("?", "")

            # chercher variante/hit
            found = mots_speciaux_dans_partie(clean)

            # mesurer le mot rendu (avec split highlight)
            part1, part2, part3 = split_highlight(raw, found)

            # largeur totale si placé maintenant
            w_total = 0
            if part1:
                w_total += self.font_normal.measure(part1)
            if part2:
                w_total += self.font_bold.measure(part2)
            if part3:
                w_total += self.font_normal.measure(part3)
            w_total += self.font_normal.measure(" ")  # espace après

            # wrap si dépasse
            if x + w_total > x0 + max_width:
                x = x0
                y += line_height

            # dessiner les 3 parties
            if part1:
                id1 = self.canvas.create_text(x, y, text=part1, fill="white", font=self.font_normal, anchor="nw")
                x = self.canvas.bbox(id1)[2]
            if part2:
                id2 = self.canvas.create_text(x, y, text=part2, fill="red", font=self.font_bold, anchor="nw")
                x = self.canvas.bbox(id2)[2]
            if part3:
                id3 = self.canvas.create_text(x, y, text=part3, fill="white", font=self.font_normal, anchor="nw")
                x = self.canvas.bbox(id3)[2]

            # espace entre mots
            space_w = self.font_normal.measure(" ")
            x += space_w

    def loop_tick(self):
        self.root.update_idletasks()
        self.root.update()

def mots_speciaux_dans_partie(mot: str):
    mot = mot.lower()
    # check homophones
    for liste in homophones.values():
        for variante in liste:
            if variante in mot:
                return variante
    # check items
    for nom in nom_to_id.keys():
        if nom in mot:
            return nom
    return None

def split_highlight(mot_affiche: str, found: str):
    """Retourne (part1, part2, part3) où part2 est la partie à surligner."""
    if not found:
        return mot_affiche, "", ""
    lower = mot_affiche.lower()
    idx = lower.find(found)
    if idx < 0:
        return mot_affiche, "", ""
    p1 = mot_affiche[:idx]
    p2 = mot_affiche[idx:idx+len(found)]
    p3 = mot_affiche[idx+len(found):]
    return p1, p2, p3

def text_has_trigger(text: str):
    # logique proche de ton code: homophones puis items
    texte_clean = text.replace(" ", "").lower()

    for variantes in homophones.values():
        for variante in variantes:
            if variante in texte_clean:
                return True
    for nom in nom_to_id.keys():
        if nom in texte_clean:
            return True
    return False

def main():
    # UI
    overlay = Overlay()

    # Micro
    mic = mic_stream_start()
    print("🎙️ Prêt à écouter (faster-whisper, FR)")

    # Boucle principale: récupère audio, infère régulièrement
    global audio_buffer, last_infer_time
    last_text = ""
    last_trigger_time = 0.0
    TRIGGER_COOLDOWN = 1.0  # évite spam d'explosions (secondes)

    try:
        while True:
            # Récupère tout ce qui est en file (non bloquant)
            try:
                while True:
                    data = audio_q.get_nowait()
                    audio_buffer = np.concatenate((audio_buffer, data.flatten()))
            except queue.Empty:
                pass

            # Limite la fenêtre
            max_len = int(WINDOW_SEC * SAMPLE_RATE)
            if len(audio_buffer) > max_len:
                audio_buffer = audio_buffer[-max_len:]

            # Infère à intervalle régulier
            now = time.time()
            if (now - last_infer_time) * 1000.0 >= INFER_EVERY_MS and len(audio_buffer) > SAMPLE_RATE * 0.5:
                last_infer_time = now

                # Copie la fenêtre actuelle
                window_audio = audio_buffer.copy()

                # Transcription
                # Conseils: beam_size=1 (rapide), no_speech_thresh = défaut ok, vad_filter pour couper silences
                segments, info = model.transcribe(
                    window_audio,
                    language="fr",
                    beam_size=1,
                    vad_filter=VAD_FILTER,
                    vad_parameters=dict(min_silence_duration_ms=200)
                )

                # Concat segments texte
                text = "".join(seg.text for seg in segments).strip()

                if text:
                    # Affiche immédiatement (overlay dynamique)
                    overlay.set_text(text)

                    # Déclenche si mot clé et anti-spam
                    if text_has_trigger(text) and (now - last_trigger_time) > TRIGGER_COOLDOWN:
                        try:
                            mc.stream(["Random explosion"])
                            last_trigger_time = now
                        except Exception as e:
                            print("Erreur en envoyant à Minecraft:", e)

                    last_text = text

            # Tick UI
            overlay.loop_tick()
            time.sleep(0.01)

    except KeyboardInterrupt:
        print("Fermeture du programme.")
    finally:
        try:
            mic.stop()
            mic.close()
        except Exception:
            pass

if __name__ == "__main__":
    main()
