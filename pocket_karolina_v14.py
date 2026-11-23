"""
Pocket Karolina  v14
----------------------
Çalıştırma:  python pocket_karolina_v14.py   (ya da start_pocket_karolina.bat'a çift tık)
             Ekstra kurulum yok: sadece Python + tkinter.

Kontroller:
  - Sol tık + sürükle : karakteri tut, taşı / fırlat (hızlı yukarı = KURWA!)
  - Tek tık           : sevgi (ilgi + mood artar)      - Çift tık : dans
  - Sağ tık           : aksiyon balonu
      Dance Sleep Kiss Wave Jump Spin Run Hug  |  Bag  Notes  Settings  Quit
  - Bag  : Hats / Eyes / Wear / Gear / Desk / Emote / Fun sekmeli kişiselleştirme paneli.
           Üzerine gelince anlık önizleme, tıklayınca tak/çıkar. Emote sekmesi ifade oynatır.
  - Fun > Chaos: 30-45 sn kaos modu. Koşar, eşyaları devirir, kendi paneline tıklayıp
           kıyafet değiştirir, İndirilenler klasörünü 2-3 kez açar. Pet'e tek tık = dur.
  - Fun > Treat: Lila'ya kuru et atar; koşup kapar, yatıp kemirir.
  - Chat: telefondan gelen mesajlara buradan cevap ver (telefonda "Karolina" olarak görünür).
  - Game mode: her şeyi gizler, saatin yanındaki simgeye tıklayınca geri gelir.
    Settings > Auto hide açıksa tam ekran oyun/film açıldığında kendiliğinden saklanır.
  - Ara sıra masaüstünde küçük sürprizler belirir; tıklayınca toplanır.
  - Mevsimlik kostümler: yılbaşı, sevgililer günü, yaz, Cadılar Bayramı, Noel.
  - Notes: kısa not / hatırlatıcı. "18:30 anneyi ara" yazarsan saatinde hatırlatır.
  - Settings: dil (EN/TR/PL), konuşma, SAKİN MOD, pencereye tırmanma, flaş, telefon bağlantısı.

Her şey save.json içinde saklanır (yanında .bak yedeği ile) ve uygulama açılınca kaldığı
yerden devam eder. Telefondan kontrol: Settings > Phone ile açılan linki telefonda aç.

Pencerelere tırmanma: Windows (yerleşik ctypes), macOS (pyobjc-Quartz kuruluysa),
Linux/X11 (wmctrl kuruluysa). Desteklenmeyen ortamda sessizce devre dışı kalır.
"""
import atexit
import datetime
import json
import math
import os
import random
import re
import shutil
import subprocess
import sys
import threading
import time
import tkinter as tk
import tkinter.font as tkfont

# Ağ / telefon özellikleri isteğe bağlı: bu modüller yüklenemezse pet yine de açılır.
try:
    import collections
    import hmac
    import queue
    import secrets
    import socket
    import struct
    import zlib
    from http.server import BaseHTTPRequestHandler, HTTPServer
    from urllib.parse import parse_qs, urlparse
    try:
        from http.server import ThreadingHTTPServer
    except ImportError:                                   # Python 3.6
        from socketserver import ThreadingMixIn

        class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
            daemon_threads = True
    NET_OK = True
except Exception:                                         # pragma: no cover
    NET_OK = False

try:                                                      # sert çökmelerde (Tk/Tcl) bile iz bırak
    import faulthandler
    _FH = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "pet_crash.log"), "a")
    faulthandler.enable(_FH)
except Exception:
    pass
from functools import lru_cache

IS_WIN = sys.platform.startswith("win")
IS_MAC = sys.platform == "darwin"

if IS_WIN:                       # pencere koordinatları ile Tk aynı piksel sisteminde olsun
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# ----------------------------- AYARLAR -------------------------------------
SCALE = 3            # piksel büyüklüğü (3 = ~96px, 4 = ~128px)
TICK_MS = 33         # ~30 FPS
GROUND_MARGIN = 48   # ekranın altından boşluk (görev çubuğu için)
PADX, PADT = 34, 44  # efektler (kalp, Zzz...) için pencere payı
KEY = "#010101" if IS_WIN else "systemTransparent"


def make_transparent(win):
    if IS_WIN:
        win.wm_attributes("-transparentcolor", KEY)
    elif IS_MAC:
        win.wm_attributes("-transparent", True)
        win.config(bg="systemTransparent")


# ===========================================================================
#  PIXEL ART  (kafa / gövde / kol / bacak / eşyalar ayrı parçalar)
# ===========================================================================
W = H = 32               # tuval
UW, UX, UY = 24, 4, 6    # üst vücut genişliği ve tuvaldeki yeri

PAL = {"o": "#3a1f1c", "h": "#f07a2a", "H": "#ffa24a", "d": "#c2561c",
       "s": "#fbd0b0", "k": "#e3a583", "l": "#5a2d22", "e": "#4aa8e6",
       "E": "#1d3557", "p": "#f4a0a0", "m": "#c2476b", "n": "#dcdcf0",
       "w": "#f6f6f6", "g": "#cfcfdc", "t": "#3b3b4a",
       "r": "#e63946", "R": "#b01e2a", "y": "#ffd23f", "b": "#3a86ff",
       "u": "#8a3ffc", "a": "#1f1f2b", "c": "#6c7bff", "B": "#8fd3ff",
       "W": "#ff9ebd", "G": "#e0709a", "J": "#2e2e38", "j": "#1d1d25",
       "Y": "#f2c230", "Z": "#d9a21b", "S": "#e0525e", "Q": "#b83a46",
       "V": "#8fe3c0", "D": "#62c79d", "N": "#9a6a35", "M": "#5a3a1e",
       "v": "#58b368", "x": "#ff7aa2", "X": "#ff4f8b",
       "P": "#c9a8ff", "L": "#9b78e0", "T": "#f3e3c3", "q": "#d4bb8a",
       "I": "#4b6fb5", "i": "#34528f", "F": "#ffe9a8", "f": "#fff6d6"}

EYES = {
    "normal": ("slllssssllls", "seEesssseEes", "seeesssseees"),
    "wide":   ("slllssssllls", "seEesssseEes", "seEesssseEes"),
    "closed": ("ssssssssssss", "slllssssllls", "ssssssssssss"),
    "happy":  ("sslsssssslss", "slslsssslsls", "ssssssssssss"),
    "annoyed": ("llllssssllll", "seEesssseEes", "ssssssssssss"),   # sıkkın / küs
    "heart":  ("sXsXssssXsXs", "sXXXssssXXXs", "ssXssssssXss"),    # kalp gözler
    "star":   ("ssyssssssyss", "syYyssssyYys", "ssyssssssyss"),    # yıldız gözler
    "wink":   ("slllssssslss", "seEesssslsls", "seeessssssss"),    # göz kırpma
    "cry":    ("slllssssllls", "seEesssseEes", "sBeesssseeBs"),    # ağlayan
    "dizzy":  ("slslsssslsls", "sslsssssslss", "slslsssslsls"),    # baş dönmesi
    "shy":    ("ssssssssssss", "slllssssllls", "ssssssssssss"),    # utangaç
}
MOUTH = {
    "smile": "sssssmmsssss",
    "grin":  "ssssmmmmssss",
    "open":  "sssssoosssss",
    "kiss":  "sssssmssssss",
    "wavy":  "sssmsmsmsmss",
    "laugh": "sssoooooosss",
}


def O(s):
    return "o" + s + "o"


def C(s):
    return s.center(UW, ".")


@lru_cache(maxsize=None)
def head_rows(eyes, mouth):
    e8, e9, e10 = EYES[eyes]
    rows = [
        "",
        "oooooooooo",
        O("hHHhhhhhhhhd"),
        O("hhHHhhhhhhhhhhhd"),
        O("hhhHhhhhhhhhhhhhhd"),
        O("hhHhhhhhhhhhhhhhhd"),
        O("hhhhhhh" + "ssss" + "hhhhhhd"),
        O("hhhhh" + "ssssssssss" + "hhd"),
        O("hhh" + e8 + "hhd"),
        O("hHh" + e9 + "hhd"),
        O("hhhh" + e10 + "hhhd"),
        O("hHhh" + "sppsssssspps" + "hhhd"),
        O("hhn" + MOUTH[mouth] + "nhd"),          # küpeler (n)
        O("hhhhn" + "ssssssss" + "nhhhd"),
        O("hhhhhh" + "kkkkkk" + "hhhhhd"),
    ]
    return [C(r) for r in rows]


TORSO = [C(r) for r in [
    O("hhhhhhh" + "ssss" + "hhhhhhd"),
    O("hhhhhh" + "snnnnnns" + "hhhhhd"),          # kolye
    O("hhhh" + "ssswwwwwwsss" + "hhhd"),
    O("hhh" + "swwwwwwwwwws" + "hhd"),
    O("hhH" + "gwwwwwwwwwwwwg" + "hhd"),
    O("ttttttttttttt" + "t"),
]]

ARM_D = ["owwo", "owwo", "owgo", "osso", "osso", ".oo."]
ARM_U = ARM_D[::-1]
LEG = ["otttto"] * 5 + ["owwwwo", "oooooo"]
SHOE = ["owwwwo", "oooooo"]
PHONE = ["oooo", "oBBo", "oBBo", "oBBo", "oBBo", "oooo"]

# ------------------------------- EŞYALAR -----------------------------------
# Şapkalar: (satırlar, kafa üstüne göre y kayması)
HATS = {
    "party": ([C(r) for r in [
        "oyyo", "orro", "orrrro", "oyyyyyyo", "orrrrrrrro", "obbbbbbbbbbo"]], -4),
    "cap": ([C(r) for r in [
        "oooooooo",
        O("rrrrrrrrrr"),
        O("rrrrrrwwrrrrrr"),
        O("RRRRRRRRRRRRRRRRRR")]], 0),
    "crown": ([C(r) for r in [
        ".oo..oo..oo.",
        "oyyooyyooyyo",
        "oyyyyrryyyyo",
        "oooooooooooo"]], -1),
}


def _phones():
    g = [["."] * UW for _ in range(15)]

    def p(x, y, c="u"):
        if 0 <= x < UW and 0 <= y < 15:
            g[y][x] = c
    for x in range(7, 17):
        p(x, 0)
    for x in (5, 6, 17, 18):
        p(x, 1)
    for x in (3, 4, 19, 20):
        p(x, 2)
    for x in (2, 21):
        p(x, 3)
    for y in range(4, 9):
        p(1, y)
        p(22, y)
    cup = ["ouuo", "uppu", "uuuu", "ouuo"]
    for j, row in enumerate(cup):
        for i, ch in enumerate(row):
            p(0 + i, 9 + j, ch)
            p(20 + i, 9 + j, ch)
    return ["".join(r) for r in g]


HATS["phones"] = (_phones(), 0)
HATS["beanie"] = ([C(r) for r in [
    "oyyo", O("bbbbbbbb"), O("bbwbbwbbwbbw"), O("wwwwwwwwwwwwwwww")]], 0)
_EAR_L = [".oo.", "owwo", "opwo", "opwo", "opwo", "owwo", "owwo"]
_EAR_R = [".oo.", "owwo", "owpo", "owpo", "owpo", "owwo", "owwo"]
HATS["bunny"] = ([C(a + "...." + b) for a, b in zip(_EAR_L, _EAR_R)], -4)
HATS["cowboy"] = ([C(r) for r in [
    "oooooooo", O("NNNNNNNN"), O("MMMMMMMMMM"), O("N" * 20)]], -1)
HATS["flowers"] = ([C(r) for r in [
    "vxvyvxvyvx", "xvvyvxvvyvxvvx"]], 1)



def _pad(rows, w=None):
    w = w or max(len(r) for r in rows)
    return [C(r.center(w, ".")) for r in rows]


HATS["catears"] = (_pad([
    "oo..........oo", "opo........opo", "oppo......oppo",
    "ouuuuuuuuuuuuo"]), -1)
HATS["bow"] = (_pad([
    "oooo..oooo", "oXXXooXXXo", "oXxGGGGxXo", "oXXXooXXXo", "oooo..oooo"]), -3)
HATS["santa"] = (_pad([
    "...........ooo.", "..........owwwo", ".......ooooowwo", ".....oorrrrrro.",
    "....orrrrrrrrro", "...orrRrrrrrrro", "..owwwwwwwwwwwwo"], 16), -4)
HATS["strawhat"] = (_pad([
    "...oooooooo...", "..oYYYYYYYYo..", "..oYrrrrrrYo..", "oooYYYYYYYYooo",
    "oYYYYYYYYYYYYYYo", "oooooooooooooooo"], 16), -2)
HATS["witch"] = (_pad([
    "..........oo......", ".........oao......", "........oaao......", ".......oaaao......",
    "......oaaaao......", ".....oaaaaaao.....", ".....oaaaaaao.....", "....ouuuyyuuuo....",
    "oooooaaaaaaaaaoooo", "oaaaaaaaaaaaaaaaao", "oooooooooooooooooo"]), -6)
HATS["halo"] = (_pad([
    "..oooooooo..", ".oyyyyyyyyo.", "oyo......oyo", ".oyyyyyyyyo.", "..oooooooo.."]), -5)

# Gözlük: (satırlar, x, y)  -> kafa gridine göre
GLASSES = {
    "shades": (["aaaaaaaaaaaa", "acaaa..acaaa", ".aaa....aaa."], 6, 8),
    "hearts": (["XX.XX..XX.XX", "XXXXX..XXXXX", ".XXX....XXX."], 6, 8),
    "specs":  ([".yyy....yyy.", "y...yyyy...y", ".yyy....yyy."], 6, 8),
    "round":  ([".NNN....NNN.", "N...NNNN...N", ".NNN....NNN."], 6, 8),
    "stars":  (["..y......y..", "yyYyy..yyYyy", ".yyy....yyy."], 6, 8),
    "pixel":  (["aaaaaaaaaaaa", "aBaaaaaaaBaa", "aaaaaaaaaaaa"], 6, 8),
}

# Kıyafetler: renk eşlemesi + ekstra pikseller (gövde gridine göre)
OUTFITS = {
    "hoodie": dict(map={"w": "W", "g": "G"},
                   extra=[(10, 3, "n"), (10, 4, "n"), (13, 3, "n"), (13, 4, "n")]),
    "jacket": dict(map={"w": "J", "g": "j"},
                   extra=[(11, 2, "n"), (11, 3, "n"), (11, 4, "n")]),
    "raincoat": dict(map={"w": "Y", "g": "Z"}, extra=[(11, 3, "a"), (11, 4, "a")]),
    "sweater": dict(map={"w": "S", "g": "Q"},
                    extra=[(c, 2, "w") for c in range(9, 15)]),
    "mint": dict(map={"w": "V", "g": "D"}, extra=[]),
    "sailor": dict(map={}, extra=[(c, 2, "b") for c in range(9, 15)] +
                   [(c, 4, "b") for c in range(6, 18)]),
}


def _wcols(y):
    return [i for i, ch in enumerate(TORSO[y]) if ch == "w"]


OUTFITS["lavender"] = dict(map={"w": "P", "g": "L"},
                           extra=[(10, 3, "w"), (10, 4, "w"), (13, 3, "w"), (13, 4, "w")])
OUTFITS["heart"] = dict(map={}, extra=[(10, 2, "X"), (13, 2, "X"), (10, 3, "X"), (11, 3, "X"),
                                       (12, 3, "X"), (13, 3, "X"), (11, 4, "X"), (12, 4, "X")])
OUTFITS["overalls"] = dict(map={}, extra=[(9, 2, "I"), (14, 2, "I")] +
                           [(c, 3, "I") for c in range(9, 15)] + [(c, 4, "I") for c in range(7, 17)] +
                           [(11, 3, "y"), (12, 3, "y")])
OUTFITS["cardigan"] = dict(map={"w": "T", "g": "q"},
                           extra=[(11, 3, "N"), (11, 4, "N"), (12, 2, "q"), (12, 3, "q"), (12, 4, "q")])
OUTFITS["candy"] = dict(map={}, extra=[(c, 3, "x") for c in _wcols(3)])
# boyun aksesuarları (gövde gridine göre x, y, renk)
NECK = {
    "scarf": [(c, 1, "r") for c in range(8, 16)] + [(c, 0, "R") for c in range(10, 14)] +
             [(13, 2, "r"), (14, 2, "r"), (14, 3, "r")],
    "bowtie": [(9, 1, "u"), (10, 1, "u"), (11, 1, "y"), (12, 1, "y"), (13, 1, "u"),
               (14, 1, "u"), (9, 2, "u"), (14, 2, "u")],
    "choker": [(c, 1, "a") for c in range(8, 16)] + [(11, 2, "X"), (12, 2, "X")],
    "beads": [(c, 1, "P" if c % 2 else "x") for c in range(8, 16)] +
             [(9, 2, "x"), (14, 2, "P"), (11, 2, "P"), (12, 2, "x")],
    "ribbon": [(c, 1, "x") for c in (8, 9, 14, 15)] + [(10, 0, "X"), (10, 1, "X"), (10, 2, "X"),
               (13, 0, "X"), (13, 1, "X"), (13, 2, "X"), (11, 1, "G"), (12, 1, "G")],
    "locket": [(c, 1, "Y") for c in range(8, 16)] +
              [(11, 2, "Y"), (12, 2, "Y"), (11, 3, "r"), (12, 3, "r")],
}
CUP = ["oNNo", "owwo", "owwo", "oooo"]
BOBA = ["..o..", ".owo.", "opppo", "opppo", "oaaao", ".ooo."]
CONE = [".ooo.", "oWWWo", "oWWGo", "ooooo", "oNMNo", ".oNo.", "..o.."]
ROSE = [".ooo.", "orRro", "oRrRo", ".ooo.", "..v..", ".vv..", "..v..", "..v.."]
LOLLI = [".ooo.", "oxXxo", "oXwXo", "oxXxo", ".ooo.", "..g..", "..g..", "..g.."]
PUMPKIN = ["...v...", ".ooooo.", "ohhdhho", "oahdaho", "ohhdhho", "ohaaaho", ".ooooo."]
HELD_SPR = {"coffee": (CUP, 2), "boba": (BOBA, -1), "icecream": (CONE, -2),
            "rose": (ROSE, -3), "lollipop": (LOLLI, -3), "pumpkin": (PUMPKIN, 1)}
BALLOON_ICON = ["..ooo..", ".orrro.", "orwrrro", "orrrrro", "orrrrro", ".orrro.",
                "..ooo..", "...o...", "...o..."]

# kategori -> eşya haritası
SLOT_OF = {}
for _i in HATS:
    SLOT_OF[_i] = "hat"
for _i in GLASSES:
    SLOT_OF[_i] = "glasses"
for _i in OUTFITS:
    SLOT_OF[_i] = "outfit"
for _i in NECK:
    SLOT_OF[_i] = "neck"
for _i in ("coffee", "balloon", "boba", "icecream", "rose", "lollipop", "pumpkin"):
    SLOT_OF[_i] = "held"
SLOTS = ("hat", "glasses", "outfit", "neck", "held")


def K(hdx=0, hdy=0, bdy=0, eyes="normal", mouth="smile",
      al="d", ald=0, alx=0, ar="d", ard=0, arx=0,
      legs="stand", ll=0, lr=0, ldx=0, rdx=0,
      hat=None, glasses=None, outfit=None, neck=None, held=None, ph=0):
    """Bir pozu tanımlayan (hashlenebilir) anahtar."""
    return (hdx, hdy, bdy, eyes, mouth, al, ald, alx, ar, ard, arx,
            legs, ll, lr, ldx, rdx, hat, glasses, outfit, neck, held, ph)


EQ = slice(16, 21)       # anahtar içindeki (hat, glasses, outfit, neck, held)


def compose(key):
    (hdx, hdy, bdy, eyes, mouth, al, ald, alx, ar, ard, arx,
     legs, ll, lr, ldx, rdx, hat, glasses, outfit, neck, held, ph) = key
    g = [["."] * W for _ in range(H)]

    def px(x, y, ch):
        if 0 <= y < H and 0 <= x < W:
            g[y][x] = ch

    def paste(part, x, y, remap=None):
        for j, row in enumerate(part):
            for i, ch in enumerate(row):
                if ch != ".":
                    px(x + i, y + j, remap.get(ch, ch) if remap else ch)

    of = OUTFITS.get(outfit)
    remap = of["map"] if of else None

    if legs == "stand":
        paste(LEG, 9 + ldx, 24 - ll)
        paste(LEG, 17 + rdx, 24 - lr)
    else:                                   # oturma: ll/lr = ayakları sallama
        paste(SHOE, 4 + ldx, 29 - ll)
        paste(SHOE, 22 + rdx, 29 - lr)

    ty = UY + 15 + bdy
    paste(TORSO, UX, ty, remap)
    if of:
        for cx, cy, ch in of["extra"]:
            px(UX + cx, ty + cy, ch)
    for cx, cy, ch in NECK.get(neck, ()):
        px(UX + cx, ty + cy, ch)

    hy = UY + bdy + hdy
    paste(head_rows(eyes, mouth), UX + hdx, hy)
    if glasses:
        rows, gx, gy = GLASSES[glasses]
        paste(rows, UX + hdx + gx, hy + gy)
    if hat:
        rows, yo = HATS[hat]
        paste(rows, UX + hdx, hy + yo)

    by = UY + 17 + bdy
    if al == "d":
        paste(ARM_D, 6 + alx, by + ald, remap)
    else:
        paste(ARM_U, 3 + alx, by - 5 + ald, remap)
    if ar == "d":
        paste(ARM_D, 22 + arx, by + ard, remap)
        if held in HELD_SPR:
            spr, dy = HELD_SPR[held]
            paste(spr, 26 + arx, by + dy + ard)
    else:
        paste(ARM_U, 25 + arx, by - 5 + ard, remap)
        if ph == 1:
            paste(PHONE, 26 + arx, by - 9 + ard)
        elif ph == 2:                                   # bardak yüze yakın (içiyor)
            paste(CUP, 26 + arx, by - 8 + ard)
    if ph == 3:                                         # kitap göğüs hizasında
        paste(BOOK, 12, by - 1)
    return ["".join(r) for r in g]


# yürüme / koşma döngüsü (8 evre)
WALK = dict(
    ll=[0, 1, 1, 1, 0, 0, 0, 0], lr=[0, 0, 0, 0, 0, 1, 1, 1],
    bob=[0, 0, -1, 0, 0, 0, -1, 0], hx=[0, 0, 1, 1, 0, 0, -1, -1])
RUN = dict(
    ll=[0, 1, 2, 2, 1, 0, 0, 0], lr=[1, 0, 0, 0, 0, 1, 2, 2],
    bob=[0, -1, -1, 0, 0, -1, -1, 0], hx=[0, 1, 1, 1, 0, -1, -1, -1])

DANCE = [
    dict(hdx=-1, bdy=-1, al="u", ar="d", ll=1, lr=0, ldx=-1),
    dict(hdx=0, bdy=-2, al="u", ar="u", ll=2, lr=2),
    dict(hdx=1, bdy=-1, al="d", ar="u", ll=0, lr=1, rdx=1),
    dict(hdx=0, bdy=0, al="u", ar="u", ll=0, lr=0),
]



# ------------------------------ MASA OBJELERİ -------------------------------
PROP_PAL = {"o": "#2a1d22", "v": "#58b368", "L": "#2f7d44", "r": "#d9774a",
            "R": "#b85a32", "s": "#e8f1ff", "c": "#e63946", "C": "#ffffff",
            "y": "#ffe27a", "Y": "#ffc93c", "g": "#9aa3b2", "G": "#6d7686",
            "h": "#7c8594", "k": "#6b4a2f", "K": "#a4743f", "j": "#d0a36a",
            "p": "#ff9ebd", "P": "#e0709a", "b": "#6ec6ff", "B": "#3a86ff",
            "w": "#ffffff", "W": "#e9edf7", "n": "#4a4358", "m": "#c9a0ff", "u": "#8a3ffc"}
PLANT = [
    "...oo....oo...", "..ovvo..ovvo..", ".ovvvvooovvvo.", ".ovLvvvvvvLvo.",
    "..oovvvvvvoo..", "....ovvvvo....", ".....oLLo.....", ".....oLLo.....",
    "..oooooooooo..", "..orrrrrrrro..", "..orrRrrRrro..", "...orrrrrro...",
    "....oooooo....",
]
MUG = [
    ".oooooooo...", ".occcccco.oo", ".occCccco.co", ".occcccco.oo",
    ".occcccco...", "..oooooo....",
]
LAMP = [
    "...oooo...", "..oyyyyo..", ".oyyYYyyo.", "oyyyyyyyyo", "oooooooooo",
    "....oo....", "....og....", "....og....", "....og....", "...oggo...",
    "..oggggo..", "..oooooo..",
]
PROP_W = {"plant": 14, "mug": 12, "lamp": 10, "radio": 14, "chair": 16,
          "mirror": 12, "cupcake": 12, "teddy": 12, "books": 12, "cactus": 12}
PROP_ORDER = ["chair", "teddy", "radio", "books", "mirror", "plant", "cactus",
              "cupcake", "lamp", "mug"]   # köşe dizilimi
BOOK = ["bbbbbbbb", "bwwbwwwb", "bwwbwwwb", "bwwbwwwb", "bbbbbbbb"]


# ---- mobilyalar kodla üretilir (piksel ızgara yardımcıları)
def _new(w, h):
    return [["."] * w for _ in range(h)]


def _fill(g, x1, y1, x2, y2, ch):
    for y in range(y1, y2 + 1):
        for x in range(x1, x2 + 1):
            g[y][x] = ch


def _box(g, x1, y1, x2, y2, fill, line="o"):
    _fill(g, x1, y1, x2, y2, line)
    _fill(g, x1 + 1, y1 + 1, x2 - 1, y2 - 1, fill)


def _rows(g):
    return ["".join(r) for r in g]


CUPCAKE = [
    ".....oo.....", "....occo....", "...oooooo...", "..oPPPPPPo..", ".oPppPPppPo.",
    ".oooooooooo.", "..oBbBbBbo..", "..oBbBbBbo..", "...oBbBbo...", "...oooooo...",
]
TEDDY = [
    ".oo......oo.", "oKKooooooKKo", "oKKKKKKKKKKo", ".oKoKKKKoKo.", ".oKKjjjjKKo.",
    ".oKKjoojKKo.", "...occcco...", ".oKKKKKKKKo.", "oKKoKKKKoKKo", "oKKoKjjKoKKo",
    ".ooKKjjKKoo.", "..oKKKKKKo..", "..oKKooKKo..", "..ooo..ooo..",
]
BOOKS = [
    "...ooooooo..", "..oBBBBBBBo.", "..oBbcbbbBo.", "..ooooooooo.", ".oPPPPPPPPPo",
    ".owwwwwwwwwo", ".oooooooooo.", "oyyyyyyyyyyo", "owwwwwwwwwwo", "oooooooooooo",
]
CACTUS = [
    ".....pp.....", "....pyyp....", ".....pp.....", "....ovvo....", ".oo.ovLo.oo.",
    ".ovoovvoovo.", ".ovvvvvvvvo.", "..oovvvvoo..", "....ovLo....", "....ovvo....",
    "..oooooooo..", "..oBBBBBBo..", "..oBbBBbBo..", "...oBBBBo...", "...oooooo...",
]


def mirror_grid(frame=0, on=False):
    g = _new(12, 15)
    _box(g, 1, 0, 10, 8, "K")
    _fill(g, 2, 1, 9, 7, "s")
    for r in (0, 1, 8):                                   # oval köşeleri
        for x in (1, 10):
            g[r][x] = "."
    for x, y in ((3, 2), (4, 2), (3, 3)) if frame == 0 or not on else ((7, 4), (8, 4), (8, 5), (6, 6)):
        g[y][x] = "C"
    _fill(g, 4, 9, 7, 10, "K")
    _fill(g, 3, 11, 8, 11, "K")
    _fill(g, 2, 12, 9, 13, "K")
    _fill(g, 2, 14, 9, 14, "o")
    for y in (9, 10):
        g[y][3] = g[y][8] = "o"
    return _rows(g)


def radio_grid(frame=0):
    g = _new(14, 10)
    _box(g, 0, 3, 13, 9, "G")
    _fill(g, 10, 0, 10, 2, "o")
    _box(g, 2, 4, 7, 8, "y" if frame == 0 else "Y")
    _fill(g, 4, 6, 5, 6, "o")
    _fill(g, 9, 5, 11, 5, "c" if frame else "g")
    _fill(g, 9, 7, 11, 7, "g")
    return _rows(g)


def chair_grid():
    g = _new(16, 14)
    _box(g, 2, 0, 13, 7, "B")
    _box(g, 0, 5, 15, 11, "b")
    _box(g, 0, 4, 2, 11, "B")
    _box(g, 13, 4, 15, 11, "B")
    _fill(g, 4, 8, 11, 8, "B")
    _fill(g, 1, 12, 2, 13, "k")
    _fill(g, 13, 12, 14, 13, "k")
    return _rows(g)


def prop_grid(kind, t=0, on=True):
    """Masa objesinin o anki karesi. on: lamba yanık / radyo çalıyor."""
    if kind == "plant":
        sway = (0, 1, 0, -1)[(t // 22) % 4]
        rows = []
        for i, r in enumerate(PLANT):
            if i <= 4 and sway:
                r = (("." * sway + r)[:14]) if sway > 0 else (r[-sway:] + "." * -sway)
            rows.append(r)
        return rows
    if kind == "mug":
        a = (t // 14) % 2
        steam = ("...s...s....", "..s...s.....") if a else ("....s...s...", "...s...s....")
        return list(steam) + MUG
    if kind == "radio":
        return radio_grid((t // 8) % 2 if on else 0)
    if kind == "mirror":
        return mirror_grid((t // 10) % 2, on)
    if kind == "cupcake":
        return CUPCAKE
    if kind == "teddy":
        return TEDDY
    if kind == "books":
        return BOOKS
    if kind == "cactus":
        return CACTUS
    if kind == "chair":
        return chair_grid()
    rows = list(LAMP)
    if not on:
        rows = [r.replace("y", "h").replace("Y", "G") for r in rows]
    return rows


# ===========================================================================
#  BALONLAR / PANELLER
# ===========================================================================
B_FILL, B_OUT, B_SHADOW = "#fff4ea", "#3a1f1c", "#d6bfae"
BTN_FILL, BTN_HOVER, BTN_ON = "#ffe3d3", "#ffb3c7", "#c8f3d2"
TXT, TITLE_C, CHECK_C = "#3a1f1c", "#c2561c", "#2a9d5c"


def _lerp(c1, c2, a):
    a = max(0.0, min(1.0, a))
    p1 = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    p2 = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(int(p1[i] + (p2[i] - p1[i]) * a) for i in range(3))


def _out_back(t):
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def _clip(s, n):
    return s if len(s) <= n else s[:n - 1] + "…"


def _trim(grid):
    rows = [r for r in grid if r.strip(".")]
    if not rows:
        return ["."]
    cols = [i for i in range(max(len(r) for r in rows))
            if any(i < len(r) and r[i] != "." for r in rows)]
    a, b = cols[0], cols[-1] + 1
    return [r[a:b] for r in rows]


_ICONS = {}


def icon_image(kind, iid):
    """Panel karoları için küçük piksel ikonlar (önbellekli)."""
    key = (kind, iid)
    if key in _ICONS:
        return _ICONS[key]
    pal, sc = PAL, 2
    if kind == "hat":                                   # şapka başın üstünde görünsün
        g = compose(K(hat=iid, eyes="happy", mouth="grin"))
        grid, sc = [r[4:28] for r in g[0:17]], 2
    elif kind == "glasses":
        g = compose(K(glasses=iid, eyes="normal", mouth="smile"))
        grid, sc = [r[9:23] for r in g[12:19]], 3
    elif kind == "outfit":
        of = OUTFITS[iid]
        rows = [list(r) for r in TORSO[2:5]]
        for r in rows:
            for i, ch in enumerate(r):
                r[i] = "." if ch in "hHdo" else of["map"].get(ch, ch)
        for cx, cy, ch in of["extra"]:
            if 2 <= cy <= 4:
                rows[cy - 2][cx] = ch
        grid, sc = _trim(["".join(r) for r in rows]), 3
    elif kind == "neck":
        g = compose(K(neck=iid, eyes="happy", mouth="grin"))
        grid, sc = [r[10:22] for r in g[20:27]], 4
    elif kind == "held":
        grid, sc = (HELD_SPR[iid][0], 5) if iid in HELD_SPR else (BALLOON_ICON, 4)
    elif kind == "phone":
        grid, sc = PHONE, 4
    elif kind == "prop":
        grid, pal = prop_grid(iid, 0, iid == "lamp"), PROP_PAL
        sc = 2 if len(grid) * 2 <= 40 else 1
    elif kind == "emote":
        e = EMOTES[iid]
        grid, sc = [r[4:20] for r in head_rows(e["eyes"], e["mouth"])[7:13]], 3
    elif kind == "pal":
        if iid == "frog":
            grid, pal, sc = FROG_SIT, FROG_PAL, 2
        else:
            grid, pal, sc = dog_grid(("stand", 0, "closed", 0)), DOG_PAL, 2
    else:
        return None
    _ICONS[key] = grid_to_image(grid, pal, False, sc)
    return _ICONS[key]


# ===========================================================================
#  ARAYÜZ METİNLERİ (EN / TR / PL)  +  PİKSEL MENÜ İKONLARI
# ===========================================================================
LANG = ["en"]
UI_TXT = {
    "tr": {
        "~ What now? ~": "~ Şimdi ne? ~", "Dance": "Dans", "Sleep": "Uyu", "Kiss": "Öp",
        "Wave": "El salla", "Jump": "Zıpla", "Spin": "Dön", "Run": "Koş", "Hug": "Sarıl",
        "Bag": "Çanta", "Notes": "Notlar", "Settings": "Ayarlar", "Quit": "Çık",
        "~ Settings ~": "~ Ayarlar ~", "Lang": "Dil", "Chatter": "Konuş", "Climb": "Tırman",
        "Climb n/a": "Tırman yok", "Flash": "Flaş", "Phone": "Telefon", "Link": "Bağlantı",
        "Back": "Geri", "Calm": "Sakin", "~ Style ~": "~ Stil ~",
        "Hats": "Şapka", "Eyes": "Göz", "Wear": "Giyim", "Gear": "Takı", "Desk": "Masa",
        "Emote": "Emote", "Fun": "Oyun",
        "Crown": "Taç", "Party": "Parti", "Red Cap": "Kırmızı", "Phones": "Kulaklık",
        "Beanie": "Bere", "Bunny": "Tavşan", "Cowboy": "Kovboy", "Flowers": "Çiçek",
        "Cat Ears": "Kedi", "Big Bow": "Fiyonk", "Santa": "Noel", "Straw Hat": "Hasır",
        "Halo": "Halka", "None": "Yok", "Shades": "Güneş", "Hearts": "Kalp", "Specs": "Gözlük",
        "Round": "Yuvarlak", "Stars": "Yıldız", "Deal": "Deal",
        "Hoodie": "Kapüşon", "Jacket": "Ceket", "Raincoat": "Yağmurluk", "Sweater": "Kazak",
        "Mint Tee": "Nane", "Sailor": "Denizci", "Lavender": "Lavanta",
        "Heart Tee": "Kalpli", "Overalls": "Salopet", "Cardigan": "Hırka", "Candy": "Şeker",
        "Scarf": "Atkı", "Bow Tie": "Papyon", "Choker": "Gerdanlık", "Beads": "Boncuk",
        "Ribbon": "Kurdele", "Locket": "Madalyon", "Coffee": "Kahve", "Boba": "Boba",
        "Ice Cream": "Dondurma", "Rose": "Gül", "Lollipop": "Lolipop", "Balloon": "Balon",
        "Plant": "Bitki", "Tea Mug": "Çay", "Lamp": "Lamba", "Radio": "Radyo",
        "Armchair": "Koltuk", "Mirror": "Ayna", "Cupcake": "Kek", "Teddy": "Ayıcık",
        "Books": "Kitaplar", "Cactus": "Kaktüs", "Corner": "Köşe",
        "Love": "Aşk", "Wow": "Vay", "Wink": "Göz kır", "Shy": "Utan", "Laugh": "Gül",
        "Super!": "Süper!", "Cry": "Ağla", "Grr": "Grr", "Dizzy": "Sersem", "Shock": "Şok",
        "Frog": "Kurbağa", "Lila": "Lila", "RPS": "TKM", "Fetch": "Getir", "Chaos": "Kaos",
        "Clear outfit": "Hepsini çıkar", "Close": "Kapat",
        "hover to preview · click to wear": "üzerine gel: önizle · tıkla: tak",
        "click an emote to play it": "bir emote seç, oynasın",
        "pals and games": "arkadaşlar ve oyunlar",
        "~ Rock Paper Scissors ~": "~ Taş Kağıt Makas ~", "You win!": "Kazandın!",
        "Pocket K wins!": "Pocket K kazandı!", "Tie!": "Berabere!",
        "You %d   K %d   Tie %d": "Sen %d   K %d   Ber. %d", "PHONE": "TELEFON", "YOU": "SEN",
        "waiting...": "bekleniyor...", "Rock": "Taş", "Paper": "Kağıt", "Scissors": "Makas",
        "vs Phone": "Telefona karşı", "vs Pocket K": "Pocket K'ye karşı",
        "~ Notes (%d open) ~": "~ Notlar (%d açık) ~", "Add": "Ekle",
        "Nothing yet. Type a note above!\n(\"18:30 call mom\" sets a reminder)":
            "Henüz yok. Yukarıya not yaz!\n(\"18:30 annemi ara\" hatırlatıcı kurar)",
        "▼ %d more": "▼ %d tane daha", "Clear done": "Bitenleri sil",
    },
    "pl": {
        "~ What now? ~": "~ Co teraz? ~", "Dance": "Taniec", "Sleep": "Spać", "Kiss": "Buziak",
        "Wave": "Pomachaj", "Jump": "Skok", "Spin": "Obrót", "Run": "Biegaj", "Hug": "Przytul",
        "Bag": "Torba", "Notes": "Notatki", "Settings": "Opcje", "Quit": "Wyjdź",
        "~ Settings ~": "~ Ustawienia ~", "Lang": "Język", "Chatter": "Gadanie",
        "Climb": "Wspinaj", "Climb n/a": "Brak wsp.", "Flash": "Flesz", "Phone": "Telefon",
        "Link": "Link", "Back": "Wstecz", "Calm": "Spokój", "~ Style ~": "~ Styl ~",
        "Hats": "Czapki", "Eyes": "Oczy", "Wear": "Strój", "Gear": "Dodat.", "Desk": "Biurko",
        "Emote": "Emocje", "Fun": "Zabawa",
        "Crown": "Korona", "Party": "Imprezowa", "Red Cap": "Czerwona", "Phones": "Słuchawki",
        "Beanie": "Czapka", "Bunny": "Króliczek", "Cowboy": "Kowboj", "Flowers": "Kwiaty",
        "Cat Ears": "Kocie", "Big Bow": "Kokarda", "Santa": "Mikołaj", "Straw Hat": "Słomkowy",
        "Halo": "Aureola", "None": "Brak", "Shades": "Ciemne", "Hearts": "Serca", "Specs": "Okulary",
        "Round": "Okrągłe", "Stars": "Gwiazdki", "Deal": "Deal",
        "Hoodie": "Bluza", "Jacket": "Kurtka", "Raincoat": "Płaszcz", "Sweater": "Sweter",
        "Mint Tee": "Miętowa", "Sailor": "Marynarz", "Lavender": "Lawenda",
        "Heart Tee": "W serca", "Overalls": "Ogrodn.", "Cardigan": "Kardigan", "Candy": "Cukierek",
        "Scarf": "Szalik", "Bow Tie": "Muszka", "Choker": "Choker", "Beads": "Korale",
        "Ribbon": "Wstążka", "Locket": "Medalion", "Coffee": "Kawa", "Boba": "Boba",
        "Ice Cream": "Lody", "Rose": "Róża", "Lollipop": "Lizak", "Balloon": "Balon",
        "Plant": "Roślina", "Tea Mug": "Herbata", "Lamp": "Lampa", "Radio": "Radio",
        "Armchair": "Fotel", "Mirror": "Lustro", "Cupcake": "Babeczka", "Teddy": "Miś",
        "Books": "Książki", "Cactus": "Kaktus", "Corner": "Róg",
        "Love": "Miłość", "Wow": "Wow", "Wink": "Mrugnij", "Shy": "Wstyd", "Laugh": "Śmiech",
        "Super!": "Super!", "Cry": "Płacz", "Grr": "Grr", "Dizzy": "Zawrót", "Shock": "Szok",
        "Frog": "Żabka", "Lila": "Lila", "RPS": "KPN", "Fetch": "Aport", "Chaos": "Chaos",
        "Clear outfit": "Zdejmij wszystko", "Close": "Zamknij",
        "hover to preview · click to wear": "najedź: podgląd · kliknij: załóż",
        "click an emote to play it": "kliknij emocję, a ją zagra",
        "pals and games": "przyjaciele i gry",
        "~ Rock Paper Scissors ~": "~ Kamień Papier Nożyce ~", "You win!": "Wygrałaś!",
        "Pocket K wins!": "Pocket K wygrywa!", "Tie!": "Remis!",
        "You %d   K %d   Tie %d": "Ty %d   K %d   Rem. %d", "PHONE": "TELEFON", "YOU": "TY",
        "waiting...": "czekam...", "Rock": "Kamień", "Paper": "Papier", "Scissors": "Nożyce",
        "vs Phone": "z telefonem", "vs Pocket K": "z Pocket K",
        "~ Notes (%d open) ~": "~ Notatki (%d otwarte) ~", "Add": "Dodaj",
        "Nothing yet. Type a note above!\n(\"18:30 call mom\" sets a reminder)":
            "Jeszcze nic. Wpisz notatkę powyżej!\n(\"18:30 zadzwoń do mamy\" ustawia przypomnienie)",
        "▼ %d more": "▼ jeszcze %d", "Clear done": "Usuń zrobione",
    },
}


def L(txt, lang=None):
    """Arayüz metnini seçili dile çevirir (bilinmeyen metin olduğu gibi kalır)."""
    return UI_TXT.get(lang or LANG[0], {}).get(txt, txt)


_MENU_PAL = {"o": "#3a1f1c", "c": "#e8742a", "r": "#e63946", "p": "#ff7aa2", "y": "#ffd23f",
             "Y": "#f2a900", "b": "#3a86ff", "B": "#8fd3ff", "w": "#ffffff", "g": "#58b368",
             "u": "#8a3ffc", "k": "#9a6a35", "n": "#f6d9b8"}
UI_TXT["tr"].update({
    "Treat": "Kuru et", "Witch": "Cadı", "Pumpkin": "Bal kabağı", "Chat": "Sohbet",
    "Game mode": "Oyun modu", "Auto hide": "Oto gizle", "~ Chat ~": "~ Sohbet ~", "Send": "Gönder",
    "Close": "Kapat", "pals and games": "dostlar ve oyunlar",
    "No messages yet. Turn on Settings > Phone\nand write from the phone, or type here!":
        "Henüz mesaj yok. Ayarlar > Telefon'u aç,\ntelefondan yaz ya da buraya yaz!",
    "Phone link is off: messages wait here.": "Telefon bağlantısı kapalı: mesajlar burada bekler.",
})
UI_TXT["pl"].update({
    "Treat": "Gryzak", "Witch": "Wiedźma", "Pumpkin": "Dynia", "Chat": "Czat",
    "Game mode": "Tryb gry", "Auto hide": "Auto ukryj", "~ Chat ~": "~ Czat ~", "Send": "Wyślij",
    "Close": "Zamknij", "pals and games": "przyjaciele i gry",
    "No messages yet. Turn on Settings > Phone\nand write from the phone, or type here!":
        "Brak wiadomości. Włącz Opcje > Telefon\ni pisz z telefonu albo tutaj!",
    "Phone link is off: messages wait here.": "Telefon wyłączony: wiadomości czekają tutaj.",
})


MENU_ICONS = {
    "dance": ["....oo...", "....o.o..", "....o..o.", "....o....", "....o....", "..ooo....",
              ".ouuo....", ".ouuo....", "..oo....."],
    "sleep": ["ooooo....", "...o.....", "..o......", ".o....ooo", "ooooo..o.", "......ooo"],
    "kiss": [".ooo.ooo.", "orrrorrro", "oprrrrrro", ".orrrrro.", "..orrro..", "...oro...", "....o...."],
    "wave": ["..ooooo..", ".oyyyyyo.", "oyyyyyyyo", "oyoyyyoyo", "oyyyyyyyo", "oyoyyyoyo",
             ".oyoooyo.", "..ooooo.."],
    "jump": ["....c....", "...ccc...", "..ccccc..", ".ccccccc.", "...ccc...", "...ccc...",
             "...ccc...", "...ccc..."],
    "spin": ["....o....", "....o....", "...oyo...", "ooooyoooo", "...oyo...", "....o....", "....o...."],
    "run": ["cc..cc...", ".cc..cc..", "..cc..cc.", "...cc..cc", "..cc..cc.", ".cc..cc..", "cc..cc..."],
    "hug": [".ooo.ooo.", "owwwowwwo", "owwwwwwwo", ".owwwwwo.", "..owwwo..", "...owo...", "....o...."],
    "bag": ["...ooo...", "..o...o..", ".ooooooo.", "orrrrrrro", "orrrrrrro", "orrywyrro",
            "orrrrrrro", ".ooooooo."],
    "notes": [".ooooooo.", ".owwwwwo.", ".owbbbwo.", ".owwwwwo.", ".owbbbwo.", ".owwwwwo.",
              ".owbbwwo.", ".ooooooo."],
    "settings": [".........", "ooorrrooo", ".........", "rrrooooo.", ".........", "oooorrroo", "........."],
    "quit": ["r.......r", ".r.....r.", "..r...r..", "...r.r...", "....r....", "...r.r...",
             "..r...r..", ".r.....r.", "r.......r"],
    "lang": ["ooooooooo", "owwwwwwwo", "owwoooowo", "owowwowwo", "owooooowo", "owowwwowo",
             "owwwwwwwo", ".ooooooo.", "..oo....."],
    "chat": [".ooooooo.", "owwwwwwwo", "owowowowo", "owwwwwwwo", ".ooooooo.", "..oo....."],
    "climb": ["....g....", "...ggg...", "..ggggg..", ".ggggggg.", "ggggggggg"],
    "flash": ["....y....", "....y....", "...yyy...", "yyyyoyyyy", "...yyy...", "....y....", "....y...."],
    "remote": ["..ooooo..", "..obbbo..", "..obbbo..", "..obbbo..", "..obbbo..", "..ooooo..", "..oroo.."],
    "pair": ["ooooooooo", "oo.....oo", "o.o...o.o", "o..o.o..o", "o...o...o", "o.......o", "ooooooooo"],
    "back": ["...c.....", "..cc.....", ".ccccccc.", "..cc.....", "...c....."],
}
MENU_ICONS["calm"] = MENU_ICONS["sleep"]
MENU_ICONS.update({
    "msgs": [".ooooooo.", "oxxxxxxxo", "oxwwxwwxo", "oxxxxxxxo", ".oooooxo.", ".....oo..", "......o.."],
    "hide": ["ooooooooo", "owwwwwwwo", "owwwwwwwo", "ooooooooo", "....o....", "..ooooo..",
             "........."],
    "autohide": ["ooooooooo", "obbbbbbbo", "obbbbbbbo", "obbbbbbbo", "ooooooooo", "...ooo..."],
})
MENU_ICONS.update({
    "check": ["......GG.", ".GG..GG..", "..GGGG...", "...GG...."],
    "box_off": ["ooooooooo"] + ["owwwwwwwo"] * 7 + ["ooooooooo"],
    "box_on": ["ooooooooo", "owwwwwwwo", "owwwwwwwo", "owwwwwwGo", "owGwwwGwo", "owwGwGwwo",
               "owwwGwwwo", "owwwwwwwo", "ooooooooo"],
    "x": ["m.....m", ".m...m.", "..m.m..", "...m...", "..m.m..", ".m...m.", "m.....m"],
    "none": ["a.......a", ".a.....a.", "..a...a..", "...a.a...", "....a....", "...a.a...",
             "..a...a..", ".a.....a.", "a.......a"],
    "corner": ["a........", "a........", "a........", "a..bb.cc.", "a..bb.cc.", "aaaaaaaaa"],
})
_MENU_PAL.update({"G": "#2a9d5c", "m": "#c2476b", "a": "#a08a7a"})
_MENU_IMG = {}


def menu_icon(cid, sc=2):
    g = MENU_ICONS.get(cid)
    if not g:
        return None
    im = _MENU_IMG.get((cid, sc))
    if im is None:
        w = max(len(r) for r in g)
        im = _MENU_IMG[(cid, sc)] = grid_to_image([r.ljust(w, ".") for r in g], _MENU_PAL, False, sc)
    return im


class BubbleBase:
    """Ortak balon: pencere, kuyruk, açılış/kapanış animasyonu, otomatik kapanma."""
    M, TAIL = 16, 15

    def __init__(self, pet, cx, top_y, bw, bh, gentle=False):
        self.pet, self.bw, self.bh, self.gentle = pet, bw, bh, gentle
        self.ww = bw + 2 * self.M
        self.wh = bh + self.TAIL + 2 * self.M
        x = max(0, min(cx - self.ww // 2, pet.sw - self.ww))
        self.tx = cx - x
        ty = self.M + bh + self.TAIL
        y = max(0, top_y - ty)
        self.tip = (self.tx, ty)
        self.tail_x = max(self.M + 26, min(self.tx, self.M + bw - 26))

        w = self.win = tk.Toplevel(pet.root)
        w.overrideredirect(True)
        w.wm_attributes("-topmost", True)
        make_transparent(w)
        try:
            w.attributes("-alpha", 0.0)
        except tk.TclError:
            pass
        w.geometry(f"{self.ww}x{self.wh}+{int(x)}+{int(y)}")
        self.winx, self.winy = x, y
        self.cv = tk.Canvas(w, width=self.ww, height=self.wh, bg=KEY,
                            highlightthickness=0)
        self.cv.pack()
        self.hover = -1
        self.t = 0.0
        self.state = "open"
        self.choice = None
        self.outside = 0
        cv = self.cv
        cv.bind("<Motion>", self.on_move)
        cv.bind("<Leave>", self.on_leave)
        cv.bind("<Button-1>", self.on_click)
        cv.bind("<MouseWheel>", lambda e: self.on_wheel(-1 if e.delta > 0 else 1))
        cv.bind("<Button-4>", lambda e: self.on_wheel(-1))
        cv.bind("<Button-5>", lambda e: self.on_wheel(1))
        w.bind("<Escape>", lambda e: self.close())
        try:
            w.focus_force()
        except tk.TclError:
            pass
        self.animate()
        w.after(250, self.poll)

    # --- çizim yardımcıları -------------------------------------------
    def _sc(self, px, py, s):
        tx, ty = self.tip
        return tx + (px - tx) * s, ty + (py - ty) * s

    def rect(self, x1, y1, x2, y2, fill, s):
        a = self._sc(x1, y1, s)
        b = self._sc(x2, y2, s)
        self.cv.create_rectangle(a[0], a[1], b[0], b[1], fill=fill, outline="", tags="ui")

    def pixrect(self, x1, y1, x2, y2, fill, c, s):
        a = self._sc(x1, y1, s)
        b = self._sc(x2, y2, s)
        c = max(1, c * s)
        cv = self.cv
        cv.create_rectangle(a[0] + c, a[1], b[0] - c, b[1], fill=fill, outline="", tags="ui")
        cv.create_rectangle(a[0], a[1] + c, b[0], b[1] - c, fill=fill, outline="", tags="ui")

    def text(self, x, y, s, txt, fill, font, anchor="center", tr=True):
        sx, sy = self._sc(x, y, s)
        if tr:
            txt = L(txt)
        self.cv.create_text(sx, sy, text=txt, fill=fill, font=font, anchor=anchor, tags="ui")

    def image(self, x, y, s, img):
        sx, sy = self._sc(x, y, s)
        self.cv.create_image(sx, sy, image=img, tags="ui")

    def draw_frame(self, s):
        M = self.M
        x1, y1, x2, y2 = M, M, M + self.bw, M + self.bh
        self.pixrect(x1 + 4, y1 + 5, x2 + 4, y2 + 5, B_SHADOW, 6, s)
        for hw, yy in [(16, y2 - 2), (11, y2 + 4), (6, y2 + 9)]:
            for grow, col in ((3, B_OUT), (0, B_FILL)):
                self.rect(self.tail_x - hw - grow, yy - (grow and 1),
                          self.tail_x + hw + grow, yy + 6 + grow, col, s)
        self.pixrect(x1 - 3, y1 - 3, x2 + 3, y2 + 3, B_OUT, 8, s)
        self.pixrect(x1, y1, x2, y2, B_FILL, 6, s)
        for hw, yy in [(13, y2 - 4), (8, y2 + 4), (3, y2 + 9)]:
            self.rect(self.tail_x - hw, yy, self.tail_x + hw, yy + 6, B_FILL, s)

    def draw(self, s, t):
        self.cv.delete("ui")
        if s < 0.05:
            return
        self.draw_frame(s)
        if s >= (0.9 if self.gentle else 0.6):
            self.content(s, t)

    def content(self, s, t):
        pass

    # --- animasyon ----------------------------------------------------
    def ease_open(self, t):
        if self.gentle:                              # ince, zarif büyüme
            return 0.9 + 0.1 * (1 - (1 - t) ** 3)
        return _out_back(t)

    def animate(self):
        if not self.win.winfo_exists():
            return
        if self.state == "open":
            self.t = min(1.0, self.t + (1 / 9 if self.gentle else 1 / 12))
            s = self.ease_open(self.t)
            if self.t >= 1.0:
                self.state = "idle"
                s = 1.0
                self.on_ready()
        elif self.state == "closing":
            self.t = max(0.0, self.t - (1 / 6 if self.gentle else 1 / 7))
            s = (0.92 + 0.08 * self.t) if self.gentle else self.t ** 2
            if self.t <= 0:
                self.finish()
                return
        else:
            s = 1.0
        try:
            self.win.attributes("-alpha", min(1.0, self.t * 2.2))
        except tk.TclError:
            pass
        self.draw(s, self.t if self.state != "idle" else 1.0)
        self.win.after(16, self.animate)

    def close(self, choice=None):
        if self.state == "closing":
            return
        self.choice = choice
        self.state = "closing"
        self.t = min(self.t, 1.0)
        self.on_closing()

    def finish(self):
        try:
            self.win.destroy()
        except tk.TclError:
            pass
        self.pet.bubble_closed(self.choice)

    # --- kancalar -----------------------------------------------------
    def on_ready(self):
        pass

    def on_closing(self):
        pass

    def on_move(self, e):
        pass

    def on_leave(self, e):
        self.hover = -1

    def on_click(self, e):
        pass

    def on_wheel(self, d):
        pass

    def keep_open(self):
        return False

    def poll(self):
        if not self.win.winfo_exists() or self.state == "closing":
            return
        px, py = self.win.winfo_pointerx(), self.win.winfo_pointery()
        m = 60
        inside = (self.winx - m <= px <= self.winx + self.ww + m and
                  self.winy - m <= py <= self.winy + self.wh + m)
        near_pet = (self.pet.x <= px <= self.pet.x + self.pet.cw and
                    self.pet.y <= py <= self.pet.y + self.pet.ch)
        self.outside = 0 if (inside or near_pet or self.keep_open()) else self.outside + 1
        if self.outside >= 12:      # ~3 sn dışarıdaysa kapan
            self.close()
            return
        self.win.after(250, self.poll)


class Bubble(BubbleBase):
    """Izgara butonlu menü (ana menü, ayarlar). label bir fonksiyon da olabilir."""
    BH, GAP, PAD, TITLE = 34, 6, 12, 24

    def __init__(self, pet, cx, top_y, items, title, cols=3, btnw=92,
                 equipped=None, stay=None):
        self.items, self.title, self.cols, self.BW = items, title, cols, btnw
        self.equipped, self.stay = equipped, stay
        rows = math.ceil(len(items) / cols)
        bw = cols * btnw + (cols - 1) * self.GAP + 2 * self.PAD
        bh = self.TITLE + rows * self.BH + (rows - 1) * self.GAP + 2 * self.PAD
        super().__init__(pet, cx, top_y, bw, bh)

    def _btn_rect(self, i):
        col, row = i % self.cols, i // self.cols
        x = self.M + self.PAD + col * (self.BW + self.GAP)
        y = self.M + self.PAD + self.TITLE + row * (self.BH + self.GAP)
        return x, y, x + self.BW, y + self.BH

    def content(self, s, t):
        M = self.M
        a = max(0, min(1, (t - 0.3) / 0.25))
        self.text(M + self.bw / 2, M + self.PAD + 9, s, self.title,
                  _lerp(B_FILL, TITLE_C, a), ("Courier New", 11, "bold"))
        for i, (ico, label, cid) in enumerate(self.items):
            a = max(0, min(1, (t - 0.35 - i * 0.04) / 0.22))
            if a <= 0:
                continue
            bx1, by1, bx2, by2 = self._btn_rect(i)
            off = (1 - a) * 9
            by1 += off
            by2 += off
            on = bool(self.equipped and self.equipped(cid))
            hov = (i == self.hover and self.state == "idle")
            fill = BTN_HOVER if hov else (BTN_ON if on else BTN_FILL)
            fill = _lerp(B_FILL, fill, a)
            edge = _lerp(B_FILL, B_OUT, a)
            if hov:
                by1 -= 2
                by2 -= 2
            self.pixrect(bx1 - 2, by1 - 2, bx2 + 2, by2 + 2, edge, 4, s)
            self.pixrect(bx1, by1, bx2, by2, fill, 3, s)
            cy = (by1 + by2) / 2
            pic = menu_icon(cid)
            if pic is not None:
                self.image(bx1 + 19, cy + (-1 if hov else 0), s, pic)
            else:
                self.text(bx1 + 17, cy, s, ico, _lerp(B_FILL, TITLE_C, a), ("Arial", 14, "bold"))
            lab = L(label() if callable(label) else label)
            avail = self.BW - 40 - (22 if self.equipped else 4)
            fsz = 10 if len(lab) * 8 <= avail else 9 if len(lab) * 7.3 <= avail else 8
            self.text(bx1 + 36, cy, s, lab, _lerp(B_FILL, TXT, a),
                      ("Courier New", fsz, "bold"), "w", tr=False)
            if on:
                self.image(bx2 - 14, cy, s, menu_icon("check", 2))

    def hit(self, x, y):
        for i in range(len(self.items)):
            x1, y1, x2, y2 = self._btn_rect(i)
            if x1 <= x <= x2 and y1 <= y <= y2:
                return i
        return -1

    def on_move(self, e):
        if self.state == "idle":
            self.hover = self.hit(e.x, e.y)
            self.cv.config(cursor="hand2" if self.hover >= 0 else "")

    def on_click(self, e):
        if self.state != "idle":
            return
        i = self.hit(e.x, e.y)
        if i < 0:
            return
        cid = self.items[i][2]
        if self.stay and self.stay(cid):      # balon açık kalır
            self.pet.use_item(cid)
        else:
            self.close(cid)


# ---------------------------------------------------------------------------
#  BAG: sekmeli kıyafet / aksesuar / masa objesi paneli (ince büyüme efekti)
# ---------------------------------------------------------------------------
#  EMOTE'LAR: göz / ağız ifadesi + parçacık + replik (Pet.emote_pose çizer)
EMOTES = {
    "love":  dict(label="Love", eyes="heart", mouth="smile", dur=110),
    "wow":   dict(label="Wow", eyes="star", mouth="open", dur=90),
    "wink":  dict(label="Wink", eyes="wink", mouth="grin", dur=80),
    "shy":   dict(label="Shy", eyes="shy", mouth="smile", dur=110),
    "laugh": dict(label="Laugh", eyes="happy", mouth="laugh", dur=110),
    "super": dict(label="Super!", eyes="star", mouth="grin", dur=100),
    "cry":   dict(label="Cry", eyes="cry", mouth="wavy", dur=110),
    "angry": dict(label="Grr", eyes="annoyed", mouth="wavy", dur=100),
    "dizzy": dict(label="Dizzy", eyes="dizzy", mouth="wavy", dur=110),
    "shock": dict(label="Shock", eyes="wide", mouth="open", dur=80),
}


AUTO_EMOTES = ["love", "wink", "laugh", "wow", "shy", "super", "shock"]   # kendiliğinden oynayanlar

STYLE_TABS = [
    ("Hats", "hat", [("worn", "crown", "Crown"), ("worn", "party", "Party"),
                     ("worn", "cap", "Red Cap"), ("worn", "phones", "Phones"),
                     ("worn", "beanie", "Beanie"), ("worn", "bunny", "Bunny"),
                     ("worn", "cowboy", "Cowboy"), ("worn", "flowers", "Flowers"),
                     ("worn", "catears", "Cat Ears"), ("worn", "bow", "Big Bow"),
                     ("worn", "santa", "Santa"), ("worn", "strawhat", "Straw Hat"),
                     ("worn", "halo", "Halo"), ("worn", "witch", "Witch"), ("clear", "hat", "None")]),
    ("Eyes", "glasses", [("worn", "shades", "Shades"), ("worn", "hearts", "Hearts"),
                         ("worn", "specs", "Specs"), ("worn", "round", "Round"),
                         ("worn", "stars", "Stars"), ("worn", "pixel", "Deal"),
                         ("clear", "glasses", "None")]),
    ("Wear", "outfit", [("worn", "hoodie", "Hoodie"), ("worn", "jacket", "Jacket"),
                        ("worn", "raincoat", "Raincoat"), ("worn", "sweater", "Sweater"),
                        ("worn", "mint", "Mint Tee"), ("worn", "sailor", "Sailor"),
                        ("worn", "lavender", "Lavender"), ("worn", "heart", "Heart Tee"),
                        ("worn", "overalls", "Overalls"), ("worn", "cardigan", "Cardigan"),
                        ("worn", "candy", "Candy"), ("clear", "outfit", "None")]),
    ("Gear", "neck", [("worn", "scarf", "Scarf"), ("worn", "bowtie", "Bow Tie"),
                      ("worn", "choker", "Choker"), ("worn", "beads", "Beads"),
                      ("worn", "ribbon", "Ribbon"), ("worn", "locket", "Locket"),
                      ("worn", "coffee", "Coffee"), ("worn", "boba", "Boba"),
                      ("worn", "icecream", "Ice Cream"), ("worn", "rose", "Rose"),
                      ("worn", "lollipop", "Lollipop"), ("worn", "balloon", "Balloon"),
                      ("worn", "pumpkin", "Pumpkin"),
                      ("phone", "phone", "Phone"), ("clear", "gear", "None")]),
    ("Desk", "prop", [("prop", "plant", "Plant"), ("prop", "mug", "Tea Mug"),
                      ("prop", "lamp", "Lamp"),
                      ("prop", "radio", "Radio"), ("prop", "chair", "Armchair"),
                      ("prop", "mirror", "Mirror"), ("prop", "cupcake", "Cupcake"),
                      ("prop", "teddy", "Teddy"), ("prop", "books", "Books"),
                      ("prop", "cactus", "Cactus"), ("corner", "corner", "Corner")]),
    ("Emote", "emote", [("emote", e, EMOTES[e]["label"]) for e in EMOTES]),
    ("Fun", "fun", [("pal", "frog", "Frog"), ("pal", "lila", "Lila"),
                    ("game", "rps", "RPS"), ("game", "ball", "Fetch"),
                    ("game", "chaos", "Chaos"), ("game", "treat", "Treat")]),
]


class StylePanel(BubbleBase):
    PAD, TITLE, TABH, TW, TH, GAP, COLS, ROWS, FOOT = 12, 22, 24, 68, 58, 6, 5, 3, 26
    TABW = 50

    def __init__(self, pet, cx, top_y):
        gw = self.COLS * self.TW + (self.COLS - 1) * self.GAP
        n = len(STYLE_TABS)
        self.TABW = (gw - 6 * (n - 1)) // n
        bw = gw + 2 * self.PAD
        bh = (self.PAD + self.TITLE + self.TABH + 8 + self.ROWS * self.TH +
              (self.ROWS - 1) * self.GAP + 8 + self.FOOT + self.PAD)
        self.tab = pet.style_tab
        self.hover_tab = -1
        super().__init__(pet, cx, top_y, bw, bh, gentle=True)

    def tiles(self):
        return STYLE_TABS[self.tab][2]

    def tab_rect(self, i):
        x = self.M + self.PAD + i * (self.TABW + 6)
        y = self.M + self.PAD + self.TITLE
        return x, y, x + self.TABW, y + self.TABH

    def tile_rect(self, i):
        c, r = i % self.COLS, i // self.COLS
        x = self.M + self.PAD + c * (self.TW + self.GAP)
        y = self.M + self.PAD + self.TITLE + self.TABH + 8 + r * (self.TH + self.GAP)
        return x, y, x + self.TW, y + self.TH

    def foot_rects(self):
        y = self.M + self.bh - self.PAD - self.FOOT
        x1 = self.M + self.PAD
        w = (self.bw - 2 * self.PAD - 6) / 2
        return [(x1, y, x1 + w, y + self.FOOT), (x1 + w + 6, y, x1 + 2 * w + 6, y + self.FOOT)]

    def content(self, s, t):
        M, pet = self.M, self.pet
        self.text(M + self.bw / 2, M + self.PAD + 8, s, "~ Style ~", TITLE_C,
                  ("Courier New", 11, "bold"))
        for i, (name, _slot, _tl) in enumerate(STYLE_TABS):
            x1, y1, x2, y2 = self.tab_rect(i)
            act = (i == self.tab)
            fill = BTN_ON if act else (BTN_HOVER if i == self.hover_tab else BTN_FILL)
            self.pixrect(x1 - 2, y1 - 2, x2 + 2, y2 + 2, B_OUT, 4, s)
            self.pixrect(x1, y1, x2, y2, fill, 3, s)
            self.text((x1 + x2) / 2, (y1 + y2) / 2, s, name, TXT, ("Courier New", 9, "bold"))
        for i, (kind, iid, label) in enumerate(self.tiles()):
            x1, y1, x2, y2 = self.tile_rect(i)
            on = pet.is_on(kind, iid)
            hov = (i == self.hover and self.state == "idle")
            fill = BTN_HOVER if hov else (BTN_ON if on else BTN_FILL)
            self.pixrect(x1 - 2, y1 - 2, x2 + 2, y2 + 2, B_OUT, 4, s)
            self.pixrect(x1, y1, x2, y2, fill, 3, s)
            cx, cy = (x1 + x2) / 2, y1 + 23
            if kind == "worn":
                img = icon_image(SLOT_OF[iid], iid)
            elif kind in ("phone", "prop", "pal", "emote"):
                img = icon_image(kind, iid)
            elif kind == "game":
                img = game_icon(iid)
            else:
                img = None
            if img is not None:
                self.image(cx, cy, s, img)
            else:
                self.image(cx, cy, s, menu_icon("corner" if kind == "corner" else "none", 3))
            self.text(cx, y2 - 9, s, label, TXT, ("Courier New", 8, "bold"))
            if on:
                self.image(x2 - 11, y1 + 9, s, menu_icon("check", 2))
        used = -(-len(self.tiles()) // self.COLS)
        if used < self.ROWS:                                 # boş kalan alana küçük ipucu
            tip = {"emote": "click an emote to play it", "fun": "pals and games"}.get(
                STYLE_TABS[self.tab][1], "hover to preview · click to wear")
            ty = self.tile_rect((self.ROWS - 1) * self.COLS)[1] + self.TH / 2 - 6
            n = sum(pet.found.values())
            if STYLE_TABS[self.tab][1] == "fun" and n:
                tip = L(tip) + "  ·  ♥ " + str(n)
                self.text(M + self.bw / 2, ty, s, tip, "#b49a8a", ("Courier New", 8, "bold"), tr=False)
            else:
                self.text(M + self.bw / 2, ty, s, tip, "#b49a8a", ("Courier New", 8, "bold"))
        for (x1, y1, x2, y2), lab, j in zip(self.foot_rects(), ("Clear outfit", "Close"), (0, 1)):
            hov = (self.hover == 100 + j)
            self.pixrect(x1 - 2, y1 - 2, x2 + 2, y2 + 2, B_OUT, 4, s)
            self.pixrect(x1, y1, x2, y2, BTN_HOVER if hov else BTN_FILL, 3, s)
            self.text((x1 + x2) / 2, (y1 + y2) / 2, s, lab, TXT, ("Courier New", 9, "bold"))

    def hit(self, x, y):
        for i in range(len(STYLE_TABS)):
            x1, y1, x2, y2 = self.tab_rect(i)
            if x1 <= x <= x2 and y1 <= y <= y2:
                return ("tab", i)
        for i in range(len(self.tiles())):
            x1, y1, x2, y2 = self.tile_rect(i)
            if x1 <= x <= x2 and y1 <= y <= y2:
                return ("tile", i)
        for j, (x1, y1, x2, y2) in enumerate(self.foot_rects()):
            if x1 <= x <= x2 and y1 <= y <= y2:
                return ("foot", j)
        return (None, -1)

    def on_move(self, e):
        if self.state != "idle":
            return
        kind, i = self.hit(e.x, e.y)
        self.hover_tab = i if kind == "tab" else -1
        self.hover = i if kind == "tile" else (100 + i if kind == "foot" else -1)
        self.cv.config(cursor="hand2" if kind else "")
        self.pet.preview.clear()                     # anlık önizleme
        if kind == "tile":
            tk_, iid, _ = self.tiles()[i]
            if tk_ == "worn":
                self.pet.preview[SLOT_OF[iid]] = iid
            elif tk_ == "clear":
                if iid == "gear":
                    self.pet.preview["neck"] = ""
                    self.pet.preview["held"] = ""
                else:
                    self.pet.preview[iid] = ""

    def on_leave(self, e):
        self.hover = self.hover_tab = -1
        self.pet.preview.clear()

    def on_closing(self):
        self.pet.preview.clear()

    def keep_open(self):
        return bool(self.pet.chaos)

    def on_click(self, e):
        if self.state != "idle":
            return
        kind, i = self.hit(e.x, e.y)
        if kind == "tab":
            self.tab = self.pet.style_tab = i
        elif kind == "tile":
            tk_, iid, _ = self.tiles()[i]
            self.pet.preview.clear()
            if tk_ == "phone":
                self.close("phone")
            elif tk_ == "game":
                self.close("game_" + iid)
            elif tk_ == "emote":                    # panel kapanır, ifade görünür
                self.close("emote_" + iid)
            else:
                self.pet.tile_action(tk_, iid)
        elif kind == "foot":
            if i == 0:
                self.pet.preview.clear()
                self.pet.clear_worn()
            else:
                self.close()


# ---------------------------------------------------------------------------
#  TAŞ-KAĞIT-MAKAS  (el çizimleri + oyun paneli)
# ---------------------------------------------------------------------------
HAND_PAL = {"o": "#3a1f1c", "y": "#ffd2b0", "s": "#e8a98a"}
HAND_GRID = {
    "rock": ["............",
             "..oo.oo.oo..",
             ".oyyoyyoyyo.",
             ".oyyyyyyyyoo",
             ".oyysyysyyyo",
             ".oyyyyyyyyyo",
             ".oyyyyyyyyo.",
             "..oyyyyyyyo.",
             "..oyyyyyyo..",
             "...oooooo..."],
    "paper": ["..o.o.o.o...",
              ".oyoyoyoyo..",
              ".oyoyoyoyo..",
              ".oyoyoyoyoo.",
              ".oyyyyyyyyyo",
              ".oyyyyyyyyo.",
              ".oyyyyyyyyo.",
              "..oyyyyyyo..",
              "..oyyyyyyo..",
              "...oooooo..."],
    "scissors": [".oo....oo...",
                 ".oyo..oyo...",
                 ".oyo..oyo...",
                 ".oyo..oyo...",
                 "..oyooyo....",
                 "..oyyyyoo...",
                 ".oyyyyyyyo..",
                 ".oyyyyyyyo..",
                 "..oyyyyyo...",
                 "...ooooo...."],
}
RPS_MOVES = ("rock", "paper", "scissors")
RPS_BEATS = {"rock": "scissors", "paper": "rock", "scissors": "paper"}
_HAND_IMG = {}


def rps_result(you, pet):
    """'you' (oyuncu kazandı) / 'pet' (karakter kazandı) / 'draw'."""
    if you == pet:
        return "draw"
    return "you" if RPS_BEATS[you] == pet else "pet"


def hand_image(kind, scale, flip=False):
    k = (kind, scale, flip)
    im = _HAND_IMG.get(k)
    if im is None:
        im = _HAND_IMG[k] = grid_to_image(HAND_GRID[kind], HAND_PAL, flip, scale)
    return im


class RPSPanel(BubbleBase):
    """Taş-kağıt-makas: seç -> 3-2-1 sayım (karakter yumruk sallar) -> açılış -> tepki."""
    PAD, TITLE, SCORE, ARENA, BTNH, FOOT, BW = 12, 22, 16, 98, 66, 26, 300
    STEP = 0.5                       # sayım hızı (sn / kelime)
    RES = {"you": ("You win!", "#2a9d5c"), "pet": ("Pocket K wins!", "#d62839"),
           "draw": ("Tie!", "#6d6d7a")}

    def __init__(self, pet, cx, top_y):
        self.stage, self.t0 = "pick", time.time()
        self.you = self.pm = self.result = None
        self.duel, self.phone_move = False, None            # düello: rakip telefondaki kişi
        self.quip = pick_line(pet.prefs["lang"], "rps_hi")
        bh = (self.PAD + self.TITLE + self.SCORE + self.ARENA + 8 + self.BTNH + 8 +
              self.FOOT + self.PAD)
        super().__init__(pet, cx, top_y, self.BW, bh, gentle=True)
        pet.rps_pose = self.pose

    # --- geometri
    def arena(self):
        x1 = self.M + self.PAD
        y1 = self.M + self.PAD + self.TITLE + self.SCORE
        return x1, y1, self.M + self.bw - self.PAD, y1 + self.ARENA

    def btn_rect(self, i):
        w = (self.bw - 2 * self.PAD - 16) / 3
        x = self.M + self.PAD + i * (w + 8)
        y = self.arena()[3] + 8
        return x, y, x + w, y + self.BTNH

    def foot_rects(self):
        y = self.M + self.bh - self.PAD - self.FOOT
        x1, x2 = self.M + self.PAD, self.M + self.bw - self.PAD
        mid = (x1 + x2) / 2
        return [(x1, y, mid - 3, y + self.FOOT), (mid + 3, y, x2, y + self.FOOT)]

    # --- oyun mantığı
    def pick(self, move):
        if self.stage != "pick":
            return
        self.you, self.pm = move, (None if self.duel else random.choice(RPS_MOVES))
        self.stage, self.t0 = "count", time.time()
        self.result = None

    def reveal(self):
        pet = self.pet
        phone_picked = self.phone_move is not None
        if self.pm is None:
            self.pm = self.phone_move or random.choice(RPS_MOVES)
        self.result = rps_result(self.you, self.pm)
        self.stage, self.t0 = "reveal", time.time()
        pet.games["rps"][self.result] += 1
        if self.duel and phone_picked:                      # telefondaki kişiye sonucu bildir
            pet.set_phone_rps(self.pm, self.you, {"you": "lose", "pet": "win", "draw": "draw"}[self.result], True)
        key = {"you": "rps_lose", "pet": "rps_win", "draw": "rps_draw"}[self.result]
        self.quip = pick_line(pet.prefs["lang"], key)
        if self.result == "pet":
            pet.love(aff=2, mood=3)
            for _ in range(2):
                pet.spawn("note", PADX + random.choice([2, 28]) * SCALE, PADT + 10 * SCALE)
        elif self.result == "you":
            pet.love(aff=3, mood=-1)
        else:
            pet.love(aff=2)
        pet.save_soon()

    def advance(self):
        el = time.time() - self.t0
        if self.stage == "count" and el >= 4 * self.STEP:
            if self.duel and self.phone_move is None:
                self.stage, self.t0 = "wait", time.time()
            else:
                self.reveal()
        elif self.stage == "wait" and (self.phone_move is not None or el > 12):
            self.reveal()
        elif self.stage == "reveal" and el > 2.3:
            self.stage, self.t0 = "pick", time.time()
            self.you = self.pm = self.phone_move = None

    def pose(self):
        """Karakterin beden dili (Pet.action_pose tarafından çağrılır)."""
        p, t = self.pet, self.pet.t
        if self.stage in ("count", "wait"):
            b = (t // 4) % 2
            return K(eyes=p.eyes(), mouth="smile", ar="u", ard=-b, bdy=b, hdy=b)
        if self.stage == "reveal":
            if self.result == "pet":
                return K(eyes="happy", mouth="grin", al="u", ar="u", alx=(t // 3) % 2,
                         arx=-((t // 3) % 2), hdy=(t // 6) % 2)
            if self.result == "you":
                return K(eyes="annoyed", mouth="kiss", hdx=-1 if (t // 20) % 2 else 0)
            return K(eyes="wide", mouth="open", hdy=(t // 8) % 2)
        return None

    # --- çizim
    def content(self, s, t):
        self.advance()
        M, pet = self.M, self.pet
        el = time.time() - self.t0
        self.text(M + self.bw / 2, M + self.PAD + 9, s, "~ Rock Paper Scissors ~", TITLE_C,
                  ("Courier New", 11, "bold"))
        g = pet.games["rps"]
        self.text(M + self.bw / 2, M + self.PAD + self.TITLE + 8, s,
                  L("You %d   K %d   Tie %d") % (g["you"], g["pet"], g["draw"]), TXT,
                  ("Courier New", 9, "bold"))
        x1, y1, x2, y2 = self.arena()
        self.pixrect(x1 - 2, y1 - 2, x2 + 2, y2 + 2, B_OUT, 4, s)
        self.pixrect(x1, y1, x2, y2, BTN_FILL, 3, s)
        cx, cy = (x1 + x2) / 2, y1 + 38
        lx, rx = x1 + 62, x2 - 62
        self.text(lx, y1 + 11, s, "PHONE" if self.duel else "KAROLINA", TXT, ("Courier New", 8, "bold"))
        self.text(rx, y1 + 11, s, "YOU", TXT, ("Courier New", 8, "bold"))
        bounce = 0.0
        if self.stage == "count":
            bounce = 12 * abs(math.sin(math.pi * el / self.STEP))
        if self.stage in ("pick", "count", "wait"):
            self.image(lx, cy - bounce + 4, s, hand_image("rock", 4, True))
            if self.stage in ("count", "wait"):
                self.image(rx, cy - bounce + 4, s, hand_image("rock", 4))
            else:
                self.text(rx, cy + 4, s, "?", TITLE_C, ("Courier New", 26, "bold"))
        else:
            self.image(lx, cy, s, hand_image(self.pm, 4, True))
            self.image(rx, cy, s, hand_image(self.you, 4))
        if self.stage == "wait":
            self.text(cx, cy, s, "waiting...", TITLE_C, ("Courier New", 10, "bold"))
        elif self.stage == "count":
            words = LINES[pet.prefs["lang"]]["rps_count"]
            self.text(cx, cy, s, words[min(3, int(el / self.STEP))], TITLE_C,
                      ("Courier New", 12, "bold"))
        elif self.stage == "reveal":
            lab, col = self.RES[self.result]
            self.text(cx, cy, s, lab, col, ("Courier New", 11, "bold"))
        else:
            self.text(cx, cy, s, "VS", TXT, ("Courier New", 12, "bold"))
        if self.stage not in ("count", "wait"):
            self.text(cx, y2 - 14, s, self.quip, TXT, ("Courier New", 9, "bold"))
        for i, mv in enumerate(RPS_MOVES):
            bx1, by1, bx2, by2 = self.btn_rect(i)
            on = self.stage == "pick"
            hov = on and i == self.hover and self.state == "idle"
            fill = BTN_HOVER if hov else (BTN_FILL if on else _lerp(B_FILL, BTN_FILL, 0.5))
            if hov:
                by1 -= 2
                by2 -= 2
            self.pixrect(bx1 - 2, by1 - 2, bx2 + 2, by2 + 2, B_OUT, 4, s)
            self.pixrect(bx1, by1, bx2, by2, fill, 3, s)
            self.image((bx1 + bx2) / 2, by1 + 26, s, hand_image(mv, 2))
            self.text((bx1 + bx2) / 2, by2 - 10, s, mv.capitalize(), TXT, ("Courier New", 8, "bold"))
        for j, (fx1, fy1, fx2, fy2) in enumerate(self.foot_rects()):
            self.pixrect(fx1 - 2, fy1 - 2, fx2 + 2, fy2 + 2, B_OUT, 4, s)
            fill = BTN_HOVER if self.hover == 100 + j else (BTN_ON if (j == 0 and self.duel) else BTN_FILL)
            self.pixrect(fx1, fy1, fx2, fy2, fill, 3, s)
            lab = ("vs Phone" if self.duel else "vs Pocket K") if j == 0 else "Close"
            self.text((fx1 + fx2) / 2, (fy1 + fy2) / 2, s, lab, TXT, ("Courier New", 9, "bold"))

    def hit(self, x, y):
        for i in range(3):
            a, b, c, d = self.btn_rect(i)
            if a <= x <= c and b <= y <= d:
                return i
        for j, (a, b, c, d) in enumerate(self.foot_rects()):
            if a <= x <= c and b <= y <= d:
                return 100 + j
        return -1

    def on_move(self, e):
        if self.state == "idle":
            self.hover = self.hit(e.x, e.y)
            self.cv.config(cursor="hand2" if self.hover >= 0 else "")

    def on_click(self, e):
        if self.state != "idle":
            return
        i = self.hit(e.x, e.y)
        if i == 101:
            self.close()
        elif i == 100:
            if self.stage == "pick":
                self.duel = not self.duel
                self.phone_move = None
        elif 0 <= i < 3:
            self.pick(RPS_MOVES[i])

    def keep_open(self):
        return self.stage != "pick"

    def on_closing(self):
        self.pet.rps_pose = None


# ---------------------------------------------------------------------------
#  NOTES: mini günlük / hatırlatıcı paneli
# ---------------------------------------------------------------------------
class NotesPanel(BubbleBase):
    PAD, TITLE, ENT, ROW, ROWS, FOOT = 12, 22, 28, 26, 6, 26
    BW = 340

    def __init__(self, pet, cx, top_y):
        bw = self.BW + 2 * self.PAD
        bh = (self.PAD + self.TITLE + self.ENT + 6 + self.ROWS * self.ROW + 8 +
              self.FOOT + self.PAD)
        self.scroll = 0
        self.entry = None
        self.f_norm = tkfont.Font(family="Courier New", size=9, weight="bold")
        self.f_done = tkfont.Font(family="Courier New", size=9, weight="bold",
                                  overstrike=True)
        super().__init__(pet, cx, top_y, bw, bh)

    # düzen
    def ent_rect(self):
        x = self.M + self.PAD
        y = self.M + self.PAD + self.TITLE
        return x, y, x + self.BW - 54, y + self.ENT

    def add_rect(self):
        x1, y1, x2, y2 = self.ent_rect()
        return x2 + 6, y1, x2 + 54, y2

    def row_rect(self, i):
        x = self.M + self.PAD
        y = self.M + self.PAD + self.TITLE + self.ENT + 6 + i * self.ROW
        return x, y, x + self.BW, y + self.ROW - 2

    def foot_rects(self):
        y = self.M + self.bh - self.PAD - self.FOOT
        x1 = self.M + self.PAD
        w = (self.BW - 6) / 2
        return [(x1, y, x1 + w, y + self.FOOT), (x1 + w + 6, y, x1 + 2 * w + 6, y + self.FOOT)]

    def sorted_notes(self):
        return sorted(self.pet.notes, key=lambda n: bool(n["done"]))

    def visible(self):
        ns = self.sorted_notes()
        self.scroll = max(0, min(self.scroll, max(0, len(ns) - self.ROWS)))
        return ns[self.scroll:self.scroll + self.ROWS]

    # entry
    def on_ready(self):
        x1, y1, x2, y2 = self.ent_rect()
        self.entry = tk.Entry(self.cv, font=("Courier New", 10, "bold"), bg=B_FILL,
                              fg=TXT, relief="flat", highlightthickness=2,
                              highlightbackground=B_OUT, highlightcolor=TITLE_C,
                              insertbackground=TXT)
        self.cv.create_window(x1, y1, window=self.entry, anchor="nw",
                              width=x2 - x1, height=y2 - y1, tags="entry")
        self.entry.bind("<Return>", lambda e: self.submit())
        self.entry.bind("<Escape>", lambda e: self.close())
        try:
            self.entry.focus_force()
        except tk.TclError:
            pass

    def keep_open(self):
        return self.entry is not None

    def submit(self):
        if not self.entry:
            return
        txt = self.entry.get().strip()
        if txt:
            self.pet.add_note(txt[:80])
            self.entry.delete(0, "end")
            self.scroll = 0

    def on_closing(self):
        if self.entry is not None:
            try:
                self.entry.destroy()
            except tk.TclError:
                pass
            self.entry = None

    # çizim
    def content(self, s, t):
        M = self.M
        pend = sum(1 for n in self.pet.notes if not n["done"])
        self.text(M + self.bw / 2, M + self.PAD + 8, s, L("~ Notes (%d open) ~") % pend, TITLE_C,
                  ("Courier New", 11, "bold"))
        x1, y1, x2, y2 = self.add_rect()
        hov = (self.hover == 200)
        self.pixrect(x1 - 2, y1 - 2, x2 + 2, y2 + 2, B_OUT, 4, s)
        self.pixrect(x1, y1, x2, y2, BTN_HOVER if hov else BTN_FILL, 3, s)
        self.text((x1 + x2) / 2, (y1 + y2) / 2, s, "Add", TXT, ("Courier New", 9, "bold"))

        vis = self.visible()
        if not vis:
            self.text(M + self.bw / 2, M + self.PAD + self.TITLE + self.ENT + 60, s,
                      "Nothing yet. Type a note above!\n(\"18:30 call mom\" sets a reminder)",
                      "#a08a7a", ("Courier New", 9, "bold"))
        for i, n in enumerate(vis):
            rx1, ry1, rx2, ry2 = self.row_rect(i)
            hov = (self.hover == i)
            self.pixrect(rx1, ry1, rx2, ry2, BTN_HOVER if hov else (BTN_ON if n["done"] else BTN_FILL), 3, s)
            self.image(rx1 + 14, (ry1 + ry2) / 2, s, menu_icon("box_on" if n["done"] else "box_off", 2))
            label = (f"⏰{n['due']} " if n.get("due") else "") + n["text"]
            self.text(rx1 + 30, (ry1 + ry2) / 2, s, _clip(label, 33),
                      "#8a7a6e" if n["done"] else TXT,
                      self.f_done if n["done"] else self.f_norm, "w", tr=False)
            self.image(rx2 - 13, (ry1 + ry2) / 2, s, menu_icon("x", 2))
        rest = len(self.pet.notes) - self.scroll - self.ROWS
        if rest > 0:
            self.text(M + self.bw - self.PAD - 4, M + self.bh - self.PAD - self.FOOT - 6, s,
                      L("▼ %d more") % rest, "#a08a7a", ("Courier New", 8, "bold"), "e")
        for (fx1, fy1, fx2, fy2), lab, j in zip(self.foot_rects(), ("Clear done", "Close"), (0, 1)):
            hov = (self.hover == 300 + j)
            self.pixrect(fx1 - 2, fy1 - 2, fx2 + 2, fy2 + 2, B_OUT, 4, s)
            self.pixrect(fx1, fy1, fx2, fy2, BTN_HOVER if hov else BTN_FILL, 3, s)
            self.text((fx1 + fx2) / 2, (fy1 + fy2) / 2, s, lab, TXT, ("Courier New", 9, "bold"))

    def hit(self, x, y):
        ax1, ay1, ax2, ay2 = self.add_rect()
        if ax1 <= x <= ax2 and ay1 <= y <= ay2:
            return ("add", 0)
        for i in range(len(self.visible())):
            rx1, ry1, rx2, ry2 = self.row_rect(i)
            if rx1 <= x <= rx2 and ry1 <= y <= ry2:
                return ("del", i) if x >= rx2 - 26 else ("row", i)
        for j, (fx1, fy1, fx2, fy2) in enumerate(self.foot_rects()):
            if fx1 <= x <= fx2 and fy1 <= y <= fy2:
                return ("foot", j)
        return (None, -1)

    def on_move(self, e):
        if self.state != "idle":
            return
        kind, i = self.hit(e.x, e.y)
        self.hover = {"add": 200, "foot": 300 + i}.get(kind, i if kind in ("row", "del") else -1)
        self.cv.config(cursor="hand2" if kind else "")

    def on_wheel(self, d):
        self.scroll += d

    def on_click(self, e):
        if self.state != "idle":
            return
        kind, i = self.hit(e.x, e.y)
        if kind == "add":
            self.submit()
        elif kind in ("row", "del"):
            note = self.visible()[i]
            if kind == "row":
                self.pet.toggle_note(note)
            else:
                self.pet.delete_note(note)
        elif kind == "foot":
            if i == 0:
                self.pet.clear_done_notes()
            else:
                self.close()


def tk_safe(text):
    """Eski Tk sürümleri BMP dışı emojileri çizemez: güvenli bir karakterle değiştir."""
    return "".join(ch if ord(ch) <= 0xFFFF else "♥" for ch in str(text))


def wrap_text(text, width):
    out = []
    for para in str(text).split("\n"):
        line = ""
        for word in para.split(" "):
            while len(word) > width:
                if line:
                    out.append(line)
                    line = ""
                out.append(word[:width])
                word = word[width:]
            if len(line) + len(word) + (1 if line else 0) > width:
                out.append(line)
                line = word
            else:
                line = (line + " " + word) if line else word
        out.append(line)
    return out


class ChatPanel(BubbleBase):
    """Telefonla yazışma: telefondan gelenler solda, buradan yazılanlar sağda."""
    PAD, TITLE, LINE, LINES, ENT, FOOT = 12, 22, 17, 12, 28, 24
    BW, WRAP = 360, 30

    def __init__(self, pet, cx, top_y):
        bw = self.BW + 2 * self.PAD
        bh = (self.PAD + self.TITLE + self.LINES * self.LINE + 10 + self.ENT + 8 +
              self.FOOT + self.PAD)
        self.scroll = 0
        self.entry = None
        self.f_txt = ("Courier New", 9, "bold")
        self.f_small = ("Courier New", 7, "bold")
        super().__init__(pet, cx, top_y, bw, bh)

    def log_rect(self):
        x = self.M + self.PAD
        y = self.M + self.PAD + self.TITLE
        return x, y, x + self.BW, y + self.LINES * self.LINE + 6

    def ent_rect(self):
        x1, _y1, _x2, y2 = self.log_rect()
        return x1, y2 + 6, x1 + self.BW - 70, y2 + 6 + self.ENT

    def send_rect(self):
        x1, y1, x2, y2 = self.ent_rect()
        return x2 + 6, y1, self.M + self.PAD + self.BW, y2

    def foot_rect(self):
        y = self.M + self.bh - self.PAD - self.FOOT
        return self.M + self.PAD, y, self.M + self.PAD + self.BW, y + self.FOOT

    def lines(self):
        """(kimden, satır, saat|None) listesi, eskiden yeniye."""
        out = []
        for m in self.pet.inbox[-40:]:
            who = m.get("from", "phone")
            parts = wrap_text(tk_safe(m["text"]), self.WRAP)
            stamp = time.strftime("%H:%M", time.localtime(m.get("ts", 0)))
            for i, ln in enumerate(parts):
                out.append((who, ln, stamp if i == len(parts) - 1 else None, i == 0))
        return out

    def on_ready(self):
        x1, y1, x2, y2 = self.ent_rect()
        self.entry = tk.Entry(self.cv, font=("Courier New", 10, "bold"), bg=B_FILL,
                              fg=TXT, relief="flat", highlightthickness=2,
                              highlightbackground=B_OUT, highlightcolor=TITLE_C,
                              insertbackground=TXT)
        self.cv.create_window(x1, y1, window=self.entry, anchor="nw",
                              width=x2 - x1, height=y2 - y1, tags="entry")
        self.entry.bind("<Return>", lambda e: self.submit())
        self.entry.bind("<Escape>", lambda e: self.close())
        try:
            self.entry.focus_force()
        except tk.TclError:
            pass

    def keep_open(self):
        return self.entry is not None

    def submit(self):
        if not self.entry:
            return
        txt = self.entry.get().strip()
        if txt:
            self.pet.send_from_pc(txt)
            self.entry.delete(0, "end")
            self.scroll = 0

    def on_closing(self):
        if self.entry is not None:
            try:
                self.entry.destroy()
            except tk.TclError:
                pass
            self.entry = None

    def content(self, s, t):
        M = self.M
        self.text(M + self.bw / 2, M + self.PAD + 8, s, "~ Chat ~", TITLE_C,
                  ("Courier New", 11, "bold"))
        x1, y1, x2, y2 = self.log_rect()
        self.pixrect(x1 - 2, y1 - 2, x2 + 2, y2 + 2, B_OUT, 4, s)
        self.pixrect(x1, y1, x2, y2, "#fffaf4", 3, s)
        ls = self.lines()
        if not ls:
            self.text((x1 + x2) / 2, (y1 + y2) / 2, s,
                      "No messages yet. Turn on Settings > Phone\nand write from the phone, or type here!",
                      "#a08a7a", ("Courier New", 9, "bold"))
        self.scroll = max(0, min(self.scroll, max(0, len(ls) - self.LINES)))
        end = len(ls) - self.scroll
        vis = ls[max(0, end - self.LINES):end]
        col = {"phone": "#a3214f", "pet": "#8a7a6e", "pc": "#2b4a8a"}
        band = {"phone": "#ffe9ef", "pc": "#e4edff", "pet": "#f6efe8"}
        for i, (who, ln, stamp, first) in enumerate(vis):
            y = y1 + 4 + i * self.LINE + self.LINE / 2
            self.rect(x1 + 3, y - self.LINE / 2 + 1, x2 - 3, y + self.LINE / 2, band.get(who, B_FILL), s)
            if who == "pc":
                self.text(x2 - 8, y, s, ln, col["pc"], self.f_txt, "e", tr=False)
                if stamp:
                    self.text(x1 + 8, y, s, stamp, "#c0b0a4", self.f_small, "w", tr=False)
            else:
                pre = ("• " if who == "pet" else "♥ ") if first else "  "
                self.text(x1 + 8, y, s, pre + ln, col.get(who, TXT), self.f_txt, "w", tr=False)
                if stamp:
                    self.text(x2 - 8, y, s, stamp, "#c0b0a4", self.f_small, "e", tr=False)
        if not self.pet.remote:
            self.text(M + self.bw / 2, y2 - 9, s, "Phone link is off: messages wait here.",
                      "#c0907a", self.f_small)
        sx1, sy1, sx2, sy2 = self.send_rect()
        hov = self.hover == 200
        self.pixrect(sx1 - 2, sy1 - 2, sx2 + 2, sy2 + 2, B_OUT, 4, s)
        self.pixrect(sx1, sy1, sx2, sy2, BTN_HOVER if hov else BTN_ON, 3, s)
        self.text((sx1 + sx2) / 2, (sy1 + sy2) / 2, s, "Send", TXT, ("Courier New", 9, "bold"))
        fx1, fy1, fx2, fy2 = self.foot_rect()
        hov = self.hover == 300
        self.pixrect(fx1 - 2, fy1 - 2, fx2 + 2, fy2 + 2, B_OUT, 4, s)
        self.pixrect(fx1, fy1, fx2, fy2, BTN_HOVER if hov else BTN_FILL, 3, s)
        self.text((fx1 + fx2) / 2, (fy1 + fy2) / 2, s, "Close", TXT, ("Courier New", 9, "bold"))

    def hit(self, x, y):
        for k, (x1, y1, x2, y2) in (("send", self.send_rect()), ("foot", self.foot_rect())):
            if x1 <= x <= x2 and y1 <= y <= y2:
                return k
        return None

    def on_move(self, e):
        if self.state != "idle":
            return
        k = self.hit(e.x, e.y)
        self.hover = {"send": 200, "foot": 300}.get(k, -1)
        self.cv.config(cursor="hand2" if k else "")

    def on_wheel(self, d):
        self.scroll -= d

    def on_click(self, e):
        if self.state != "idle":
            return
        k = self.hit(e.x, e.y)
        if k == "send":
            self.submit()
        elif k == "foot":
            self.close()


# ===========================================================================
#  OYUN MODU: tepsi simgesi (Windows), tam ekran algılama
# ===========================================================================
HEAD_ICON = [
    "....oooooooo....",
    "..oohhhhhhhhoo..",
    ".ohhhHHHhhhhhho.",
    "ohhHHhhhhhhhhhho",
    "ohhhhhsssshhhhho",
    "ohhhsssssssshhho",
    "ohhsssssssssshho",
    "ohhsEessssEeshho",
    "ohhsEessssEeshho",
    "ohhpssssssssphho",
    "ohhssssmmsssshho",
    "ohdhsssssssshdho",
    "odhhoossssoohhdo",
    "odhho..oo..ohhdo",
    ".odo........odo.",
    "..o..........o..",
]


def head_icon_grid():
    """Karolina'nın kafası, 16x16 (tepsi simgesi için)."""
    return [r.ljust(16, ".")[:16] for r in HEAD_ICON]


def write_ico(path, grid, pal):
    """16 ve 32 piksellik 32-bit ICO dosyası yazar (harici kütüphane yok)."""
    import struct

    def rgba(ch):
        if ch not in pal:
            return (0, 0, 0, 0)
        c = pal[ch].lstrip("#")
        return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16), 255)

    imgs = []
    for sc in (1, 2):
        n = 16 * sc
        px = bytearray()
        for y in range(n - 1, -1, -1):                       # BMP: alttan yukarı
            row = grid[y // sc]
            for x in range(n):
                r, g, b, a = rgba(row[x // sc] if x // sc < len(row) else ".")
                px += bytes((b, g, r, a))
        mask = bytes(((n + 31) // 32) * 4 * n)
        hdr = struct.pack("<IiiHHIIiiII", 40, n, n * 2, 1, 32, 0, len(px) + len(mask), 0, 0, 0, 0)
        imgs.append((n, hdr + bytes(px) + mask))
    out = struct.pack("<HHH", 0, 1, len(imgs))
    off = 6 + 16 * len(imgs)
    for n, data in imgs:
        out += struct.pack("<BBBBHHII", n, n, 0, 0, 1, 32, len(data), off)
        off += len(data)
    for _n, data in imgs:
        out += data
    with open(path, "wb") as f:
        f.write(out)
    return path


class TrayIcon:
    """Windows bildirim alanı (saat yanındaki küçük simgeler) için ctypes ile simge.
    ÖNEMLİ: pencere fonksiyonu Tk'yi ASLA çağırmaz (Tk'nin olay döngüsünün içinden çağrılır ve
    Windows'ta kilitlenme/çökme yapar). Sadece 'clicked' işaretini koyar; Pet bunu döngüsünde okur.
    Pencere sınıfı ve fonksiyonu tek sefer kaydedilir ve hiç silinmez (tekrar gizlenince çökmesin)."""
    WM_TRAY = 0x8000 + 17
    _proc = None
    _ready = False
    current = None

    @classmethod
    def _setup(cls, ctypes, wintypes, u32):
        if cls._ready:
            return
        LRESULT = ctypes.c_ssize_t
        WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM,
                                     wintypes.LPARAM)
        u32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        u32.DefWindowProcW.restype = LRESULT

        def proc(hwnd, msg, wp, lp):
            try:
                if msg == cls.WM_TRAY:
                    if (lp & 0xFFFF) in (0x0202, 0x0203, 0x0205, 0x0405):
                        cur = cls.current
                        if cur is not None:
                            cur.clicked = True
                    return 0
            except Exception:
                return 0
            return u32.DefWindowProcW(hwnd, msg, wp, lp)

        cls._proc = WNDPROC(proc)                            # sınıf ömrü boyunca canlı kalır

        class WNDCLASSW(ctypes.Structure):
            _fields_ = [("style", wintypes.UINT), ("lpfnWndProc", WNDPROC), ("cbClsExtra", ctypes.c_int),
                        ("cbWndExtra", ctypes.c_int), ("hInstance", wintypes.HINSTANCE),
                        ("hIcon", wintypes.HICON), ("hCursor", wintypes.HANDLE),
                        ("hbrBackground", wintypes.HBRUSH), ("lpszMenuName", wintypes.LPCWSTR),
                        ("lpszClassName", wintypes.LPCWSTR)]
        ctypes.windll.kernel32.GetModuleHandleW.restype = wintypes.HMODULE
        cls.hinst = ctypes.windll.kernel32.GetModuleHandleW(None)
        wc = WNDCLASSW()
        wc.lpfnWndProc = cls._proc
        wc.hInstance = cls.hinst
        wc.lpszClassName = "PocketKarolinaTray"
        u32.RegisterClassW(ctypes.byref(wc))
        u32.DestroyIcon.argtypes = [wintypes.HANDLE]
        u32.DestroyWindow.argtypes = [wintypes.HWND]
        u32.CreateWindowExW.restype = wintypes.HWND
        u32.CreateWindowExW.argtypes = [wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
                                        ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                        wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID]
        u32.LoadImageW.restype = wintypes.HANDLE
        u32.LoadImageW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR, wintypes.UINT, ctypes.c_int,
                                   ctypes.c_int, wintypes.UINT]
        ctypes.windll.shell32.Shell_NotifyIconW.argtypes = [wintypes.DWORD, ctypes.c_void_p]
        cls._ready = True

    def __init__(self, root, ico_path, tip, on_click=None):
        import ctypes
        from ctypes import wintypes
        self.ct = ctypes
        self.clicked = False
        u32, sh = ctypes.windll.user32, ctypes.windll.shell32
        self.u32, self.sh = u32, sh
        TrayIcon._setup(ctypes, wintypes, u32)

        class NOTIFYICONDATAW(ctypes.Structure):
            _fields_ = [("cbSize", wintypes.DWORD), ("hWnd", wintypes.HWND), ("uID", wintypes.UINT),
                        ("uFlags", wintypes.UINT), ("uCallbackMessage", wintypes.UINT),
                        ("hIcon", wintypes.HICON), ("szTip", ctypes.c_wchar * 128),
                        ("dwState", wintypes.DWORD), ("dwStateMask", wintypes.DWORD),
                        ("szInfo", ctypes.c_wchar * 256), ("uVersion", wintypes.UINT),
                        ("szInfoTitle", ctypes.c_wchar * 64), ("dwInfoFlags", wintypes.DWORD),
                        ("guidItem", ctypes.c_byte * 16), ("hBalloonIcon", wintypes.HICON)]

        self.hwnd = u32.CreateWindowExW(0, "PocketKarolinaTray", "PocketKarolinaTray", 0,
                                        0, 0, 0, 0, None, None, TrayIcon.hinst, None)
        if not self.hwnd:
            raise OSError("tray window")
        self.hicon = u32.LoadImageW(None, ico_path, 1, 0, 0, 0x10 | 0x40)   # LOADFROMFILE|DEFAULTSIZE
        nid = self.nid = NOTIFYICONDATAW()
        nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        nid.hWnd, nid.uID = self.hwnd, 1
        nid.uFlags = 0x1 | 0x2 | 0x4                         # MESSAGE | ICON | TIP
        nid.uCallbackMessage = self.WM_TRAY
        nid.hIcon = self.hicon
        nid.szTip = tip[:127]
        TrayIcon.current = self
        if not sh.Shell_NotifyIconW(0, ctypes.byref(nid)):  # NIM_ADD
            self.remove()
            raise OSError("Shell_NotifyIcon")

    def balloon(self, title, text):
        try:
            n = self.nid
            n.uFlags = 0x10                                  # NIF_INFO
            n.szInfoTitle, n.szInfo, n.dwInfoFlags = title[:63], text[:255], 0x4 | 0x20
            self.sh.Shell_NotifyIconW(1, self.ct.byref(n))   # NIM_MODIFY
        except Exception:
            pass

    def remove(self):
        if TrayIcon.current is self:
            TrayIcon.current = None
        try:
            self.sh.Shell_NotifyIconW(2, self.ct.byref(self.nid))   # NIM_DELETE
        except Exception:
            pass
        for fn, h in (("DestroyIcon", getattr(self, "hicon", None)),
                      ("DestroyWindow", getattr(self, "hwnd", None))):
            if h:
                try:
                    getattr(self.u32, fn)(h)
                except Exception:
                    pass


class RestoreChip:
    """Tepsi simgesi kurulamazsa: ekranın sağ altında küçük bir kafa, tıklayınca geri gelir."""

    def __init__(self, pet):
        self.pet = pet
        w = self.win = tk.Toplevel(pet.root)
        w.overrideredirect(True)
        w.wm_attributes("-topmost", True)
        make_transparent(w)
        self.img = grid_to_image(head_icon_grid(), PAL, False, 2)
        cv = tk.Canvas(w, width=32, height=32, bg=KEY, highlightthickness=0, cursor="hand2")
        cv.pack()
        cv.create_image(0, 0, anchor="nw", image=self.img)
        self.clicked = False
        cv.bind("<Button-1>", lambda e: setattr(self, "clicked", True))
        w.geometry(f"+{pet.sw - 44}+{pet.sh - 92}")

    def remove(self):
        try:
            self.win.destroy()
        except tk.TclError:
            pass


_FS = {}


def fullscreen_app_active():
    """Öndeki pencere tüm monitörü kaplıyor ve çerçevesizse (oyun, film, F11) True.
    Desteklenmeyen sistemde None."""
    if not IS_WIN:
        return None
    try:
        import ctypes
        from ctypes import wintypes
        if not _FS:
            u = ctypes.windll.user32
            u.GetForegroundWindow.restype = wintypes.HWND
            u.MonitorFromWindow.restype = wintypes.HANDLE
            u.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
            u.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
            u.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
            u.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
            u.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]

            class MONITORINFO(ctypes.Structure):
                _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                            ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]
            u.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MONITORINFO)]
            _FS.update(u=u, MI=MONITORINFO, w=wintypes, c=ctypes)
        u, wt, ct = _FS["u"], _FS["w"], _FS["c"]
        hwnd = u.GetForegroundWindow()
        if not hwnd:
            return False
        pid = wt.DWORD(0)
        u.GetWindowThreadProcessId(hwnd, ct.byref(pid))
        if pid.value == os.getpid():
            return False
        buf = ct.create_unicode_buffer(64)
        u.GetClassNameW(hwnd, buf, 64)
        if buf.value in ("Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd"):
            return False
        if (u.GetWindowLongW(hwnd, -16) & 0x00C00000) == 0x00C00000:   # başlık çubuğu var: normal pencere
            return False
        r = wt.RECT()
        u.GetWindowRect(hwnd, ct.byref(r))
        mi = _FS["MI"]()
        mi.cbSize = ct.sizeof(mi)
        if not u.GetMonitorInfoW(u.MonitorFromWindow(hwnd, 2), ct.byref(mi)):
            return False
        m = mi.rcMonitor
        return r.left <= m.left and r.top <= m.top and r.right >= m.right and r.bottom >= m.bottom
    except Exception:
        return None


# ===========================================================================
#  MEVSİMLİK KOSTÜMLER
# ===========================================================================
SEASONS = [   # (kimlik, başlangıç (ay, gün), bitiş (ay, gün), kostüm)
    ("newyear", (12, 31), (1, 1), {"hat": "party", "glasses": "stars", "held": "balloon"}),
    ("valentine", (2, 10), (2, 14), {"glasses": "hearts", "outfit": "heart", "held": "rose"}),
    ("summer", (7, 1), (8, 31), {"hat": "strawhat", "glasses": "shades", "held": "icecream"}),
    ("halloween", (10, 25), (11, 1), {"hat": "witch", "held": "pumpkin"}),
    ("christmas", (12, 15), (12, 26), {"hat": "santa", "outfit": "sweater", "neck": "scarf"}),
]


def season_of(day):
    """O güne denk gelen mevsim: (kimlik, tekil anahtar, kostüm) ya da None."""
    md = (day.month, day.day)
    for sid, a, b, look in SEASONS:
        if a <= b:
            inside = a <= md <= b
        else:                                               # yıl dönümünü aşan aralık
            inside = md >= a or md <= b
        if inside:
            year = day.year - 1 if (a > b and md <= b) else day.year
            return sid, "%s-%d" % (sid, year), look
    return None


# ===========================================================================
#  POLAROID (selfie sonucu)
# ===========================================================================
class Polaroid:
    def __init__(self, pet, img, saved_path):
        self.pet = pet
        self.img = img
        w = self.win = tk.Toplevel(pet.root)
        w.overrideredirect(True)
        w.wm_attributes("-topmost", True)
        pw, ph = img.width(), img.height()
        self.ww, self.wh = pw + 12, ph + 12 + 24
        cv = tk.Canvas(w, width=self.ww, height=self.wh, bg="#3a1f1c",
                       highlightthickness=0)
        cv.pack()
        cv.create_image(6, 6, anchor="nw", image=img)
        cv.create_rectangle(6, ph + 6, self.ww - 6, self.wh - 6, fill="#fff4ea", outline="")
        txt = "♥ saved to Pictures/PocketKarolina" if saved_path else "♥ selfie!"
        cv.create_text(self.ww / 2, ph + 6 + 9, text=txt, fill="#c2561c",
                       font=("Courier New", 8, "bold"))
        cv.bind("<Button-1>", lambda e: self.end())
        x = max(0, min(int(pet.x + pet.cw / 2 - self.ww / 2), pet.sw - self.ww))
        self.x = x
        self.y_end = max(8, int(pet.y - self.wh - 6))
        self.y = self.y_end + 50
        self.t = 0
        self.alive = True
        try:
            w.attributes("-alpha", 0.0)
        except tk.TclError:
            pass
        w.geometry(f"+{self.x}+{self.y}")
        self.step()

    def step(self):
        if not self.alive:
            return
        self.t += 1
        t = self.t
        if t <= 14:                                 # süzülerek gel
            k = 1 - (1 - t / 14) ** 3
            self.y = self.y_end + 50 * (1 - k)
            alpha = k
        elif t <= 14 + 110:                         # bekle
            alpha = 1.0
        elif t <= 14 + 110 + 12:                    # sön
            alpha = 1 - (t - 124) / 12
        else:
            self.end()
            return
        try:
            self.win.attributes("-alpha", max(0.0, min(1.0, alpha)))
        except tk.TclError:
            pass
        self.win.geometry(f"+{self.x}+{int(self.y)}")
        self.win.after(30, self.step)

    def end(self):
        self.alive = False
        try:
            self.win.destroy()
        except tk.TclError:
            pass


# ===========================================================================
#  TASMALI ARKADAŞLAR  (Companion -> Frog, Dog)
# ===========================================================================
HOP_T = 9


def grid_to_image(grid, pal, flip, scale):
    h, w = len(grid), len(grid[0])
    p = tk.PhotoImage(width=w, height=h)
    for y, row in enumerate(grid):
        if flip:
            row = row[::-1]
        n, x = len(row), 0
        while x < n:                                  # aynı renkli pikselleri tek seferde yaz
            ch = row[x]
            x2 = x + 1
            if ch in pal:
                while x2 < n and row[x2] == ch:
                    x2 += 1
                p.put(pal[ch], to=(x, y, x2, y + 1))
            x = x2
    return p.zoom(scale) if scale != 1 else p


class Companion:
    """Tasmayla bağlı arkadaş: pencere + tasma + fizik. Alt sınıflar davranışı yazar."""
    GW, GH, GS = 14, 10, 4
    PALETTE = {}
    REST, MAX = 70, 175
    LEAD = False                  # True: karakterin önünde, öndeki elden bağlı
    LEASH = "#e63946"

    def __init__(self, pet):
        self.pet = pet
        w = self.win = tk.Toplevel(pet.root)
        w.overrideredirect(True)
        w.wm_attributes("-topmost", True)
        make_transparent(w)
        self.cv = tk.Canvas(w, width=10, height=10, bg=KEY, highlightthickness=0)
        self.cv.pack()
        self.cv.bind("<Button-1>", lambda e: self.poke())
        self.fw, self.fh = self.GW * self.GS, self.GH * self.GS
        side = 1 if self.LEAD else -1
        self.x = pet.x + pet.cw / 2 + side * 110
        self.y = pet.ground + pet.ch - self.fh - 140
        self.vy = 0.0
        self.face = 1
        self.t = 0
        self.lift = 0.0
        self.imgs = {}
        self.win_w = self.win_h = 0
        self._geo = None

    # --- alt sınıf kancaları ------------------------------------------------
    def grid(self, pose):
        raise NotImplementedError

    def behave(self, floor, target):
        return None

    def dragged_pose(self):
        return None

    def anchor_off(self):
        return self.fw / 2, self.fh * 0.55

    def top_margin(self):
        return 0

    def extra(self, cv, minx, miny):
        pass

    def poke(self):
        floor = self.pet.floor + self.pet.ch - self.fh
        if self.y >= floor - 1:
            self.vy = -9.0

    def settle(self, floor):
        """Zemin (veya tünek) seviyesine yumuşakça otur. Hâlâ yükseliyorsa True."""
        if self.y > floor + 2:
            self.y += (floor - self.y) * 0.3
            return True
        self.y = floor
        return False

    # ------------------------------------------------------------------------
    def img(self, pose, flip):
        k = (pose, flip)
        if k not in self.imgs:
            self.imgs[k] = grid_to_image(self.grid(pose), self.PALETTE, flip, self.GS)
        return self.imgs[k]

    def destroy(self):
        try:
            self.win.destroy()
        except tk.TclError:
            pass

    def update(self):
        pet = self.pet
        self.t += 1
        fl = pet.face_left
        if self.LEAD:
            col = 8 if fl else 23
        else:
            col = 24 if fl else 7
        hx = pet.x + PADX + col * SCALE                      # tasmayı tutan el
        hy = pet.y + PADT + 27 * SCALE
        fdir = -1 if fl else 1
        side = 1 if self.LEAD else -1
        floor = pet.floor + pet.ch - self.fh
        target = hx + side * fdir * self.REST - self.fw / 2

        self.lift = 0.0
        pose = self.behave(floor, target)

        ox, oy = self.anchor_off()
        cx, cy = self.x + ox, self.y - self.lift + oy
        dxl, dyl = cx - hx, cy - hy
        dist = math.hypot(dxl, dyl)
        if dist > self.MAX + 0.5:                            # tasma gerildi
            k = self.MAX / dist
            cx, cy = hx + dxl * k, hy + dyl * k
            self.x, self.y = cx - ox, cy - oy + self.lift
            self.vy = 0.0
            pose = self.dragged_pose()
            dist = self.MAX

        ay = self.y - self.lift
        sag = min(24.0, max(0.0, self.REST + 40 - dist) * 0.35)
        mx, my = (hx + cx) / 2, (hy + cy) / 2 + sag
        pad = 8
        tm = self.top_margin()
        minx = int(min(hx, cx, self.x, mx) - pad)
        maxx = int(max(hx, cx, self.x + self.fw, mx) + pad)
        miny = int(min(hy, cy, ay - tm, my) - pad)
        maxy = int(max(hy, cy, ay + self.fh, my) + pad)
        w, h = maxx - minx, maxy - miny
        if (w > self.win_w or h > self.win_h or
                w < self.win_w - 96 or h < self.win_h - 96):       # boyut her karede değişmesin
            self.win_w, self.win_h = (w + 31) // 32 * 32 + 32, (h + 31) // 32 * 32 + 32
            self.cv.config(width=self.win_w, height=self.win_h)
            self._geo = None
        geo = f"{self.win_w}x{self.win_h}+{minx}+{miny}"
        if geo != self._geo:
            self._geo = geo
            self.win.geometry(geo)
        self.cv.delete("all")
        self.cv.create_line(hx - minx, hy - miny, mx - minx, my - miny,
                            cx - minx, cy - miny, smooth=True, width=2,
                            fill=self.LEASH)
        self.cv.create_oval(hx - minx - 3, hy - miny - 3, hx - minx + 3,
                            hy - miny + 3, fill=self.LEASH, outline="")
        self.cv.create_image(self.x - minx, ay - miny, anchor="nw",
                             image=self.img(pose, self.face < 0))
        self.extra(self.cv, minx, miny)


# ------------------------------- KURBAĞA ------------------------------------
FROG_PAL = {"o": "#1f4d2b", "g": "#6fd36f", "l": "#c9f2a8", "w": "#ffffff",
            "k": "#16241a", "p": "#ff9fb2"}
FROG_SIT = [
    "..oooo..oooo..",
    ".owkkwoowkkwo.",
    ".owkkwoowkkwo.",
    "oggggggggggggo",
    "oggpggggggpggo",
    "ogggkkkkkkgggo",
    "oggllllllllggo",
    "oggllllllllggo",
    ".oggo....oggo.",
    "ooooo....ooooo",
]


def frog_grid(name):
    g = list(FROG_SIT)
    if name == "blink":
        g[1] = g[1].replace("w", "g").replace("k", "g")
        g[2] = ".oooooooooooo."
    elif name == "hop":
        g[8] = "oggo......oggo"
        g[9] = "ogo........ogo"
    elif name == "crouch":                            # zıplamadan önce çömelir
        del g[2]
        g.insert(0, "." * 14)
    return g


class Frog(Companion):
    GW, GH, GS = 14, 10, 4
    PALETTE = FROG_PAL
    REST, MAX = 70, 175
    LEAD = False
    LEASH = "#e63946"

    def __init__(self, pet):
        super().__init__(pet)
        self.hop_t = 0
        self.hop_dx = 0.0
        self.blink_t = 0
        self.crouch_t = 0
        self.squash_t = 0

    def grid(self, pose):
        return frog_grid(pose)

    def dragged_pose(self):
        self.hop_t = 0
        return "hop"

    def behave(self, floor, target):
        pose = "sit"
        if self.hop_t > 0:                                  # zıplıyor
            self.hop_t -= 1
            self.x += self.hop_dx / HOP_T
            k = 1 - self.hop_t / HOP_T
            self.y = floor - 14 * math.sin(math.pi * k)
            if self.hop_t == 0:
                self.y = floor
                self.squash_t = 1                           # inince hafif ezilir
            pose = "hop"
        elif self.y < floor - 0.5 or self.vy < 0:           # havada
            self.vy += 1.0
            self.y += self.vy
            if self.y >= floor:
                self.y = floor
                self.vy = 0.0
                self.squash_t = 2
            pose = "hop"
        else:
            if self.settle(floor):
                return "hop"
            dx = target - self.x
            if self.squash_t > 0:
                self.squash_t -= 1
                pose = "crouch"
            elif self.crouch_t > 0:
                self.crouch_t -= 1
                pose = "crouch"
                if self.crouch_t == 0 and abs(dx) > 30:
                    self.hop_t = HOP_T
                    self.hop_dx = max(-44.0, min(44.0, dx))
                    self.face = 1 if dx > 0 else -1
            elif abs(dx) > 30:
                self.face = 1 if dx > 0 else -1
                self.crouch_t = 2                           # önce çömel, sonra zıpla
                pose = "crouch"
            elif self.blink_t > 0:
                self.blink_t -= 1
                pose = "blink"
            elif self.t % 90 == 0:
                self.blink_t = 4
        return pose


# ------------------------------- LILA (pinscher) ----------------------------
DOG_PAL = {"o": "#16111a", "b": "#4a4254", "t": "#c2763a", "T": "#e29a5c",
           "w": "#ffffff", "n": "#0b080c", "p": "#ff8fa3", "r": "#8a3ffc"}
DGW, DGH = 24, 18


def _dblank():
    return [["."] * DGW for _ in range(DGH)]


def _dpaste(g, part, x, y):
    for j, row in enumerate(part):
        for i, ch in enumerate(row):
            if ch != "." and 0 <= y + j < DGH and 0 <= x + i < DGW:
                g[y + j][x + i] = ch


DOG_HEAD = [
    "..o...o....",
    ".obo.obo...",
    ".obbobbo...",
    ".obbbtbbo..",
    ".obbbwnbbbo",
    ".obbbbbbtoo",
    ".obbbbtTTno",
    "obbbbtTTTTo",
    "..ooooooo..",
    "...........",
]
DOG_HEADS = {"closed": DOG_HEAD}
_h = list(DOG_HEAD)
_h[8], _h[9] = "..obbpppo..", "...obTTTo.."
DOG_HEADS["open"] = _h
_h = list(DOG_HEAD)
_h[8], _h[9] = "..oooppoo..", "......pp..."
DOG_HEADS["tongue"] = _h
_h = list(DOG_HEAD)
_h[4] = ".obbboobbbo"
DOG_HEADS["sleep"] = _h
for _r in DOG_HEADS.values():
    assert all(len(x) == 11 for x in _r)

DOG_TORSO = [
    "........................",
    "........................",
    "........................",
    "........................",
    "........................",
    "........................",
    "........................",
    "............obbo........",
    "........ooooobbbo.......",
    "...obbbbbbbbbbbbrrrro...",
    "....obbbbbbbbbbbttTTto..",
    "....obbbbbbbbbbbbtTTo...",
    ".....obbbbbbbbbbbbbo....",
]
DOG_TAILS = [["...ooo...", "..obbbo..", "..obbbbo."],
             [".........", "..oooo...", "..obbbbo."]]
DOG_LEG = ["obo", "obo", "oto", "ooo"]
DOG_STAND_LEGS = [(4, 0, 0), (8, 0, 0), (14, 0, 0), (19, 0, 0)]
DOG_WALK = [
    [(4, 0, 0), (8, 1, 1), (14, 1, 1), (19, 0, 0)],
    [(4, -1, 0), (8, 2, 0), (14, 2, 0), (19, -1, 0)],
    [(4, 1, 1), (8, 0, 0), (14, 0, 0), (19, 1, 1)],
    [(4, 2, 0), (8, -1, 0), (14, -1, 0), (19, 2, 0)],
]


def dog_grid(pose):
    kind, idx, head, tail = pose
    g = _dblank()
    hd, tl = DOG_HEADS[head], DOG_TAILS[tail]
    if kind == "lie":
        _dpaste(g, DOG_TORSO, 0, 4)
        _dpaste(g, tl, 0, 10)
        _dpaste(g, hd, 13, 7 if head == "sleep" else 4)
        _dpaste(g, ["otTTTTTTo", "ooooooooo"], 12, 16)
        _dpaste(g, ["otTTo", "ooooo"], 5, 16)
    else:
        bob = -1 if (kind == "walk" and idx in (1, 3)) else 0
        _dpaste(g, DOG_TORSO, 0, bob)
        _dpaste(g, tl, 0, 6 + bob)
        _dpaste(g, hd, 13, bob)
        for x, dx, lift in (DOG_WALK[idx] if kind == "walk" else DOG_STAND_LEGS):
            _dpaste(g, DOG_LEG, x + dx, 13 - lift)
    return ["".join(r) for r in g]


class Dog(Companion):
    GW, GH, GS = DGW, DGH, 3
    PALETTE = DOG_PAL
    REST, MAX = 95, 190
    LEAD = True
    LEASH = "#8a3ffc"

    def __init__(self, pet):
        super().__init__(pet)
        self.vx = 0.0
        self.phase = 0.0
        self.trot = False
        self.idle_t = 0
        self.bark_t = 0
        self.say_t = 0
        self.say_text = ""
        self.free, self.fetch = False, None           # getir oyunu: tasmasız mod
        self.chew = None                                # kuru et kemirme
        self.crumbs = []
        self.font = tkfont.Font(family="Courier New", size=10, weight="bold")

    def grid(self, pose):
        return dog_grid(pose)

    def bark(self, text="HAU!", dur=45):
        self.say_text, self.say_t, self.bark_t = text, dur, 16

    def anchor_off(self):
        ax = 17.5 if self.face > 0 else DGW - 17.5          # tasma = tasmanın (collar) yeri
        return ax * self.GS, 9.5 * self.GS

    def dragged_pose(self):
        return ("walk", int(self.t * 0.5) % 4, "open", (self.t // 4) % 2)

    def sleeping(self):
        return self.idle_t > 40 and self.pet.sleeping_now()

    def top_margin(self):
        return 40 if (self.say_t > 0 or self.sleeping()) else 0

    def behave(self, floor, target):
        pet = self.pet
        wag = (self.t // 6) % 2
        if self.y < floor - 0.5 or self.vy < 0:             # havada (tasma yukarı çekti)
            self.vy += 1.0
            self.y += self.vy
            if self.y >= floor:
                self.y, self.vy = floor, 0.0
            return ("walk", int(self.t * 0.5) % 4, "open", wag)

        if self.settle(floor):
            return ("walk", int(self.t * 0.5) % 4, "open", wag)
        dx = target - self.x
        if abs(dx) > 42:
            self.trot = True
        elif abs(dx) < 14:
            self.trot = False

        if self.trot:                                       # tırıs
            self.idle_t = 0
            want = max(-6.5, min(6.5, dx * 0.10))
            self.vx += (want - self.vx) * 0.25
            self.x += self.vx
            self.phase += abs(self.vx) * 0.16
            if abs(self.vx) > 0.3:
                self.face = 1 if self.vx > 0 else -1
            head = "open" if abs(self.vx) > 5 else "closed"
            pose = ("walk", int(self.phase) % 4, head, wag)
        else:
            self.vx *= 0.6
            self.x += self.vx
            self.idle_t += 1
            excited = pet.excited_now() and not pet.menu_open
            if pet.sleeping_now() and self.idle_t > 40:
                pose = ("lie", 0, "sleep", 1)
            elif excited:
                self.lift = 11 * abs(math.sin(self.t * 0.3))
                pose = ("stand", 0, "tongue", wag)
            elif self.idle_t > 150:
                pose = ("lie", 0, "closed", 1 if (self.t // 12) % 3 else 0)
            else:
                pose = ("stand", 0, "closed", wag)
        if self.bark_t > 0:                                 # havlıyor
            self.bark_t -= 1
            self.lift = max(self.lift, 7 * math.sin(math.pi * (1 - self.bark_t / 16)))
            pose = (pose[0], pose[1], "open", pose[3])
            if pose[0] == "lie":
                pose = ("stand", 0, "open", pose[3])
        return pose

    # ------------------------------------------------------------ GETİR OYUNU
    FETCH_MIN = 90                    # top sahibine bundan yakınsa Lila kovalamaz

    def begin_fetch(self):
        self.free = True
        self.fetch = {"stage": "wait", "t": 0, "cool": 0}

    def end_fetch(self):
        if self.free:
            self.fetch = {"stage": "home", "t": 0, "cool": 0}

    def run_to(self, tx, speed):
        dx = tx - (self.x + self.fw / 2)
        want = max(-speed, min(speed, dx * 0.18))
        self.vx += (want - self.vx) * 0.3
        self.x += self.vx
        self.phase += abs(self.vx) * 0.16
        if abs(self.vx) > 0.3:
            self.face = 1 if self.vx > 0 else -1
        return dx

    def gait(self, carrying=False):
        head = "closed" if carrying else ("open" if abs(self.vx) > 5 else "closed")
        return ("walk", int(self.phase) % 4, head, (self.t // 6) % 2)

    def mouth_xy(self):
        """Ağız noktası (dünya koordinatı)."""
        col = 21 if self.face > 0 else DGW - 21
        return self.x + col * self.GS, self.y - self.lift + 10 * self.GS

    def fetch_step(self, floor):
        pet, f, b = self.pet, self.fetch, self.pet.ball
        f["t"] += 1
        wag = (self.t // 4) % 2
        if f["cool"] > 0:
            f["cool"] -= 1
        if self.y < floor - 0.5 or self.vy < 0:             # havada (küçük zıplama)
            self.vy += 1.0
            self.y += self.vy
            if self.y >= floor:
                self.y, self.vy = floor, 0.0
            return ("walk", int(self.t * 0.5) % 4, "open", wag)
        self.y = floor
        ox = pet.x + pet.cw / 2
        cx = self.x + self.fw / 2
        st = f["stage"]
        if b is None:
            st = f["stage"] = "home"
        if st == "home":                                    # tasmaya geri dön
            fdir = -1 if pet.face_left else 1
            dx = self.run_to(ox + fdir * self.REST, 7.0)
            if abs(dx) < 22:
                self.free, self.fetch = False, None
                self.vx *= 0.5
            return self.gait()
        if st == "wait":
            if b.drag is not None:                          # top elde: heyecanla bekle
                self.face = 1 if b.cx > cx else -1
                self.vx *= 0.6
                self.x += self.vx
                self.lift = 6 * abs(math.sin(self.t * 0.35))
                return ("stand", 0, "tongue", wag)
            if b.moving:                                    # uçan / yuvarlanan topu karşıla
                self.run_to(b.cx + b.vx * 6, 9.0)
                return self.gait()
            if abs(b.cx - ox) > self.FETCH_MIN and f["cool"] <= 0 and not b.carried:
                f["stage"], f["t"] = "chase", 0
                pet.chat("ball_cheer", force=True, cooldown=500, dur=70)
                return self.gait()
            fdir = -1 if pet.face_left else 1               # topu bekleyerek sahibinin yanında dur
            dx = (ox + fdir * self.REST) - cx
            if abs(dx) > 60:
                self.run_to(ox + fdir * self.REST, 6.0)
                return self.gait()
            self.vx *= 0.6
            self.x += self.vx
            if f["t"] % 170 == 169:
                self.bark("HAU!", 36)
            if f["t"] > 420:
                return ("lie", 0, "closed", 1 if (self.t // 12) % 3 else 0)
            return ("stand", 0, "tongue" if f["t"] % 170 < 40 else "closed", wag)
        if st == "chase":
            if b.drag is not None or b.carried or f["t"] > 600:
                f["stage"], f["t"], f["cool"] = "wait", 0, 40
                return ("stand", 0, "closed", wag)
            self.run_to(b.cx + (b.vx * 5 if b.moving else 0), 9.5)
            near_y = abs((b.y + b.s) - (self.y + self.fh)) < 50
            if abs(b.cx - cx) < 28 and near_y:              # yakaladı
                b.carried, b.rest = True, False
                b.vx = b.vy = 0.0
                f["stage"], f["t"] = "return", 0
                self.vy = -6.0
                self.face = 1 if ox > cx else -1
            return self.gait()
        if st == "return":                                  # topu sahibine götür
            side = 1 if cx > ox else -1
            dx = self.run_to(ox + side * 58, 8.0)
            if abs(dx) < 16 or f["t"] > 900:
                mx, my = self.mouth_xy()
                b.carried, b.rest = False, False
                b.x, b.y = mx - b.s / 2, my - b.s / 2
                b.vx, b.vy = -side * 2.0, -6.0
                f["stage"], f["t"], f["cool"] = "wait", 0, 70
                self.bark("HAU!", 36)
                pet.on_fetch_done()
            return self.gait(carrying=b.carried)
        f["stage"] = "wait"
        return ("stand", 0, "closed", wag)

    # ------------------------------------------------------------ KURU ET
    def begin_chew(self):
        self.free, self.fetch = True, None
        self.chew = {"stage": "chase", "t": 0, "dur": random.randint(480, 660)}

    def chew_step(self, floor):
        pet, c, tr = self.pet, self.chew, self.pet.treat
        c["t"] += 1
        wag = (self.t // 4) % 2
        if self.y < floor - 0.5 or self.vy < 0:             # havada (dürtüldü / zıpladı)
            self.vy += 1.0
            self.y += self.vy
            if self.y >= floor:
                self.y, self.vy = floor, 0.0
            return ("walk", int(self.t * 0.5) % 4, "open", wag)
        self.y = floor
        cx = self.x + self.fw / 2
        st = c["stage"]
        if tr is None and st in ("chase", "sniff", "chew"):
            st = c["stage"] = "home"
        if st == "chase":
            self.run_to(tr.cx + (tr.vx * 5 if not tr.rest else 0), 9.5)
            if abs(tr.cx - cx) < 26 and tr.by >= tr.floor() - 6:
                tr.taken = True
                c["stage"], c["t"] = "sniff", 0
                self.vx = 0.0
                self.say_text, self.say_t = "*sniff*", 30
            elif c["t"] > 700:                               # ulaşamadı: vazgeç
                tr.taken = True
                c["stage"], c["t"] = "chew", 0
            return self.gait()
        if st == "sniff":
            self.vx *= 0.5
            if c["t"] > 22:
                c["stage"], c["t"] = "chew", 0
                self.bark("HAU!", 30)
            return ("stand", 0, "closed" if (c["t"] // 4) % 2 else "tongue", wag)
        if st == "chew":
            self.vx = 0.0
            if c["t"] % 7 == 0:                             # kırıntılar
                mx, my = self.chew_mouth()
                self.crumbs.append([mx + random.uniform(-6, 6), my + 4, random.uniform(-1.2, 1.2),
                                    random.uniform(-2.5, -0.5), 22])
            if c["t"] % 150 == 75:
                self.say_text, self.say_t = random.choice(["nom nom", "*chomp*", "*gnaw*", "mmm!"]), 40
            if c["t"] >= c["dur"]:
                c["stage"], c["t"] = "happy", 0
                pet.on_treat_done()
                self.bark("HAU HAU!", 45)
            gnaw = (c["t"] // 5) % 2
            self.lift = gnaw * 1.5
            return ("lie", 0, "open" if gnaw else "closed", (self.t // 10) % 2)
        if st == "happy":
            self.lift = 8 * abs(math.sin(c["t"] * 0.3))
            if c["t"] > 45:
                c["stage"], c["t"] = "home", 0
            return ("stand", 0, "tongue", wag)
        ox = pet.x + pet.cw / 2                              # tasmaya geri dön
        fdir = -1 if pet.face_left else 1
        dx = self.run_to(ox + fdir * self.REST, 7.0)
        if abs(dx) < 22 or c["t"] > 900:
            self.free, self.chew = False, None
            self.vx *= 0.5
        return self.gait()

    def chew_mouth(self):
        col = 22 if self.face > 0 else DGW - 22
        return self.x + col * self.GS, self.y - self.lift + 11 * self.GS

    def stop_chew(self):
        if self.chew:
            self.chew = {"stage": "home", "t": 0, "dur": 0}

    def update(self):
        if not self.free or not (self.fetch or self.chew):
            self.free = False
            self.crumbs = []
            return super().update()
        pet = self.pet
        self.t += 1
        self.lift = 0.0
        floor = pet.ground + pet.ch - self.fh
        pose = self.chew_step(floor) if self.chew else self.fetch_step(floor)
        if not self.free:                                   # tasmaya döndü: normal moda geç
            return super().update()
        self.x = max(0.0, min(pet.sw - self.fw, self.x))
        tm, pad = self.top_margin(), (26 if self.chew else 8)
        ay = self.y - self.lift
        minx, miny = int(self.x - pad), int(ay - tm - pad)
        w, h = int(self.fw + 2 * pad), int(self.fh + tm + 2 * pad)
        if (w > self.win_w or h > self.win_h or
                w < self.win_w - 96 or h < self.win_h - 96):
            self.win_w, self.win_h = (w + 31) // 32 * 32 + 32, (h + 31) // 32 * 32 + 32
            self.cv.config(width=self.win_w, height=self.win_h)
            self._geo = None
        geo = f"{self.win_w}x{self.win_h}+{minx}+{miny}"
        if geo != self._geo:
            self._geo = geo
            self.win.geometry(geo)
        self.cv.delete("all")
        self.cv.create_image(self.x - minx, ay - miny, anchor="nw",
                             image=self.img(pose, self.face < 0))
        c = self.chew
        if c and c["stage"] == "chew":                      # ağızdaki çubuk, kemirdikçe kısalır
            n = max(3, 7 - int(4.5 * c["t"] / max(1, c["dur"])))
            col = 21 if self.face > 0 else DGW - 21             # burnun ucundan yere doğru
            self.cv.create_image(self.x + col * self.GS - minx, ay + 10 * self.GS - miny,
                                 anchor="nw" if self.face > 0 else "ne",
                                 image=chew_image(n, self.face > 0))
        for cr in self.crumbs[:]:
            cr[0] += cr[2]
            cr[1] += cr[3]
            cr[3] += 0.35
            cr[4] -= 1
            if cr[4] <= 0:
                self.crumbs.remove(cr)
                continue
            x, y = cr[0] - minx, min(cr[1], self.y + self.fh - 3) - miny
            self.cv.create_rectangle(x, y, x + 3, y + 3, fill="#9a6a35", outline="")
        if c:
            self.extra(self.cv, minx, miny)
            return
        if self.fetch["stage"] == "return" and pet.ball and pet.ball.carried:
            mx, my = self.mouth_xy()
            self.cv.create_image(mx - minx, my - miny, anchor="center",
                                 image=ball_image(0, 3))
        self.extra(self.cv, minx, miny)

    def extra(self, cv, minx, miny):
        ay = self.y - self.lift
        hx = self.x + (19 if self.face > 0 else DGW - 19) * self.GS - minx
        top = ay - miny
        if self.say_t > 0:
            self.say_t -= 1
            tw = self.font.measure(self.say_text) + 14
            y2 = top - 4
            y1 = y2 - 20
            cv.create_rectangle(hx - tw / 2 - 2, y1 - 2, hx + tw / 2 + 2, y2 + 2,
                                fill="#16111a", outline="")
            cv.create_rectangle(hx - tw / 2, y1, hx + tw / 2, y2,
                                fill="#fff4ea", outline="")
            cv.create_polygon(hx - 4, y2, hx + 4, y2, hx, y2 + 7,
                              fill="#fff4ea", outline="#16111a")
            cv.create_text(hx, (y1 + y2) / 2, text=self.say_text, fill="#8a3ffc",
                           font=self.font)
        elif self.sleeping():
            for i, ch in enumerate("zZ"):                   # piksel glif: kenar lekesi yok
                ph = ((self.t // 3) + i * 9) % 30
                cv.create_image(hx + 6 + i * 11, top - 2 - ph * 0.5, anchor="s",
                                image=text_image(ch, "#6f7cff", 2))


# ===========================================================================
#  PİKSEL YAZI TİPİ  (şeffaf zeminde anti-aliasing kenar lekesi olmasın diye)
#  Karakterin etrafında uçuşan kalp / nota / Zzz / "!" gibi efektler yazı yerine
#  bu bitmap glifleriyle çizilir.
# ===========================================================================
GLYPHS = {
    "C": [" ### ", "#   #", "#    ", "#    ", "#    ", "#   #", " ### "],
    "L": ["#    ", "#    ", "#    ", "#    ", "#    ", "#    ", "#####"],
    "I": ["#####", "  #  ", "  #  ", "  #  ", "  #  ", "  #  ", "#####"],
    "K": ["#   #", "#  # ", "# #  ", "##   ", "# #  ", "#  # ", "#   #"],
    "!": ["  #  ", "  #  ", "  #  ", "  #  ", "  #  ", "     ", "  #  "],
    "1": ["  #  ", " ##  ", "  #  ", "  #  ", "  #  ", "  #  ", " ### "],
    "2": [" ### ", "#   #", "    #", "   # ", "  #  ", " #   ", "#####"],
    "3": [" ### ", "#   #", "    #", "  ## ", "    #", "#   #", " ### "],
    "z": ["#####", "   # ", "  #  ", " #   ", "#####"],
    "Z": ["#####", "    #", "   # ", "  #  ", " #   ", "#    ", "#####"],
    "~": [" #   ", "# # #", "   # "],
    "…": ["# # #"],
    "♥": [" ## ## ", "#######", "#######", " ##### ", "  ###  ", "   #   "],
    "♪": ["   ##", "   # ", "   # ", "   # ", " ### ", "#### ", " ##  "],
    "♫": ["  #####", "  #   #", "  #   #", "  #   #", " ##  ##", "### ###", " ##  ##"],
    "✦": ["  #  ", " ### ", "#####", " ### ", "  #  "],
    "?": [" ### ", "#   #", "    #", "   # ", "  #  ", "     ", "  #  "],
    "A": [" ### ", "#   #", "#   #", "#####", "#   #", "#   #", "#   #"],
    "H": ["#   #", "#   #", "#   #", "#####", "#   #", "#   #", "#   #"],
    "W": ["#   #", "#   #", "#   #", "# # #", "# # #", "## ##", "#   #"],
    "O": [" ### ", "#   #", "#   #", "#   #", "#   #", "#   #", " ### "],
    "✖": ["#   #", " # # ", "  #  ", " # # ", "#   #"],
}
_BOTTOM = {"z", "…"}
_TXT_IMG = {}


def text_image(txt, color, scale):
    """Metni piksel glifleriyle çizilmiş (anti-aliasing'siz) PhotoImage olarak döndürür."""
    key = (txt, color, scale)
    im = _TXT_IMG.get(key)
    if im is None:
        rows = [""] * 7
        for ch in txt:
            g = GLYPHS.get(ch)
            if not g:
                continue
            w, h = len(g[0]), len(g)
            top = 7 - h if ch in _BOTTOM else (7 - h) // 2
            for r in range(7):
                src = r - top
                line = g[src] if 0 <= src < h else " " * w
                rows[r] += line.replace("#", "x").replace(" ", ".") + "."
        wmax = max(1, max(len(r) for r in rows))
        grid = [r.ljust(wmax, ".") for r in rows]
        im = grid_to_image(grid, {"x": color}, False, scale)
        _TXT_IMG[key] = im
    return im


def glyph_scale(size, life=99):
    sc = 1 if size < 10 else 2 if size < 18 else 3
    return max(1, sc - 1) if life < 8 else sc


# ===========================================================================
#  KONUŞMA / DÜŞÜNCE BALONU  (ayrı pencere: çok satırlı, solarak kaybolur)
# ===========================================================================
def pix_rect(cv, x1, y1, x2, y2, fill, c, tags=""):
    cv.create_rectangle(x1 + c, y1, x2 - c, y2, fill=fill, outline="", tags=tags)
    cv.create_rectangle(x1, y1 + c, x2, y2 - c, fill=fill, outline="", tags=tags)


SPEECH_STYLE = {          # fill, outline, text
    "say":   ("#fff4ea", "#3a1f1c", "#3a1f1c"),
    "angry": ("#fff4ea", "#3a1f1c", "#d62839"),
    "think": ("#f1eaff", "#4b3a7a", "#4b3a7a"),
    "love":  ("#ffe3ee", "#a3214f", "#a3214f"),
}


class Speech:
    M, TAIL = 8, 16

    def __init__(self, pet, text, kind="say", dur=100):
        self.pet, self.kind, self.life, self.dur = pet, kind, dur, dur
        f = pet.speech_font
        lines, cur = [], ""
        words = []
        for w in text.split():                       # çok uzun kelimeleri böl
            while len(w) > 24:
                words.append(w[:24])
                w = w[24:]
            words.append(w)
        for w in words:
            trial = (cur + " " + w).strip()
            if f.measure(trial) <= 210 or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        lines = (lines or [""])[:5 if kind in ("love", "think") else 3]
        tw = max(f.measure(l) for l in lines) + 24
        th = len(lines) * 17 + 14
        M = self.M
        self.ww, self.wh = tw + 2 * M, th + self.TAIL + 2 * M
        fill, out, tcol = SPEECH_STYLE.get(kind, SPEECH_STYLE["say"])

        w = self.win = tk.Toplevel(pet.root)
        w.overrideredirect(True)
        w.wm_attributes("-topmost", True)
        make_transparent(w)
        try:
            w.attributes("-alpha", 0.0)
        except tk.TclError:
            pass
        cv = tk.Canvas(w, width=self.ww, height=self.wh, bg=KEY, highlightthickness=0)
        cv.pack()
        pix_rect(cv, M + 3, M + 4, M + tw + 3, M + th + 4, B_SHADOW, 5)
        pix_rect(cv, M - 3, M - 3, M + tw + 3, M + th + 3, out, 7)
        pix_rect(cv, M, M, M + tw, M + th, fill, 5)
        cx = self.ww / 2
        yb = M + th
        if kind == "think":                         # düşünce baloncukları
            for dx, dy, r in ((0, 2, 5), (3, 10, 3.5), (6, 16, 2.2)):
                cv.create_oval(cx + dx - r - 1, yb + dy - r - 1, cx + dx + r + 1,
                               yb + dy + r + 1, fill=out, outline="")
                cv.create_oval(cx + dx - r, yb + dy - r, cx + dx + r, yb + dy + r,
                               fill=fill, outline="")
        else:                                       # kuyruk
            for hw, dy in ((8, -1), (5, 5), (2, 10)):
                cv.create_rectangle(cx - hw - 2, yb + dy, cx + hw + 2, yb + dy + 6,
                                    fill=out, outline="")
            for hw, dy in ((6, -3), (3, 4), (1, 9)):
                cv.create_rectangle(cx - hw, yb + dy, cx + hw, yb + dy + 6,
                                    fill=fill, outline="")
        for i, l in enumerate(lines):
            cv.create_text(self.ww / 2, M + 7 + 8 + i * 17, text=l, fill=tcol, font=f)
        self.update()

    def update(self):
        pet = self.pet
        x = int(max(0, min(pet.x + pet.cw / 2 - self.ww / 2, pet.sw - self.ww)))
        y = int(max(0, pet.y + PADT + 4 * SCALE - self.wh + self.M))
        if self.kind == "angry" and self.dur - self.life < 28:
            x += random.choice((-2, 0, 2))
            y += random.choice((-1, 0, 1))
        self.win.geometry(f"+{x}+{y}")
        age = self.dur - self.life
        a = min(1.0, age / 5.0) if age < 5 else 1.0
        if self.life < 10:
            a = max(0.0, self.life / 10.0)
        try:
            self.win.attributes("-alpha", a)
        except tk.TclError:
            pass
        self.life -= 1
        return self.life > 0

    def destroy(self):
        try:
            self.win.destroy()
        except tk.TclError:
            pass


# ===========================================================================
#  MASA OBJELERİ (sürüklenebilir; lamba tıklayınca açılıp kapanır)
# ===========================================================================
class DeskProp:
    SC = 3

    def __init__(self, pet, kind, x=None, on=True):
        self.pet, self.kind = pet, kind
        self.on = bool(on) if kind == "lamp" else False     # lamba dışında hep kapalı başlar
        self.hidden = False                                  # karakter kullanırken görünmez
        on = self.on
        w = self.win = tk.Toplevel(pet.root)
        w.overrideredirect(True)
        w.wm_attributes("-topmost", True)
        make_transparent(w)
        self.gw = PROP_W[kind]
        self.gh = len(prop_grid(kind, 0, on))
        self.pw, self.ph = self.gw * self.SC, self.gh * self.SC
        self.cv = tk.Canvas(w, width=self.pw, height=self.ph, bg=KEY, highlightthickness=0)
        self.cv.pack()
        self.item = self.cv.create_image(0, 0, anchor="nw")
        self.x = float(x if x is not None else random.randint(120, max(130, pet.sw - 220)))
        self.y = float(pet.ground + pet.ch - self.ph)
        self.vy = self.vx = 0.0
        self.t = random.randint(0, 200)
        self.drag = None
        self.moved = 0
        self.imgs = {}
        self.cur = None
        self._geo = None
        cv = self.cv
        cv.bind("<ButtonPress-1>", self.on_press)
        cv.bind("<B1-Motion>", self.on_drag)
        cv.bind("<ButtonRelease-1>", self.on_release)
        self.update()

    def state(self):
        return {"kind": self.kind, "x": int(self.x), "on": bool(self.on)}

    def frame(self):
        if self.kind == "plant":
            return (self.t // 22) % 4
        if self.kind == "mug":
            return (self.t // 14) % 2
        if self.kind == "radio":
            return (self.t // 8) % 2 if self.on else 0
        if self.kind == "mirror":
            return (self.t // 10) % 2 if self.on else 0
        return 0

    def on_press(self, e):
        self.drag = (e.x, e.y)
        self.moved = 0
        self.vy = self.vx = 0.0

    def knock(self, d):
        """Kaos: karakter çarpınca obje havaya fırlar, kayarak yere düşer."""
        if self.drag or self.hidden:
            return
        self.vy = -random.uniform(7.0, 10.0)
        self.vx = d * random.uniform(4.5, 7.5)
        self.y -= 1

    def on_drag(self, e):
        self.moved += 1
        self.x = self.pet.root.winfo_pointerx() - self.drag[0]
        self.y = self.pet.root.winfo_pointery() - self.drag[1]

    def on_release(self, e):
        click = self.moved < 3
        self.drag = None
        if click:                                            # tıklayınca karakter gelip kullanır
            self.pet.visit_prop(self.kind)
        self.pet.save_soon()

    def update(self):
        self.t += 1
        if self.hidden:                                      # kullanımda: ekran dışına al
            if self._geo != "+-3000+-3000":
                self._geo = "+-3000+-3000"
                self.win.geometry(self._geo)
            return
        if not self.drag:
            floor = self.pet.ground + self.pet.ch - self.ph
            if self.y < floor - 0.5:
                self.vy += 1.0
                self.y = min(self.y + self.vy, floor)
            else:
                self.y, self.vy = floor, 0.0
            if self.vx:
                self.x += self.vx
                self.vx *= 0.98 if self.y < floor - 0.5 else 0.8
                if abs(self.vx) < 0.3:
                    self.vx = 0.0
                hi = self.pet.sw - self.pw
                if self.x < 0 or self.x > hi:
                    self.x, self.vx = max(0.0, min(float(hi), self.x)), -self.vx * 0.5
        key = (self.frame(), self.on)
        if key != self.cur:
            self.cur = key
            if key not in self.imgs:
                self.imgs[key] = grid_to_image(prop_grid(self.kind, self.t, self.on),
                                               PROP_PAL, False, self.SC)
            self.cv.itemconfig(self.item, image=self.imgs[key])
        geo = f"+{round(self.x)}+{round(self.y)}"
        if geo != self._geo:
            self._geo = geo
            self.win.geometry(geo)

    def destroy(self):
        try:
            self.win.destroy()
        except tk.TclError:
            pass


# ===========================================================================
#  TOP  (Lila ile getir-götür oyunu)
# ===========================================================================
BALL_PAL = {"o": "#3a1f1c", "r": "#ff5c7a", "w": "#ffd9e0", "d": "#d93a5a"}
_BALL_BASE = ["..oooo..", ".orrrro.", "orrrrrro", "orrrrrro",
              "orrrrrdo", "orrrrddo", ".oddddo.", "..oooo.."]
_BALL_SPOT = [(2, 2), (4, 2), (5, 3), (3, 3)]
_BALL_IMG = {}


def ball_image(frame, scale=3):
    k = (frame % 4, scale)
    im = _BALL_IMG.get(k)
    if im is None:
        g = [list(r) for r in _BALL_BASE]
        x, y = _BALL_SPOT[k[0]]
        g[y][x] = "w"
        im = _BALL_IMG[k] = grid_to_image(["".join(r) for r in g], BALL_PAL, False, scale)
    return im


CHAOS_ICON = ["....oooo..", "...oyyyo..", "..oyyyo...", ".oyyyoooo.", "oyyyyyyyo.",
              "ooooyyyo..", "...oyyo...", "..oyyo....", ".oyo......", ".oo......."]
_CHAOS_IMG = []


TREAT = [".oooooooooo.", "oNMNMNMNMNNo", ".oooooooooo."]
CHEW = [".....oo", "....oNo", "...oMo.", "..oNo..", ".oMo...", "oNo....", "oo....."]
_TREAT_IMG = {}


def treat_image(n=10, scale=3, vertical=False):
    """Kuru et çubuğu; n = kalan uzunluk (kemirdikçe kısalır)."""
    k = (n, scale, vertical)
    if k not in _TREAT_IMG:
        rows = [r[:n + 1] + ("." if i != 1 else "o") for i, r in enumerate(TREAT)] if n < 10 else TREAT
        if vertical:
            rows = ["".join(r[i] for r in rows) for i in range(len(rows[0]))]
        _TREAT_IMG[k] = grid_to_image(rows, PAL, False, scale)
    return _TREAT_IMG[k]


def chew_image(n=7, flip=False, scale=3):
    """Lila'nın patileri arasında tuttuğu çapraz çubuk; n satır kalır (alttan kısalır)."""
    k = ("chew", n, flip, scale)
    if k not in _TREAT_IMG:
        rows = CHEW[:n]
        _TREAT_IMG[k] = grid_to_image(rows, PAL, flip, scale)
    return _TREAT_IMG[k]


def game_icon(iid):
    if iid == "treat":
        return treat_image(10, 3)
    if iid == "chaos":
        if not _CHAOS_IMG:
            _CHAOS_IMG.append(grid_to_image(CHAOS_ICON, {"o": "#3a1f1c", "y": "#ffd23f"}, False, 3))
        return _CHAOS_IMG[0]
    return hand_image("scissors", 2) if iid == "rps" else ball_image(0, 3)


class Treat:
    """Lila için atılan kuru et: uçar, sekip yere düşer; Lila alınca gizlenir."""
    W = 36

    def __init__(self, pet, x, by, vx, vy):
        self.pet = pet
        w = self.win = tk.Toplevel(pet.root)
        w.overrideredirect(True)
        w.wm_attributes("-topmost", True)
        make_transparent(w)
        self.cv = tk.Canvas(w, width=self.W, height=self.W, bg=KEY, highlightthickness=0)
        self.cv.pack()
        self.item = self.cv.create_image(self.W // 2, self.W, anchor="s")
        self.x, self.by, self.vx, self.vy = float(x), float(by), float(vx), float(vy)
        self.rest = self.taken = False
        self.t = 0
        self._geo = self._img = None
        self.update()

    @property
    def cx(self):
        return self.x + self.W / 2

    def floor(self):
        return self.pet.ground + self.pet.ch

    def update(self):
        self.t += 1
        if self.taken:
            if self._geo != "+-3000+-3000":
                self._geo = "+-3000+-3000"
                self.win.geometry(self._geo)
            return
        fl = self.floor()
        if not self.rest:
            self.vy += 1.0
            self.x += self.vx
            self.by += self.vy
            hi = self.pet.sw - self.W
            if self.x < 0 or self.x > hi:
                self.x, self.vx = max(0.0, min(float(hi), self.x)), -self.vx * 0.6
            if self.by >= fl:
                self.by = fl
                self.vy = -self.vy * 0.35 if self.vy > 4 else 0.0
                self.vx *= 0.7
                if self.vy == 0.0 and abs(self.vx) < 0.4:
                    self.rest, self.vx = True, 0.0
        else:
            self.by = fl
        img = treat_image(10, 3, vertical=(not self.rest and (self.t // 4) % 2 == 1))
        if img is not self._img:
            self._img = img
            self.cv.itemconfig(self.item, image=img)
        geo = f"+{round(self.x)}+{round(self.by) - self.W}"
        if geo != self._geo:
            self._geo = geo
            self.win.geometry(geo)

    def destroy(self):
        try:
            self.win.destroy()
        except tk.TclError:
            pass


# ===========================================================================
#  MASAÜSTÜ SÜRPRİZLERİ (ara sıra beliren, tıklayınca toplanan küçük hediyeler)
# ===========================================================================
SURPRISE_PAL = {"o": "#3a1f1c", "r": "#ff5c7a", "R": "#d93a5a", "y": "#ffd23f", "Y": "#e0a400",
                "g": "#62c79d", "G": "#2a9d5c", "w": "#ffffff", "p": "#ff9ebd", "u": "#8a3ffc",
                "b": "#6c7bff", "c": "#fff4ea"}
SURPRISES = {
    "flower": ["..ooo..", ".oppo..", "opyypo.", ".oppo..", "..oGo..", ".oGGo..", "..oGo.."],
    "heart": [".oo.oo.", "orrorro", "orwrrRo", "orrrrRo", ".orrRo.", "..oRo..", "...o..."],
    "star": ["...o...", "..oyo..", "ooyyyoo", "oyyyyYo", ".oyyYo.", "oyYoYYo", "oo...oo"],
    "candy": ["o.....o", "pooooop", "opwprpo", "oprpwpo", "pooooop", "o.....o"],
    "clover": [".oo.oo.", "ogGogGo", ".ooGoo.", "ogGogGo", ".oo.oo.", "...o...", "...o..."],
    "gift": ["..o.o..", "ooouooo", "orruRro", "ooouooo", "orruRro", "orruRro", "ooooooo"],
}
_SURP_IMG = {}


def surprise_image(kind, scale=3):
    k = (kind, scale)
    if k not in _SURP_IMG:
        g = SURPRISES[kind]
        w = max(len(r) for r in g)
        _SURP_IMG[k] = grid_to_image([r.ljust(w, ".") for r in g], SURPRISE_PAL, False, scale)
    return _SURP_IMG[k]


class Surprise:
    W, H = 30, 34
    LIFE = 4 * 60 * 30                                       # ~4 dk sonra kaybolur

    def __init__(self, pet, kind, x):
        self.pet, self.kind = pet, kind
        w = self.win = tk.Toplevel(pet.root)
        w.overrideredirect(True)
        w.wm_attributes("-topmost", True)
        make_transparent(w)
        self.cv = tk.Canvas(w, width=self.W, height=self.H, bg=KEY, highlightthickness=0,
                            cursor="hand2")
        self.cv.pack()
        self.item = self.cv.create_image(self.W // 2, self.H, anchor="s",
                                         image=surprise_image(kind))
        self.cv.bind("<Button-1>", lambda e: self.pet.collect_surprise(self, True))
        self.x = float(x)
        self.t = 0
        self.pet_ok = random.random() < 0.5                # karakter yürürken kendisi de alabilir
        self.gone = False
        self._geo = None
        self.update()

    @property
    def cx(self):
        return self.x + self.W / 2

    def update(self):
        """False dönerse süresi bitti."""
        self.t += 1
        if self.t > self.LIFE:
            return False
        bob = round(2 * math.sin(self.t * 0.08))
        if self.t < 12:                                     # yerden fırlar
            bob = -int(16 * math.sin(math.pi * self.t / 12))
        blink = self.t > self.LIFE - 90 and (self.t // 6) % 2
        y = self.pet.ground + self.pet.ch - self.H + bob
        geo = "+-3000+-3000" if blink else f"+{round(self.x)}+{y}"
        if geo != self._geo:
            self._geo = geo
            self.win.geometry(geo)
        return True

    def destroy(self):
        self.gone = True
        try:
            self.win.destroy()
        except tk.TclError:
            pass


class Ball:
    """Sürüklenip fırlatılabilen top. Fizik: yerçekimi, sekme, sürtünme. Lila taşırken gizlenir."""
    SC, N = 3, 8

    def __init__(self, pet, x, y, vx=0.0, vy=0.0):
        self.pet = pet
        w = self.win = tk.Toplevel(pet.root)
        w.overrideredirect(True)
        w.wm_attributes("-topmost", True)
        make_transparent(w)
        self.s = self.N * self.SC
        self.cv = tk.Canvas(w, width=self.s, height=self.s, bg=KEY, highlightthickness=0)
        self.cv.pack()
        self.item = self.cv.create_image(0, 0, anchor="nw")
        self.x, self.y, self.vx, self.vy = float(x), float(y), float(vx), float(vy)
        self.drag = None
        self.moved = 0
        self.samples = []
        self.rest = False
        self.carried = False
        self.rot = 0.0
        self.frame = None
        self._geo = None
        cv = self.cv
        cv.bind("<ButtonPress-1>", self.on_press)
        cv.bind("<B1-Motion>", self.on_drag)
        cv.bind("<ButtonRelease-1>", self.on_release)
        for seq in ("<Button-3>", "<Button-2>"):
            cv.bind(seq, lambda e: self.pet.end_ball())     # sağ tık: oyunu bitir
        self.update()

    @property
    def cx(self):
        return self.x + self.s / 2

    @property
    def moving(self):
        return not (self.rest or self.carried or self.drag is not None)

    def on_press(self, e):
        self.drag = (e.x, e.y)
        self.moved = 0
        self.samples = []
        self.vx = self.vy = 0.0
        self.rest = False
        self.pet.touch_ball()

    def on_drag(self, e):
        self.moved += 1
        px, py = self.pet.root.winfo_pointerx(), self.pet.root.winfo_pointery()
        self.x, self.y = px - self.drag[0], py - self.drag[1]
        self.samples = (self.samples + [(time.time(), px, py)])[-8:]

    def on_release(self, e):
        now = time.time()
        sm = [p for p in self.samples if now - p[0] < 0.12]
        vx = vy = 0.0
        if len(sm) >= 2 and sm[-1][0] > sm[0][0]:
            k = TICK_MS / 1000.0 / (sm[-1][0] - sm[0][0])
            vx, vy = (sm[-1][1] - sm[0][1]) * k, (sm[-1][2] - sm[0][2]) * k
        self.drag = None
        self.samples = []
        self.vx = max(-34.0, min(34.0, vx))
        self.vy = max(-34.0, min(30.0, vy))
        self.pet.touch_ball()

    def step(self):
        pet = self.pet
        floor = pet.ground + pet.ch - self.s
        if self.rest:
            self.y = floor
            return
        self.vy += 0.9
        self.x += self.vx
        self.y += self.vy
        hi = pet.sw - self.s
        if self.x < 0:
            self.x, self.vx = 0.0, abs(self.vx) * 0.7
        elif self.x > hi:
            self.x, self.vx = float(hi), -abs(self.vx) * 0.7
        if self.y < 0:
            self.y, self.vy = 0.0, abs(self.vy) * 0.5
        if self.y >= floor:
            self.y = floor
            self.vy = -self.vy * 0.55 if abs(self.vy) > 3 else 0.0
            self.vx *= 0.96
            if abs(self.vx) < 0.35 and self.vy == 0.0:
                self.vx, self.rest = 0.0, True
        self.rot += self.vx * 0.12

    def update(self):
        if self.carried:                                    # Lila ağzında: kendi tuvalinde çizilir
            if self._geo != "+-3000+-3000":
                self._geo = "+-3000+-3000"
                self.win.geometry(self._geo)
            return
        if self.drag is None:
            self.step()
        fr = int(self.rot) % 4
        if fr != self.frame:
            self.frame = fr
            self.cv.itemconfig(self.item, image=ball_image(fr, self.SC))
        geo = f"+{round(self.x)}+{round(self.y)}"
        if geo != self._geo:
            self._geo = geo
            self.win.geometry(geo)

    def destroy(self):
        try:
            self.win.destroy()
        except tk.TclError:
            pass


# ===========================================================================
#  PENCERE İZLEYİCİ  (tırmanma için platformlar; platforma özel + güvenli fallback)
# ===========================================================================
def _win_provider():
    import ctypes
    from ctypes import wintypes
    user32, dwm = ctypes.windll.user32, ctypes.windll.dwmapi
    pid = os.getpid()
    proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    H, DW = wintypes.HWND, wintypes.DWORD            # 64-bit tanıtıcılar için tip tanımları
    user32.IsWindowVisible.argtypes = [H]
    user32.IsIconic.argtypes = [H]
    user32.GetWindowTextLengthW.argtypes = [H]
    user32.GetWindowLongW.argtypes = [H, ctypes.c_int]
    user32.GetWindowThreadProcessId.argtypes = [H, ctypes.POINTER(DW)]
    user32.GetWindowRect.argtypes = [H, ctypes.POINTER(wintypes.RECT)]
    user32.EnumWindows.argtypes = [proc, wintypes.LPARAM]
    dwm.DwmGetWindowAttribute.argtypes = [H, DW, ctypes.c_void_p, DW]
    dwm.DwmGetWindowAttribute.restype = ctypes.c_long

    def get():
        out = []

        def cb(hwnd, _lp):
            try:
                if not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd):
                    return True
                cloaked = ctypes.c_int(0)
                dwm.DwmGetWindowAttribute(hwnd, 14, ctypes.byref(cloaked), ctypes.sizeof(cloaked))
                if cloaked.value:
                    return True
                p = wintypes.DWORD(0)
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
                if p.value == pid or user32.GetWindowTextLengthW(hwnd) == 0:
                    return True
                if user32.GetWindowLongW(hwnd, -20) & 0x80:          # araç penceresi
                    return True
                r = wintypes.RECT()
                if dwm.DwmGetWindowAttribute(hwnd, 9, ctypes.byref(r), ctypes.sizeof(r)) != 0:
                    user32.GetWindowRect(hwnd, ctypes.byref(r))
                out.append((int(hwnd or 0), r.left, r.top, r.right, r.bottom))
            except Exception:
                pass
            return True
        user32.EnumWindows(proc(cb), 0)
        return out                                                   # üstten alta z-sırası
    return get, True


def _mac_provider():
    import Quartz                                                    # pyobjc-framework-Quartz
    pid = os.getpid()
    opts = Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements

    def get():
        out = []
        for w in Quartz.CGWindowListCopyWindowInfo(opts, Quartz.kCGNullWindowID) or []:
            if w.get("kCGWindowLayer", 1) != 0 or w.get("kCGWindowOwnerPID") == pid:
                continue
            if w.get("kCGWindowAlpha", 1) < 0.1:
                continue
            b = w.get("kCGWindowBounds") or {}
            if any(k not in b for k in ("X", "Y", "Width", "Height")):
                continue
            out.append((int(w.get("kCGWindowNumber", 0)), int(b["X"]), int(b["Y"]),
                        int(b["X"] + b["Width"]), int(b["Y"] + b["Height"])))
        return out
    return get, True


def _linux_provider():
    import shutil
    import subprocess
    if not shutil.which("wmctrl") or not os.environ.get("DISPLAY"):
        raise RuntimeError("wmctrl/X11 yok")
    pid = os.getpid()

    def get():
        txt = subprocess.run(["wmctrl", "-lGp"], capture_output=True, text=True,
                             timeout=1.5).stdout
        out = []
        for line in txt.splitlines():
            p = line.split(None, 8)
            if len(p) < 8 or p[1] == "-1" or int(p[2]) == pid:
                continue
            x, y, w, h = (int(v) for v in p[3:7])
            out.append((int(p[0], 16), x, y, x + w, y + h))
        return out
    return get, False                                                # z-sırası bilinmiyor


def window_platforms(rects, sw, sh, ch, ordered):
    """Ham pencere dikdörtgenlerinden tünek yapılabilecek üst kenarları seçer."""
    plats = []
    for i, (wid, x1, y1, x2, y2) in enumerate(rects):
        w, h = x2 - x1, y2 - y1
        if w < 160 or h < 80:
            continue
        if w >= sw - 4 and h >= sh - 80:                              # tam ekran / büyütülmüş
            continue
        if y1 < ch * 0.6 or y1 > sh - 120 or x2 < 40 or x1 > sw - 40:
            continue
        cx1, cx2 = max(x1, 0), min(x2, sw)
        if cx2 - cx1 < 140:
            continue
        if ordered:                                                   # üst kenar örtülü mü?
            vis = 0
            for f in (0.2, 0.5, 0.8):
                px, py = cx1 + (cx2 - cx1) * f, y1 + 2
                if not any(a1 <= px <= a2 and b1 <= py <= b2
                           for (_i, a1, b1, a2, b2) in rects[:i]):
                    vis += 1
            if vis < 2:
                continue
        plats.append({"id": wid, "x1": cx1, "x2": cx2, "y": y1})
    return plats


class WindowWatcher:
    """Arka plan iş parçacığı: 0,6 sn'de bir pencere kenarlarını günceller.
    Hata verirse / destek yoksa sessizce kapanır ve platform listesi boş kalır."""

    def __init__(self, pet, provider=None):
        self.pet = pet
        self.platforms = []
        self.kind = "yok"
        self.get = None
        self.ordered = True
        self.fail = 0
        try:
            if provider is not None:
                self.get, self.ordered = provider
                self.kind = "özel"
            elif IS_WIN:
                self.get, self.ordered = _win_provider()
                self.kind = "windows"
            elif IS_MAC:
                self.get, self.ordered = _mac_provider()
                self.kind = "macos"
            elif sys.platform.startswith("linux"):
                self.get, self.ordered = _linux_provider()
                self.kind = "linux"
        except Exception:
            self.get = None
            self.kind = "yok"
        if self.get:
            threading.Thread(target=self._loop, daemon=True).start()

    def available(self):
        return self.get is not None

    def poll_once(self):
        rects = self.get()
        return window_platforms(rects, self.pet.sw, self.pet.sh, self.pet.ch, self.ordered)

    def _loop(self):
        while self.get is not None:
            time.sleep(0.6)
            if not self.pet.prefs.get("climb", True):
                self.platforms = []
                continue
            try:
                self.platforms = self.poll_once()
                self.fail = 0
            except Exception:
                self.fail += 1
                if self.fail >= 5:                                    # güvenli geri çekilme
                    self.get = None
                    self.platforms = []


# ===========================================================================
#  REPLİKLER (EN / TR)
# ===========================================================================
LINES = {
    "en": {
        "poke": ["Hehe!", "Boop!", "Aww ♥", "More cuddles?", "You're sweet!"],
        "hug": ["♥♥♥", "So warm...", "Best hug ever!"],
        "kiss": ["Mwah!", "♥"],
        "neglect": ["Hey... remember me?", "I'm right here, you know.",
                    "Psst. Pay attention to me?", "Hello? Anybody?"],
        "bored": ["*sigh*", "So bored...", "Nothing to do..."],
        "sulk": ["Hmph.", "I'm not mad. (I'm mad.)", "...", "Fine. Ignore me."],
        "forgive": ["Okay okay... ♥", "Hmph... fine, I forgive you.", "Aww, you came back!"],
        "sleepy": ["So sleepy...", "Five more minutes...", "*yawn*"],
        "wake": ["Good as new!", "Ahh, nap time worked!"],
        "happy": ["Best. Day. Ever!", "Life is good ♥", "So gay! I'm so happy!"],
        "equip": ["Looking good!", "Ooh, fancy!", "How do I look?", "Ooh, so gay!"],
        "unequip": ["Back to basics.", "Okay!"],
        "frog": ["Ribbit says hi!", "Froggy friend!"],
        "dog": ["Lila! Good girl!", "Walkies!"],
        "perch": ["I can see everything from here!", "Nice view!", "Look at me, I'm up high!"],
        "fall": ["Whoa!", "Eek!"],
        "welcome": ["I'm back! Missed you ♥", "Welcome back!"],
        "welcome_long": ["You were gone so long...", "Where were you? I missed you!"],
        "noted": ["Noted!", "Got it!", "I'll remind you ♥"],
        "done": ["Nice, one less thing!", "Yay, done!", "So gay, done!"],
        "selfie": ["Say cheese!", "Perfect shot!", "So gay! Perfect shot!"],
        "sniff": ["Ohh... lovely!", "Mmm... ahh!", "Ohh! So fresh!"],
        "sip": ["Ahh, so good!", "Mmm, still warm!", "Perfect cup!"],
        "lamp_on": ["Let there be light!", "Click! Cozy."],
        "lamp_off": ["Lights out.", "Click! Nap light."],
        "read": ["Hmm, interesting...", "Just one more page..."],
        "mirror": ["Ta-da! How do I look?", "Mirror mirror... gorgeous!", "Hehe, I look cute."],
        "cupcake": ["Nom nom nom!", "Cupcake time!", "Sooo yummy!"],
        "teddy": ["Squishy hug ♥", "Teddy is the best.", "Mmm, so cuddly."],
        "cactus": ["Ouch! It's prickly!", "Ow ow ow!", "Cactus 1, me 0."],
        "e_love": ["♥♥♥", "I love you!", "Aww ♥"],
        "e_wow": ["Wow!", "Whoa!", "So gay!", "Amazing!"],
        "e_wink": ["Hehe ;)", "Wink wink!", "Psst... ♥"],
        "e_shy": ["Stoppp, I'm blushing...", "Hehe... shy.", "Oh nooo ♥"],
        "e_laugh": ["Hahaha!", "I can't stop!", "Stoooop, so funny!"],
        "e_super": ["Super!", "So gay!", "Super! So gay!", "Yaaay, super!"],
        "e_cry": ["Waaah...", "Sniff sniff...", "That's so sad..."],
        "e_angry": ["Grrr!", "Hmph!!", "I'm so mad!"],
        "e_dizzy": ["Whoa... spinny...", "Everything is swirling...", "Dizzy!"],
        "e_shock": ["WHAT?!", "No way!", "Seriously?!"],
        "calm_on": ["Shhh... I'll be quiet.", "Calm mode. Cozy."],
        "intro": ["Hi, I'm Pocket Karolina ♥ Right-click me for the menu, or just say hi with a click!"],
        "radio": ["Turn it up!", "I love this song!", "So gay, I love this song!"],
        "chair": ["Ahh, comfy.", "Sitting is nice."],
        "held": ["Wheee!", "I'm flying!", "Hehe, careful!"],
        "held_annoyed": ["Hey! Put me down!", "I'm not a kitten!", "Okay, enough now..."],
        "panic": ["Wah!", "Whoaa!", "Too fast!"],
        "remind": "Reminder: {text}", "due": "Time for: {text}!",
        "d_cuddle": "Dear diary: {n} cuddles today ♥",
        "d_selfie": "Dear diary: {n} selfies today. I look great!",
        "d_climb": "Dear diary: I climbed {n} windows today!",
        "d_dog": "Dear diary: Lila was a very good girl today.",
        "d_frog": "Dear diary: Froggy hopped all day.",
        "d_happy": "Dear diary: feeling wonderful today!",
        "d_meh": "Dear diary: a bit lonely today...",
        "d_plain": "Dear diary: a cozy day on the desktop.",
        "rps_hi": ["Rock paper scissors? You're on!", "Let's play!"],
        "rps_count": ["Rock!", "Paper!", "Scissors!", "Shoot!"],
        "rps_win": ["Yay, I win!", "Ha! Too easy!", "Victory dance!", "So gay, I win!"],
        "rps_lose": ["Noooo! Rematch!", "You got me...", "Beginner's luck!"],
        "rps_draw": ["Tie! Again!", "Great minds think alike!"],
        "ball_start": ["Ball time!", "Throw it!"],
        "ball_cheer": ["Fetch, Lila!", "Go go go!"],
        "ball_back": ["Good girl!!", "Best dog ever!", "Drop it... good!", "So gay! Good girl!"],
        "ball_end": ["That was fun!", "Lila is tired!"],
        "msg_new": "New message ♥",
        "outfit_new": ["Ooh, a new look!", "Someone picked my outfit!", "Ooh, so gay!"],
    },
    "tr": {
        "poke": ["Hihi!", "Bop!", "Ayy ♥", "Biraz daha sevsene?", "Çok tatlısın!"],
        "hug": ["♥♥♥", "Çok sıcak...", "En güzel sarılma!"],
        "kiss": ["Mwah!", "♥"],
        "neglect": ["Hey... beni unuttun mu?", "Buradayım ama!", "Psst. Bana da bak?",
                    "Alo? Kimse yok mu?"],
        "bored": ["*of*", "Çok sıkıldım...", "Yapacak bir şey yok..."],
        "sulk": ["Hmph.", "Küsmedim. (Küstüm.)", "...", "İyi, görmezden gel."],
        "forgive": ["Tamam tamam... ♥", "Hmph... affettim.", "Ayy geri geldin!"],
        "sleepy": ["Çok uykum var...", "Beş dakika daha...", "*esneme*"],
        "wake": ["Bomba gibiyim!", "Şekerleme işe yaradı!"],
        "happy": ["En güzel gün!", "Hayat güzel ♥", "So gay! Çok mutluyum!"],
        "equip": ["Harika görünüyorum!", "Ooo, şık!", "Nasıl olmuş?", "Ooo, so gay!"],
        "unequip": ["Sade de güzel.", "Tamam!"],
        "frog": ["Vırak selam söylüyor!", "Kurbağa dostum!"],
        "dog": ["Lila! Aferin kızım!", "Gezmeye!"],
        "perch": ["Buradan her şey görünüyor!", "Manzara süper!", "Bak ne kadar yüksekteyim!"],
        "fall": ["Vay!", "İiik!"],
        "welcome": ["Döndüm! Özledim ♥", "Hoş geldin!"],
        "welcome_long": ["Çok uzun süre yoktun...", "Nerelerdeydin, özledim!"],
        "noted": ["Not aldım!", "Tamam!", "Hatırlatırım ♥"],
        "done": ["Bir iş daha bitti!", "Yaşasın!", "So gay, bitti!"],
        "selfie": ["Peynir!", "Mükemmel kare!", "So gay! Mükemmel kare!"],
        "sniff": ["Ohh... ne güzel!", "Mmm... ahh!", "Ohh! Çok taze!"],
        "sip": ["Ahh, çok güzel!", "Mmm, hâlâ sıcak!", "Mükemmel kahve!"],
        "lamp_on": ["Işık olsun!", "Klik! Ne rahat."],
        "lamp_off": ["Işıklar kapandı.", "Klik! Uyku ışığı."],
        "read": ["Hmm, ilginç...", "Bir sayfa daha..."],
        "mirror": ["Tadaa! Nasıl olmuş?", "Ayna ayna... harikayım!", "Hihi, çok tatlıyım."],
        "cupcake": ["Nam nam nam!", "Kek zamanı!", "Çok lezzetli!"],
        "teddy": ["Yumuşacık sarılma ♥", "Ayıcık en iyisi.", "Mmm, çok sarılmalık."],
        "cactus": ["Ay! Çok dikenli!", "Of of of!", "Kaktüs 1, ben 0."],
        "e_love": ["♥♥♥", "Seni seviyorum!", "Ayyy ♥"],
        "e_wow": ["Vay!", "Vaaay!", "So gay!", "Harika!"],
        "e_wink": ["Hihi ;)", "Göz kırptım!", "Psst... ♥"],
        "e_shy": ["Dur ya, kızarıyorum...", "Hihi... utandım.", "Ayy yapma ♥"],
        "e_laugh": ["Hahaha!", "Duramıyorum!", "Dur yaaa, çok komik!"],
        "e_super": ["Süper!", "So gay!", "Süper! So gay!", "Yaaay, süper!"],
        "e_cry": ["Buaaa...", "Hıh hıh...", "Çok üzücü..."],
        "e_angry": ["Grrr!", "Hmph!!", "Çok kızdım!"],
        "e_dizzy": ["Vay... dönüyor...", "Her şey dönüyor...", "Başım döndü!"],
        "e_shock": ["NE?!", "Olamaz!", "Cidden mi?!"],
        "calm_on": ["Şşş... sessiz olacağım.", "Sakin mod. Rahat."],
        "intro": ["Selam, ben Pocket Karolina ♥ Menü için bana sağ tıkla, ya da tıklayıp selam ver!"],
        "radio": ["Sesi aç!", "Bu şarkıya bayılıyorum!", "So gay, bu şarkı süper!"],
        "chair": ["Ahh, rahat.", "Oturmak güzel."],
        "held": ["Vıııı!", "Uçuyorum!", "Hihi, dikkat!"],
        "held_annoyed": ["Hey! İndir beni!", "Ben kedi değilim!", "Tamam, yeter artık..."],
        "panic": ["Vay!", "Yavaaaş!", "Çok hızlı!"],
        "remind": "Hatırlatma: {text}", "due": "Zamanı geldi: {text}!",
        "d_cuddle": "Sevgili günlük: bugün {n} sevgi aldım ♥",
        "d_selfie": "Sevgili günlük: bugün {n} selfie çektim. Harikayım!",
        "d_climb": "Sevgili günlük: bugün {n} pencereye tırmandım!",
        "d_dog": "Sevgili günlük: Lila bugün çok uslu bir kızdı.",
        "d_frog": "Sevgili günlük: Kurbağa bütün gün zıpladı.",
        "d_happy": "Sevgili günlük: bugün kendimi harika hissediyorum!",
        "d_meh": "Sevgili günlük: bugün biraz yalnızdım...",
        "d_plain": "Sevgili günlük: masaüstünde rahat bir gün.",
        "rps_hi": ["Taş kağıt makas mı? Hadi bakalım!", "Oynayalım!"],
        "rps_count": ["Taş!", "Kağıt!", "Makas!", "At!"],
        "rps_win": ["Yaşasın, ben kazandım!", "Ha! Çok kolay!", "Zafer dansı!", "So gay, kazandım!"],
        "rps_lose": ["Olamaaaz! Rövanş!", "Beni yendin...", "Acemi şansı!"],
        "rps_draw": ["Berabere! Tekrar!", "Büyük beyinler aynı düşünür!"],
        "ball_start": ["Top zamanı!", "At şunu!"],
        "ball_cheer": ["Getir Lila!", "Koş koş koş!"],
        "ball_back": ["Aferin kızım!!", "En iyi köpek!", "Bırak... aferin!", "So gay! Aferin kızım!"],
        "ball_end": ["Çok eğlenceliydi!", "Lila yoruldu!"],
        "msg_new": "Yeni mesaj ♥",
        "outfit_new": ["Ooo, yeni görünüm!", "Biri kombinimi seçti!", "Ooo, so gay!"],
    },
    "pl": {
        "poke": ["Hehe!", "Buu!", "Ojej ♥", "Jeszcze przytulasy?", "Ale słodko!"],
        "hug": ["♥♥♥", "Tak ciepło...", "Najlepszy uścisk!"],
        "kiss": ["Cmok!", "♥"],
        "neglect": ["Hej... pamiętasz o mnie?", "Przecież tu jestem.",
                    "Psst. Zwróć na mnie uwagę?", "Halo? Ktoś tu jest?"],
        "bored": ["*wzdech*", "Strasznie się nudzę...", "Nie ma nic do roboty..."],
        "sulk": ["Hmpf.", "Nie jestem zła. (Jestem zła.)", "...", "No dobra. Ignoruj mnie."],
        "forgive": ["Dobra, dobra... ♥", "Hmpf... no dobrze, wybaczam.", "Och, jesteś z powrotem!"],
        "sleepy": ["Jestem taka śpiąca...", "Jeszcze pięć minut...", "*ziew*"],
        "wake": ["Jak nowa!", "Drzemka pomogła!"],
        "happy": ["Najlepszy dzień!", "Życie jest piękne ♥", "So gay! Jestem taka szczęśliwa!"],
        "equip": ["Świetnie wyglądam!", "Ooo, elegancko!", "Jak wyglądam?", "Ooo, so gay!"],
        "unequip": ["Wracam do podstaw.", "Okej!"],
        "frog": ["Ribbit mówi cześć!", "Żabi przyjaciel!"],
        "dog": ["Lila! Dobra dziewczynka!", "Idziemy na spacer!"],
        "perch": ["Stąd widać wszystko!", "Ładny widok!", "Patrz, jestem wysoko!"],
        "fall": ["Ojej!", "Iii!"],
        "welcome": ["Wróciłam! Tęskniłam ♥", "Witaj z powrotem!"],
        "welcome_long": ["Tak długo cię nie było...", "Tyle czasu minęło! Tęskniłam!"],
        "noted": ["Zapisane!", "Mam to!", "Przypomnę ci ♥"],
        "done": ["Super, jedno mniej!", "Hurra, zrobione!", "So gay, zrobione!"],
        "selfie": ["Uśmiech!", "Idealne ujęcie!", "So gay! Idealne ujęcie!"],
        "sniff": ["Ooo... cudownie!", "Mmm... aaa!", "Ooo! Tak świeżo!"],
        "sip": ["Ahh, pyszne!", "Mmm, jeszcze ciepłe!", "Idealna filiżanka!"],
        "lamp_on": ["Niech będzie światło!", "Klik! Przytulnie."],
        "lamp_off": ["Światła zgaszone.", "Klik! Światło do spania."],
        "read": ["Hmm, ciekawe...", "Jeszcze tylko jedna strona..."],
        "mirror": ["Ta-da! Jak wyglądam?", "Lustereczko... pięknie!", "Hehe, słodko wyglądam."],
        "cupcake": ["Nam nam nam!", "Czas na babeczkę!", "Pyyyszne!"],
        "teddy": ["Miękki przytulas ♥", "Miś jest najlepszy.", "Mmm, taki milutki."],
        "cactus": ["Au! Kłuje!", "Auć auć auć!", "Kaktus 1, ja 0."],
        "e_love": ["♥♥♥", "Kocham cię!", "Awww ♥"],
        "e_wow": ["Wow!", "Łał!", "So gay!", "Super!"],
        "e_wink": ["Hehe ;)", "Mrugam!", "Psst... ♥"],
        "e_shy": ["Przestań, rumienię się...", "Hehe... wstydzę się.", "Oj nieee ♥"],
        "e_laugh": ["Hahaha!", "Nie mogę przestać!", "Przestań, takie śmieszne!"],
        "e_super": ["Super!", "So gay!", "Super! So gay!", "Jeeej, super!"],
        "e_cry": ["Buuu...", "Snif snif...", "Jakie smutne..."],
        "e_angry": ["Grrr!", "Hmph!!", "Jestem wściekła!"],
        "e_dizzy": ["Ojej... kręci się...", "Wszystko wiruje...", "Zawrót głowy!"],
        "e_shock": ["CO?!", "Niemożliwe!", "Serio?!"],
        "calm_on": ["Ciii... będę cicho.", "Tryb spokoju. Przytulnie."],
        "intro": ["Cześć, jestem Pocket Karolina ♥ Kliknij mnie prawym przyciskiem, by zobaczyć menu!"],
        "radio": ["Podgłośnij!", "Uwielbiam tę piosenkę!", "So gay, uwielbiam tę piosenkę!"],
        "chair": ["Ahh, wygodnie.", "Siedzenie jest miłe."],
        "held": ["Wiiii!", "Lecę!", "Hehe, ostrożnie!"],
        "held_annoyed": ["Hej! Postaw mnie!", "Nie jestem kotkiem!", "No dobra, już wystarczy..."],
        "panic": ["Ojej!", "Łoooo!", "Za szybko!"],
        "remind": "Przypomnienie: {text}", "due": "Czas na: {text}!",
        "d_cuddle": "Drogi pamiętniku: dziś {n} przytulasów ♥",
        "d_selfie": "Drogi pamiętniku: dziś {n} selfie. Wyglądam świetnie!",
        "d_climb": "Drogi pamiętniku: dziś wspięłam się na {n} okien!",
        "d_dog": "Drogi pamiętniku: Lila była dziś bardzo grzeczna.",
        "d_frog": "Drogi pamiętniku: Żabka skakała cały dzień.",
        "d_happy": "Drogi pamiętniku: czuję się dziś wspaniale!",
        "d_meh": "Drogi pamiętniku: dziś trochę samotnie...",
        "d_plain": "Drogi pamiętniku: przytulny dzień na pulpicie.",
        "rps_hi": ["Kamień, papier, nożyce? Zagrajmy!", "Gramy!"],
        "rps_count": ["Kamień!", "Papier!", "Nożyce!", "Hop!"],
        "rps_win": ["Hurra, wygrałam!", "Ha! Za łatwo!", "Taniec zwycięstwa!", "So gay, wygrałam!"],
        "rps_lose": ["Neeee! Rewanż!", "Pokonałeś mnie...", "Szczęście początkującego!"],
        "rps_draw": ["Remis! Jeszcze raz!", "Wielkie umysły myślą podobnie!"],
        "ball_start": ["Czas na piłkę!", "Rzuć ją!"],
        "ball_cheer": ["Aport, Lila!", "Biegnij, biegnij!"],
        "ball_back": ["Dobra dziewczynka!!", "Najlepszy pies!", "Puść... brawo!", "So gay! Dobra dziewczynka!"],
        "ball_end": ["Ale zabawa!", "Lila jest zmęczona!"],
        "msg_new": "Nowa wiadomość ♥",
        "outfit_new": ["Ooo, nowy look!", "Ktoś wybrał mój strój!", "Ooo, so gay!"],
    },
}

# Eksik anahtar olursa İngilizceye düş (yeni dil eklemek kolay olsun)
LINES["en"].update({
    "treat_throw": ["Lila! Catch!", "Who wants a treat?", "Go get it, Lila!"],
    "treat_done": ["Good girl, Lila ♥", "All gone? Wow.", "She loved it!", "So gay, she ate it all!"],
    "treat_busy": ["Let her finish first!", "She's still chewing ♥"],
    "surprise_new": ["Ooh, what's that?", "Something appeared!", "A little surprise ♥"],
    "found": ["Found it!", "Mine!", "Ooh, pretty!", "Yay, a surprise!"],
    "poke_phone": ["Someone's thinking of you ♥", "Psst! A poke from the phone ♥", "Boop! You got poked ♥"],
    "poke_log": ["*poke* ♥"],
    "hide_tip": ["I'm hiding here. Click me to come back ♥"],
    "unhide": ["I'm back! ♥", "Did you win?", "Missed me?"],
    "chat_hint": ["(Right-click me > Chat to reply)"],
    "season_newyear": ["Happy New Year! ♥", "New year, new me!"],
    "season_valentine": ["Happy Valentine's ♥", "Be my valentine? ♥"],
    "season_summer": ["Summer time!", "Ice cream weather!"],
    "season_halloween": ["Boo! Happy Halloween!", "Trick or treat!"],
    "season_christmas": ["Merry Christmas! ♥", "Ho ho ho!", "It's so gay and festive!"]})
LINES["tr"].update({
    "treat_throw": ["Lila! Yakala!", "Kim kuru et ister?", "Hadi al, Lila!"],
    "treat_done": ["Aferin Lila ♥", "Hepsi bitti mi? Vay.", "Bayıldı!", "So gay, hepsini yedi!"],
    "treat_busy": ["Önce bitirsin!", "Hâlâ kemiriyor ♥"],
    "surprise_new": ["Ooo, bu ne?", "Bir şey belirdi!", "Küçük bir sürpriz ♥"],
    "found": ["Buldum!", "Benim!", "Ooo, ne güzel!", "Yaşasın, sürpriz!"],
    "poke_phone": ["Biri seni düşünüyor ♥", "Psst! Telefondan dürtüldün ♥", "Bip! Dürtüldün ♥"],
    "poke_log": ["*dürt* ♥"],
    "hide_tip": ["Burada saklanıyorum. Geri gelmem için tıkla ♥"],
    "unhide": ["Geldim! ♥", "Kazandın mı?", "Özledin mi?"],
    "chat_hint": ["(Cevap için bana sağ tıkla > Sohbet)"],
    "season_newyear": ["Mutlu yıllar! ♥", "Yeni yıl, yeni ben!"],
    "season_valentine": ["Sevgililer günün kutlu olsun ♥", "Sevgilim olur musun? ♥"],
    "season_summer": ["Yaz geldi!", "Dondurma havası!"],
    "season_halloween": ["Böö! Mutlu Cadılar Bayramı!", "Şeker mi şaka mı!"],
    "season_christmas": ["Mutlu Noeller! ♥", "Ho ho ho!", "Çok so gay ve bayramlık!"]})
LINES["pl"].update({
    "treat_throw": ["Lila! Łap!", "Kto chce gryzaka?", "Leć, Lila!"],
    "treat_done": ["Dobra dziewczynka, Lila ♥", "Wszystko zjedzone? Wow.", "Uwielbia to!",
                   "So gay, zjadła wszystko!"],
    "treat_busy": ["Niech najpierw skończy!", "Jeszcze gryzie ♥"],
    "surprise_new": ["Ooo, co to?", "Coś się pojawiło!", "Mała niespodzianka ♥"],
    "found": ["Mam!", "Moje!", "Ooo, śliczne!", "Hura, niespodzianka!"],
    "poke_phone": ["Ktoś o tobie myśli ♥", "Psst! Szturchnięcie z telefonu ♥", "Pik! Szturch ♥"],
    "poke_log": ["*szturch* ♥"],
    "hide_tip": ["Chowam się tutaj. Kliknij, żebym wróciła ♥"],
    "unhide": ["Jestem! ♥", "Wygrałeś?", "Tęskniłeś?"],
    "chat_hint": ["(Kliknij mnie prawym > Czat, by odpisać)"],
    "season_newyear": ["Szczęśliwego Nowego Roku! ♥", "Nowy rok, nowa ja!"],
    "season_valentine": ["Szczęśliwych Walentynek ♥", "Będziesz moją walentynką? ♥"],
    "season_summer": ["Lato!", "Pogoda na lody!"],
    "season_halloween": ["Buu! Wesołego Halloween!", "Cukierek albo psikus!"],
    "season_christmas": ["Wesołych Świąt! ♥", "Ho ho ho!", "Tak so gay i świątecznie!"]})
LINES["en"].update({
    "chaos_start": ["CHAOS TIME!", "Hehehe... chaos!", "So gay! CHAOS!", "Nobody can stop me!"],
    "chaos_oops": ["Oops! Downloads!", "Hehe, what's this folder?", "Oopsie ♥", "Did I do that?"],
    "chaos_end": ["*pant pant*", "Okay... I'm done.", "That was so gay! ♥", "Worth it."],
    "chaos_stop": ["Okay okay, I'll stop!", "Fine... calm now.", "Hehe, sorry!"],
    "chaos_fixed": ["Fixed my outfit ♥", "Much better.", "Back to normal!"]})
LINES["tr"].update({
    "chaos_start": ["KAOS ZAMANI!", "Hehehe... kaos!", "So gay! KAOS!", "Kimse beni durduramaz!"],
    "chaos_oops": ["Ups! İndirilenler!", "Hehe, bu klasör ne?", "Upsi ♥", "Bunu ben mi yaptım?"],
    "chaos_end": ["*hah hah*", "Tamam... bitti.", "So gay'di! ♥", "Değdi."],
    "chaos_stop": ["Tamam tamam, duruyorum!", "Peki... sakinim.", "Hehe, pardon!"],
    "chaos_fixed": ["Kıyafetimi düzelttim ♥", "Çok daha iyi.", "Normale döndüm!"]})
LINES["pl"].update({
    "chaos_start": ["CZAS NA CHAOS!", "Hehehe... chaos!", "So gay! CHAOS!", "Nikt mnie nie zatrzyma!"],
    "chaos_oops": ["Ups! Pobrane!", "Hehe, co to za folder?", "Upsik ♥", "To ja zrobiłam?"],
    "chaos_end": ["*dysz dysz*", "Dobra... koniec.", "To było so gay! ♥", "Warto było."],
    "chaos_stop": ["Dobra dobra, przestaję!", "No dobrze... spokój.", "Hehe, sorki!"],
    "chaos_fixed": ["Poprawiłam strój ♥", "Dużo lepiej.", "Wracam do normy!"]})
LINES["en"].update({"remote_on": "Link copied! Same Wi-Fi:", "remote_off": "Phone link is off.",
                    "remote_fail": "Could not start the phone link."})
LINES["tr"].update({"remote_on": "Link kopyalandı! Aynı Wi-Fi:", "remote_off": "Telefon bağlantısı kapalı.",
                    "remote_fail": "Telefon bağlantısı başlatılamadı."})
LINES["pl"].update({"remote_on": "Link skopiowany! To samo Wi-Fi:", "remote_off": "Połączenie z telefonem wyłączone.",
                    "remote_fail": "Nie można uruchomić połączenia z telefonem."})
for _lg in list(LINES):
    if _lg != "en":
        LINES[_lg] = {**LINES["en"], **LINES[_lg]}


def pick_line(lang, key):
    v = LINES.get(lang, LINES["en"]).get(key) or LINES["en"].get(key)
    return random.choice(v) if isinstance(v, list) else v


# ===========================================================================
#  KAOS MODU: yalnızca İndirilenler klasörünü açar, başka hiçbir şeye dokunmaz
# ===========================================================================
CHAOS_TICKS = (900, 1350)      # 30-45 sn
CHAOS_FOLDERS = (2, 3)         # kaç kez İndirilenler açılır


def downloads_dir():
    """Kullanıcının İndirilenler klasörü (Windows'ta taşınmış olsa bile), yoksa None."""
    if IS_WIN:
        try:
            import ctypes
            from ctypes import wintypes

            class GUID(ctypes.Structure):
                _fields_ = [("a", wintypes.DWORD), ("b", wintypes.WORD), ("c", wintypes.WORD),
                            ("d", ctypes.c_ubyte * 8)]
            g = GUID(0x374DE290, 0x123F, 0x4565,
                     (ctypes.c_ubyte * 8)(0x91, 0x64, 0x39, 0xC4, 0x92, 0x5E, 0x46, 0x7B))
            out = ctypes.c_wchar_p()
            if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(g), 0, None,
                                                          ctypes.byref(out)) == 0:
                path = out.value
                ctypes.windll.ole32.CoTaskMemFree(out)
                if path and os.path.isdir(path):
                    return path
        except Exception:
            pass
    p = os.path.join(os.path.expanduser("~"), "Downloads")
    return p if os.path.isdir(p) else None


def open_folder(path):
    """Klasörü yeni bir dosya gezgini penceresinde açar; beklemez, hata yutar."""
    try:
        if IS_WIN:
            subprocess.Popen(["explorer", os.path.normpath(path)])
        elif IS_MAC:
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path], stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


# ===========================================================================
#  KALICI KAYIT  (save.json)
# ===========================================================================
SAVE_VERSION = 9
DEFAULT_PREFS = {"lang": "en", "chatter": True, "calm": False, "climb": True, "flash": True,
                 "autohide": True, "chat_hint": True,
                 "remind_every": 240, "corner": "left",
                 "remote": False, "lan": True, "port": 8765, "token": ""}


def default_save_path():
    base = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
    p = os.path.join(base, "save.json")
    try:
        if os.path.exists(p):
            open(p, "r").close()
        else:
            open(p, "w").close()
            os.remove(p)
        return p
    except OSError:                       # yazılamıyorsa kullanıcı klasörüne geç
        alt = os.path.join(os.path.expanduser("~"), ".pixelpet")
        os.makedirs(alt, exist_ok=True)
        return os.path.join(alt, "save.json")


def load_save(path):
    """Bozuk / eksik dosyaya dayanıklı yükleme. Her zaman geçerli bir dict döner."""
    raw = {}
    for src in (path, path + ".bak"):                 # ana dosya bozuksa yedekten dön
        try:
            with open(src, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if not isinstance(raw, dict):
                raise ValueError
            break
        except (OSError, ValueError):
            raw = {}

    def num(v, d, lo=0.0, hi=100.0):
        try:
            return max(lo, min(hi, float(v)))
        except (TypeError, ValueError):
            return d

    st = raw.get("stats") if isinstance(raw.get("stats"), dict) else {}
    out = {
        "saved_at": num(raw.get("saved_at"), 0.0, 0.0, 4e9),
        "stats": {"mood": num(st.get("mood"), 70.0), "energy": num(st.get("energy"), 80.0),
                  "affection": num(st.get("affection"), 65.0)},
    }
    ct = raw.get("counters") if isinstance(raw.get("counters"), dict) else {}
    out["counters"] = {"date": str(ct.get("date", "")),
                       **{k: int(num(ct.get(k), 0, 0, 10 ** 6))
                          for k in ("cuddles", "selfies", "climbs", "throws")}}
    wr = raw.get("worn") if isinstance(raw.get("worn"), dict) else {}
    out["worn"] = {s: (wr.get(s) if SLOT_OF.get(wr.get(s)) == s else None) for s in SLOTS}
    cp = raw.get("companions") if isinstance(raw.get("companions"), dict) else {}
    out["companions"] = {"frog": bool(cp.get("frog")), "dog": bool(cp.get("dog"))}
    out["props"] = [{"kind": p["kind"], "x": int(num(p.get("x"), 200, -2000, 20000)),
                     "on": bool(p.get("on", True))}
                    for p in raw.get("props", []) if isinstance(p, dict) and p.get("kind") in PROP_W][:12]
    notes = []
    for n in raw.get("notes", []):
        if isinstance(n, dict) and isinstance(n.get("text"), str) and n["text"].strip():
            due = n.get("due")
            ok = isinstance(due, str) and re.fullmatch(r"\d{2}:\d{2}", due)
            notes.append({"text": n["text"][:80], "done": bool(n.get("done")),
                          "due": due if ok else None, "alerted": str(n.get("alerted") or "")})
    out["notes"] = notes[:60]
    pf = raw.get("prefs") if isinstance(raw.get("prefs"), dict) else {}
    prefs = dict(DEFAULT_PREFS)
    for k, d in DEFAULT_PREFS.items():
        v = pf.get(k, d)
        prefs[k] = v if type(v) is type(d) else d
    if prefs["lang"] not in LINES:
        prefs["lang"] = "en"
    if prefs["corner"] not in ("left", "right"):
        prefs["corner"] = "left"
    prefs["remind_every"] = int(max(30, min(3600, prefs["remind_every"])))
    prefs["port"] = int(max(1024, min(65535, prefs["port"])))
    prefs["token"] = re.sub(r"[^A-Za-z0-9_-]", "", prefs["token"])[:32]
    if len(prefs["token"]) < 8:
        prefs["token"] = ""
    gm = raw.get("games") if isinstance(raw.get("games"), dict) else {}
    rp = gm.get("rps") if isinstance(gm.get("rps"), dict) else {}
    bl = gm.get("ball") if isinstance(gm.get("ball"), dict) else {}
    ph = gm.get("phone") if isinstance(gm.get("phone"), dict) else {}
    out["games"] = {"rps": {k: int(num(rp.get(k), 0, 0, 10 ** 6)) for k in ("you", "pet", "draw")},
                    "ball": {"fetches": int(num(bl.get("fetches"), 0, 0, 10 ** 6))},
                    "phone": {g: {r: int(num((ph.get(g) if isinstance(ph.get(g), dict) else {}).get(r),
                                              0, 0, 10 ** 6)) for r in ("win", "lose", "draw")}
                              for g in GAME_NAMES}}
    out["inbox"] = [{"text": clean_text(m["text"], MAX_MSG), "ts": num(m.get("ts"), 0.0, 0.0, 4e9),
                     "from": m.get("from") if m.get("from") in ("pet", "pc") else "phone"}
                    for m in raw.get("inbox", []) if isinstance(m, dict) and isinstance(m.get("text"), str)
                    and clean_text(m["text"], MAX_MSG)][-60:]
    pres = []
    for o in raw.get("outfits", []) if isinstance(raw.get("outfits"), list) else []:
        if isinstance(o, dict) and isinstance(o.get("worn"), dict):
            nm = clean_text(o.get("name"), 16)
            if nm:
                pres.append({"name": nm, "worn": {sl: (o["worn"].get(sl) if SLOT_OF.get(o["worn"].get(sl)) == sl
                                                       else None) for sl in SLOTS}})
    out["outfits"] = pres[:MAX_PRESETS]
    fd = raw.get("found") if isinstance(raw.get("found"), dict) else {}
    out["found"] = {k: int(num(fd.get(k), 0, 0, 10 ** 6)) for k in SURPRISES}

    def look(d):
        d = d if isinstance(d, dict) else {}
        return {sl: (d.get(sl) if SLOT_OF.get(d.get(sl)) == sl else None) for sl in SLOTS if sl in d}
    se = raw.get("season") if isinstance(raw.get("season"), dict) else {}
    out["season"] = {"key": str(se.get("key", ""))[:32]}
    if isinstance(se.get("prev"), dict) and isinstance(se.get("look"), dict):
        out["season"].update(prev=look(se["prev"]), look=look(se["look"]))
    out["prefs"] = prefs
    return out


def write_save(path, data):
    """Atomik yazma (önce .tmp, sonra os.replace)."""
    tmp = path + ".tmp"
    try:
        try:                                          # eski sağlam kaydı en fazla 10 dkda bir yedekle
            bak = path + ".bak"
            if os.path.exists(path) and os.path.getsize(path) > 20 and (
                    not os.path.exists(bak) or time.time() - os.path.getmtime(bak) > 600):
                shutil.copyfile(path, bak)
        except OSError:
            pass
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        os.replace(tmp, path)
        return True
    except OSError:
        return False


# ===========================================================================
#  UZAKTAN KONTROL (telefon)
#  Katmanlar:  RemoteCore (doğrulama + kuyruk, taşımadan bağımsız)
#              HttpTransport (LAN üzerinde küçük web sunucusu + telefon sayfası)
#  İleride internet üzerinden (relay / WebSocket) bağlanmak için yeni bir taşıma sınıfı
#  yazıp aynı RemoteCore.submit()/authorize()/snapshot arayüzünü kullanması yeterli.
#  Güvenlik: varsayılan KAPALI; belirteç (token) zorunlu; sabit zamanlı karşılaştırma;
#  hatalı denemede IP kilidi; hız sınırı; gövde ve mesaj boyutu sınırı; komutlar beyaz liste.
#  Tk'ye sadece ana iş parçacığı dokunur (komutlar kuyruktan orada çalıştırılır).
# ===========================================================================
MAX_PRESETS = 12
_AV_CACHE = {}


def _png(w, h, rows):
    """Minimal PNG (RGBA) yazıcı: sadece standart kütüphane."""
    raw = b"".join(b"\x00" + r for r in rows)

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)) +
            chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))


def avatar_png(worn, scale=6, pose="idle"):
    """Karakterin (kıyafetleriyle) şeffaf arka planlı PNG'si; telefon sayfasında önizleme için."""
    eq = tuple(worn.get(sl) if SLOT_OF.get(worn.get(sl)) == sl else None for sl in SLOTS)
    scale = max(1, min(8, int(scale)))
    key = (eq, scale, pose)
    data = _AV_CACHE.get(key)
    if data is None:
        if pose == "happy":
            k = K(eyes="happy", mouth="grin", al="u", ar="u", hat=eq[0], glasses=eq[1],
                  outfit=eq[2], neck=eq[3], held=eq[4])
        else:
            k = K(hat=eq[0], glasses=eq[1], outfit=eq[2], neck=eq[3], held=eq[4])
        g = compose(k)
        rgba = {c: bytes(int(PAL[c][i:i + 2], 16) for i in (1, 3, 5)) + b"\xff" for c in PAL}
        clear = b"\x00\x00\x00\x00"
        rows = []
        for row in g:
            line = b"".join(rgba.get(ch, clear) * scale for ch in row)
            rows.extend([line] * scale)
        data = _png(len(g[0]) * scale, len(g) * scale, rows)
        if len(_AV_CACHE) > 400:
            _AV_CACHE.clear()
        _AV_CACHE[key] = data
    return data


REMOTE_ACTIONS = ("poke", "dance", "wave", "kiss", "hug", "jump", "spin", "selfie", "sleep",
                  "treat", "chaos") + tuple(EMOTES)
MAX_BODY, MAX_MSG = 2048, 140
RPS_NAMES = ('rock', 'paper', 'scissors')
GAME_NAMES = ('rps', 'ttt', 'mem')


def clean_text(s, limit):
    if not isinstance(s, str):
        return ""
    s = "".join(ch for ch in s if ch >= " " and ch != "\x7f")       # kontrol karakterlerini at
    return " ".join(s.split())[:limit]


def lan_ip():
    """Yerel ağ IP'si (paket göndermeden: UDP connect hilesi)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


class RemoteCore:
    def __init__(self, token):
        self.token = token
        self.q = queue.Queue(maxsize=50)
        self.snapshot = {"ok": True}
        self.lock = threading.Lock()
        self.hits = collections.deque()
        self.hits_img = collections.deque()
        self.fails = {}

    def authorize(self, tok, ip="?"):
        now = time.time()
        with self.lock:
            rec = self.fails.get(ip)
            if rec and rec[0] >= 8 and now - rec[1] < 60:
                return "locked"
            ok = isinstance(tok, str) and hmac.compare_digest(
                tok.encode("utf-8", "ignore"), self.token.encode("utf-8"))
            if ok:
                self.fails.pop(ip, None)
                return "ok"
            if not rec or now - rec[1] >= 60:
                rec = self.fails[ip] = [0, now]
            rec[0] += 1
            if len(self.fails) > 200:
                self.fails.clear()
            return "bad"

    def rate_ok(self, bucket="api"):
        now = time.time()
        limit = 240 if bucket == "img" else 40
        with self.lock:
            dq = self.hits_img if bucket == "img" else self.hits
            while dq and now - dq[0] > 10:
                dq.popleft()
            if len(dq) >= limit:
                return False
            dq.append(now)
            return True

    def submit(self, kind, data):
        """-> (http_kodu, sözlük). Doğrulama burada; asıl iş Tk iş parçacığında yapılır."""
        if kind == "message":
            text = clean_text(data.get("text"), MAX_MSG)
            if not text:
                return 400, {"error": "empty"}
            cmd = ("message", text)
        elif kind == "note":
            text = clean_text(data.get("text"), 80)
            if not text:
                return 400, {"error": "empty"}
            cmd = ("note", text)
        elif kind == "outfit":
            slot, iid = data.get("slot"), data.get("id") or ""
            if slot not in SLOTS or not isinstance(iid, str) or (iid and SLOT_OF.get(iid) != slot):
                return 400, {"error": "bad item"}
            cmd = ("outfit", slot, iid)
        elif kind == "outfit_save":
            name = clean_text(data.get("name"), 16)
            if not name:
                return 400, {"error": "empty"}
            cmd = ("outfit_save", name)
        elif kind in ("outfit_apply", "outfit_delete"):
            i = data.get("index")
            if type(i) is not int or not 0 <= i < MAX_PRESETS:
                return 400, {"error": "bad index"}
            cmd = (kind, i)
        elif kind == "game":
            if data.get("name") not in GAME_NAMES or data.get("result") not in ("win", "lose", "draw"):
                return 400, {"error": "bad game"}
            cmd = ("game", data["name"], data["result"])
        elif kind == "rps_move":
            if data.get("move") not in RPS_NAMES:
                return 400, {"error": "bad move"}
            cmd = ("rps_move", data["move"])
        elif kind == "action":
            if data.get("name") not in REMOTE_ACTIONS:
                return 400, {"error": "bad action"}
            cmd = ("action", data["name"])
        else:
            return 404, {"error": "unknown"}
        try:
            self.q.put_nowait(cmd)
        except queue.Full:
            return 429, {"error": "busy"}
        return 200, {"ok": True}

    def drain(self, pet, limit=10):
        for _ in range(limit):
            try:
                cmd = self.q.get_nowait()
            except queue.Empty:
                break
            pet.remote_command(cmd)

    def publish(self, snap):
        self.snapshot = snap                               # referans değişimi atomik


class HttpTransport:
    name = "http"

    def __init__(self, core, host, port, page):
        self.core, self.host, self.port = core, host, port
        self.page = page.encode("utf-8")
        self.httpd = self.thread = None

    def start(self):
        core, page = self.core, self.page

        class H(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.0"
            timeout = 5

            def log_message(self, *a):
                pass

            def _send(self, code, body, ctype="application/json; charset=utf-8", cache="no-store"):
                data = body if isinstance(body, bytes) else json.dumps(
                    body, ensure_ascii=False).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", cache)
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Referrer-Policy", "no-referrer")
                self.end_headers()
                self.wfile.write(data)

            def _gate(self, bucket="api"):
                tok = self.headers.get("X-Token")
                if tok is None:
                    tok = (parse_qs(urlparse(self.path).query).get("k") or [None])[0]
                st = core.authorize(tok, self.client_address[0])
                if st == "ok":
                    if core.rate_ok(bucket):
                        return True
                    self._send(429, {"error": "slow down"})
                elif st == "locked":
                    self._send(429, {"error": "locked"})
                else:
                    self._send(403, {"error": "forbidden"})
                return False

            def do_GET(self):
                u = urlparse(self.path)
                path = u.path
                if path == "/api/avatar.png":
                    if not self._gate("img"):
                        return
                    q = {k: v[0] for k, v in parse_qs(u.query).items() if v}
                    try:
                        scale = int(q.get("scale", 6))
                    except ValueError:
                        scale = 6
                    worn = {sl: q.get(sl) for sl in SLOTS}
                    pose = "happy" if q.get("pose") == "happy" else "idle"
                    return self._send(200, avatar_png(worn, scale, pose), "image/png",
                                      "private, max-age=3600")
                if not self._gate():
                    return
                if path == "/":
                    self._send(200, page, "text/html; charset=utf-8")
                elif path == "/api/state":
                    self._send(200, core.snapshot)
                else:
                    self._send(404, {"error": "not found"})

            def do_POST(self):
                path = urlparse(self.path).path
                if not self._gate():
                    return
                try:
                    n = int(self.headers.get("Content-Length") or 0)
                except ValueError:
                    n = -1
                if n < 0 or n > MAX_BODY:
                    return self._send(413, {"error": "too large"})
                try:
                    data = json.loads(self.rfile.read(n) or b"{}")
                    if not isinstance(data, dict):
                        raise ValueError
                except ValueError:
                    return self._send(400, {"error": "bad json"})
                kind = path[5:] if path.startswith("/api/") else ""
                code, out = core.submit(kind, data)
                self._send(code, out)

        self.httpd = ThreadingHTTPServer((self.host, self.port), H)
        self.httpd.daemon_threads = True
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def stop(self):
        if self.httpd:
            try:
                self.httpd.shutdown()
                self.httpd.server_close()
            except OSError:
                pass
            self.httpd = None


PHONE_PAGE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#ffd9e6"><meta name="apple-mobile-web-app-capable" content="yes">
<title>Pocket Karolina</title><style>
:root{--bg:#fff4ea;--card:#fffaf5;--ink:#3a1f1c;--acc:#c2561c;--pink:#ff5c8a;--soft:#ffe3d3;--on:#c8f3d2;--hi:#ffb3c7;--me:#ffc2d4;--wall:#ffe9f0;--floor:#e8c9b0;--dot:#ffd0de}
@media(prefers-color-scheme:dark){:root{--bg:#21171c;--card:#2d2128;--ink:#ffe9dc;--acc:#ff9a6b;--pink:#ff7aa2;--soft:#3d2c34;--on:#2f5f42;--hi:#7a3350;--me:#6b3049;--wall:#33232c;--floor:#4a3540;--dot:#4a2d3a}}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}html,body{height:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.35 ui-monospace,"SF Mono",Menlo,Consolas,monospace;display:flex;flex-direction:column;overflow:hidden}
header{flex:none;padding:calc(env(safe-area-inset-top) + 10px) 14px 8px;background:linear-gradient(var(--hi),var(--bg));text-align:center}
h1{font-size:15px;margin:0 0 6px;color:var(--acc);letter-spacing:.5px}
#stage{position:relative;margin:0 auto;width:min(100%,360px);border:3px solid var(--ink);border-radius:12px;box-shadow:3px 3px 0 var(--ink);overflow:hidden;
background:radial-gradient(var(--dot) 1.5px,transparent 1.6px) 0 0/14px 14px,var(--wall);transition:height .25s;display:flex;align-items:flex-end;justify-content:center}
body.tall #stage{height:230px}body.small #stage{height:96px}
#stage:after{content:"";position:absolute;left:0;right:0;bottom:0;height:22px;background:var(--floor);border-top:3px solid var(--ink)}
#av{position:relative;z-index:1;margin-bottom:12px;image-rendering:pixelated;height:190px;animation:bob 1.2s steps(2) infinite}
body.small #av{height:78px;margin-bottom:6px}
@keyframes bob{50%{transform:translateY(-3px)}}
.hrt{position:absolute;z-index:2;font-size:14px;color:var(--pink);opacity:0;animation:fl 4s ease-in infinite}
.hrt:nth-of-type(1){left:14%;animation-delay:0s}.hrt:nth-of-type(2){left:80%;animation-delay:1.6s}.hrt:nth-of-type(3){left:28%;animation-delay:2.8s}
@keyframes fl{0%{bottom:20px;opacity:0}20%{opacity:.9}100%{bottom:150px;opacity:0}}
#st{font-size:11px;margin-top:6px;min-height:15px;opacity:.8}
main{flex:1;min-height:0;position:relative}
section{position:absolute;inset:0;overflow-y:auto;padding:10px 14px 14px;display:none}section.on{display:block}
#p0.on{display:flex;flex-direction:column;padding-bottom:0}
nav{flex:none;display:flex;gap:6px;padding:8px 10px calc(env(safe-area-inset-bottom) + 8px);background:var(--card);border-top:3px solid var(--ink)}
nav button{flex:1;display:flex;flex-direction:column;align-items:center;gap:2px;padding:6px 2px;font-size:11px;box-shadow:none}
nav button b{font-size:18px;line-height:1}nav button.on{background:var(--pink);color:#fff}
button{font:inherit;color:var(--ink);background:var(--soft);border:3px solid var(--ink);border-radius:8px;padding:9px 8px;cursor:pointer;box-shadow:2px 2px 0 var(--ink);transition:transform .05s}
button:active{transform:translate(2px,2px);box-shadow:0 0 0 var(--ink)}button.on{background:var(--on)}button.pri{background:var(--pink);color:#fff}
h2{font-size:12px;margin:14px 0 6px;color:var(--acc);text-transform:uppercase;letter-spacing:1px}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}
.tile{padding:4px 2px 6px;display:flex;flex-direction:column;align-items:center;gap:2px;font-size:11px}
.tile img{height:62px;image-rendering:pixelated}.tile.on{background:var(--on)}
.pre{display:flex;gap:8px;overflow-x:auto;padding:2px 2px 8px}.pre .card{flex:none;width:92px;padding:4px;text-align:center;font-size:11px;position:relative}
.card{background:var(--card);border:3px solid var(--ink);border-radius:8px;box-shadow:2px 2px 0 var(--ink)}
.pre img{height:70px;image-rendering:pixelated}.pre .x{position:absolute;top:-8px;right:-6px;padding:0 6px;font-size:12px;border-radius:50%;line-height:20px;height:22px}
.row{display:flex;gap:8px;margin-top:8px}.row>*{flex:1}input,textarea{width:100%;font:inherit;color:var(--ink);background:var(--card);border:3px solid var(--ink);border-radius:8px;padding:10px}
#log{flex:1;overflow-y:auto;display:flex;flex-direction:column;gap:8px;padding:4px 0 10px}
.b{max-width:82%;padding:8px 11px;border:3px solid var(--ink);border-radius:12px;word-wrap:break-word;overflow-wrap:anywhere;box-shadow:2px 2px 0 var(--ink)}
.b.pc{align-self:flex-start;background:#dcebff;border-bottom-left-radius:3px}.b.pc i{display:block;font-style:normal;font-size:10px;opacity:.6;margin-bottom:2px}
.b.me{align-self:flex-end;background:var(--me);border-bottom-right-radius:3px}.b.pet{align-self:flex-start;background:var(--card);border-bottom-left-radius:3px}
.b small{display:block;font-size:10px;opacity:.55;margin-top:2px}.empty{margin:auto;text-align:center;opacity:.6;font-size:13px}
#comp{flex:none;padding:8px 0 10px;border-top:3px dashed var(--ink);background:var(--bg)}
#comp textarea{height:46px;max-height:120px;resize:none}.stk{display:flex;gap:6px;margin-bottom:8px;overflow-x:auto}.stk button{flex:none;padding:4px 10px;font-size:17px}
.seg{display:flex;gap:6px;margin-bottom:8px}.seg button{flex:1;padding:5px}
.acts{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}.acts button{padding:16px 6px;font-size:14px}.acts b{display:block;font-size:26px}
.gcard{display:flex;gap:12px;align-items:center;padding:12px;margin-bottom:10px;cursor:pointer;text-align:left;width:100%}.gcard b{font-size:30px}.gcard small{display:block;opacity:.7}
.score{font-size:12px;opacity:.8;margin:2px 0 8px;text-align:center}
.banner{background:var(--hi);border:3px solid var(--ink);border-radius:8px;padding:8px;text-align:center;margin-bottom:10px;font-size:13px}
.rps{display:flex;gap:8px}.rps button{flex:1;font-size:34px;padding:14px 0}
.vs{display:flex;justify-content:space-around;align-items:center;font-size:46px;margin:14px 0 4px;min-height:64px}.vs small{display:block;font-size:11px;text-align:center;opacity:.7}
.res{text-align:center;font-size:17px;font-weight:bold;min-height:26px;color:var(--acc)}
.ttt{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;max-width:300px;margin:8px auto}.ttt button{aspect-ratio:1;font-size:36px;padding:0}
.mem{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;max-width:340px;margin:8px auto}.mem button{aspect-ratio:1;font-size:28px;padding:0}.mem button.up{background:var(--card)}.mem button.ok{background:var(--on)}
.back{margin-bottom:8px;padding:5px 12px}
#toast{position:fixed;left:50%;bottom:92px;transform:translateX(-50%);background:var(--ink);color:var(--bg);padding:8px 14px;border-radius:8px;opacity:0;transition:opacity .2s;pointer-events:none;z-index:9}
</style></head><body class="small">
<header><h1>♥ POCKET KAROLINA ♥</h1>
<div id="stage"><span class="hrt">♥</span><span class="hrt">♥</span><span class="hrt">♥</span><img id="av" alt=""></div><div id="st"></div></header>
<main>
<section id="p0" class="on"><div id="log"></div>
<div id="comp"><div class="stk" id="stk"></div><div class="seg"><button id="m0" class="on"></button><button id="m1"></button></div>
<div class="row" style="margin-top:0"><textarea id="msg" maxlength="140" rows="1"></textarea><button id="send" class="pri" style="flex:0 0 76px"></button></div></div></section>
<section id="p1"><h2 id="sh"></h2><div class="pre" id="pre"></div>
<div class="row"><input id="pname" maxlength="16"><button id="psave" class="pri" style="flex:0 0 96px"></button></div><div id="slots"></div></section>
<section id="p2"><div id="gmenu"></div><div id="gview" style="display:none"></div></section>
<section id="p3"><h2 id="h_act"></h2><div class="acts" id="acts"></div><h2 id="h_emo"></h2><div class="acts" id="emos"></div></section>
</main>
<nav id="nav"></nav><div id="toast"></div>
<script>
var Q=new URLSearchParams(location.search),K=Q.get('k')||'',S=null,TAB=0,SL=['hat','glasses','outfit','neck','held'],G=null,pickedSeq=-1,mode='msg',sig='',avsrc='';
var EM=['love','wow','wink','shy','laugh','super','cry','angry','dizzy','shock'];
var EJ={poke:'👉',treat:'🦴',chaos:'🌪️',dance:'💃',wave:'👋',kiss:'😘',hug:'🤗',jump:'🦘',spin:'🌀',selfie:'🤳',sleep:'😴',love:'😍',wow:'🤩',wink:'😉',shy:'🥰',laugh:'😂',super:'🌈',cry:'😭',angry:'😠',dizzy:'😵',shock:'😱'};
var AL={en:{poke:'Poke ♥',treat:'Lila treat',chaos:'Chaos!',dance:'Dance',wave:'Wave',kiss:'Kiss',hug:'Hug',jump:'Jump',spin:'Spin',selfie:'Selfie',sleep:'Sleep',love:'Love',wow:'Wow',wink:'Wink',shy:'Shy',laugh:'Laugh',super:'Super!',cry:'Cry',angry:'Grr',dizzy:'Dizzy',shock:'Shock',Actions:'Actions',Emotes:'Emotes'},
tr:{poke:'Dürt ♥',treat:'Lila’ya et',chaos:'Kaos!',dance:'Dans',wave:'El salla',kiss:'Öp',hug:'Sarıl',jump:'Zıpla',spin:'Dön',selfie:'Selfie',sleep:'Uyu',love:'Aşk',wow:'Vay',wink:'Göz kır',shy:'Utan',laugh:'Gül',super:'Süper!',cry:'Ağla',angry:'Grr',dizzy:'Sersem',shock:'Şok',Actions:'Hareketler',Emotes:'İfadeler'},
pl:{poke:'Szturchnij ♥',treat:'Gryzak Lili',chaos:'Chaos!',dance:'Taniec',wave:'Pomachaj',kiss:'Buziak',hug:'Przytul',jump:'Skok',spin:'Obrót',selfie:'Selfie',sleep:'Spać',love:'Miłość',wow:'Wow',wink:'Mrugnij',shy:'Wstyd',laugh:'Śmiech',super:'Super!',cry:'Płacz',angry:'Grr',dizzy:'Zawrót',shock:'Szok',Actions:'Ruchy',Emotes:'Emocje'}};
function al(n){return ((AL[(S&&S.lang)||'en']||AL.en)[n])||n}
var T={en:{Chat:'Chat',Outfit:'Outfit',Games:'Games',Play:'Play',Message:'Message',Note:'Note',send:'Send',none:'None',off:'Pocket K is offline',Saved:'Saved outfits',Save:'Save',name:'Outfit name',write:'Write something sweet...',notew:'18:30 Drink water',
empty:'Say hi! The pet will show your message on the desktop.',back:'‹ Back',rps:'Rock Paper Scissors',ttt:'Tic-Tac-Toe',mem:'Memory',rpsd:'Duel or vs pet',tttd:'You vs the pet',memd:'Find the pairs',
newmsg:'New message!',duel:'Duel is on! Pick your move',solo:'You vs Pocket K',locked:'Locked in ✓ waiting for the reveal...',win:'You win!',lose:'Pocket K wins!',draw:'Draw!',you:'You',them:'Them',yt:'Your turn ♥',pt:'Pocket K is thinking...',again:'Play again',moves:'Moves',won:'Score',sent:'Sent ♥',ok:'✓',Hats:'Hats',Eyes:'Eyes',Wear:'Wear',Neck:'Neck',Hand:'Hand'},
tr:{Chat:'Sohbet',Outfit:'Kıyafet',Games:'Oyunlar',Play:'Oyna',Message:'Mesaj',Note:'Not',send:'Gönder',none:'Yok',off:'Pocket K çevrimdışı',Saved:'Kayıtlı kombinler',Save:'Kaydet',name:'Kombin adı',write:'Tatlı bir şey yaz...',notew:'18:30 Su iç',
empty:'Merhaba de! Mesajın masaüstünde görünür.',back:'‹ Geri',rps:'Taş Kağıt Makas',ttt:'XOX',mem:'Hafıza',rpsd:'Düello ya da pete karşı',tttd:'Sen ve pet',memd:'Çiftleri bul',
newmsg:'Yeni mesaj!',duel:'Düello başladı! Hamleni seç',solo:'Sen ve Pocket K',locked:'Seçildi ✓ sonuç bekleniyor...',win:'Sen kazandın!',lose:'Pocket K kazandı!',draw:'Berabere!',you:'Sen',them:'O',yt:'Sıra sende ♥',pt:'Pocket K düşünüyor...',again:'Tekrar oyna',moves:'Hamle',won:'Skor',sent:'Gönderildi ♥',ok:'✓',Hats:'Şapka',Eyes:'Gözlük',Wear:'Kıyafet',Neck:'Boyun',Hand:'El'},
pl:{Chat:'Czat',Outfit:'Strój',Games:'Gry',Play:'Zabawa',Message:'Wiadomość',Note:'Notatka',send:'Wyślij',none:'Brak',off:'Pocket K jest offline',Saved:'Zapisane stroje',Save:'Zapisz',name:'Nazwa stroju',write:'Napisz coś miłego...',notew:'18:30 Napij się wody',
empty:'Powiedz cześć! Wiadomość pojawi się na pulpicie.',back:'‹ Wróć',rps:'Kamień Papier Nożyce',ttt:'Kółko i krzyżyk',mem:'Memory',rpsd:'Pojedynek lub z petem',tttd:'Ty kontra pet',memd:'Znajdź pary',
newmsg:'Nowa wiadomość!',duel:'Pojedynek! Wybierz ruch',solo:'Ty kontra Pocket K',locked:'Wybrano ✓ czekamy na wynik...',win:'Wygrałaś!',lose:'Pocket K wygrywa!',draw:'Remis!',you:'Ty',them:'On',yt:'Twój ruch ♥',pt:'Pocket K myśli...',again:'Jeszcze raz',moves:'Ruchy',won:'Wynik',sent:'Wysłano ♥',ok:'✓',Hats:'Czapki',Eyes:'Okulary',Wear:'Ubranie',Neck:'Szyja',Hand:'Ręka'}};
function $(i){return document.getElementById(i)}
function esc(s){return String(s).replace(/[&<>"']/g,function(c){return '&#'+c.charCodeAt(0)+';'})}
function tx(k){return (T[(S&&S.lang)||'en']||T.en)[k]||k}
function toast(m){var t=$('toast');t.textContent=m;t.style.opacity=1;clearTimeout(toast.h);toast.h=setTimeout(function(){t.style.opacity=0},1400)}
function api(path,body){return fetch(path,{method:body?'POST':'GET',headers:{'X-Token':K,'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined}).then(function(r){if(!r.ok)throw r.status;return r.json()})}
function av(worn,scale,pose){var q=['k='+encodeURIComponent(K),'scale='+scale];if(pose)q.push('pose='+pose);SL.forEach(function(s){if(worn&&worn[s])q.push(s+'='+encodeURIComponent(worn[s]))});return '/api/avatar.png?'+q.join('&')}
function setAv(pose){if(!S)return;var u=av(S.worn,6,pose);if(u!==avsrc){avsrc=u;$('av').src=u}}
function happy(){setAv('happy');clearTimeout(happy.h);happy.h=setTimeout(function(){setAv()},1300)}
/* ---- tabs */
var TABS=[['✉','Chat'],['✿','Outfit'],['★','Games'],['♪','Play']];
function buildNav(){var h='';TABS.forEach(function(t,i){h+='<button data-t="'+i+'" class="'+(i==TAB?'on':'')+'"><b>'+t[0]+'</b>'+tx(t[1])+'</button>'});$('nav').innerHTML=h}
function showTab(n){TAB=n;for(var i=0;i<4;i++)$('p'+i).classList.toggle('on',i==n);
document.body.className=(n==1?'tall':'small');buildNav();if(n==0)scrollLog(true)}
$('nav').onclick=function(e){var b=e.target.closest('button');if(b)showTab(+b.dataset.t)};
/* ---- labels */
function label(){$('m0').textContent=tx('Message');$('m1').textContent=tx('Note');$('send').textContent=tx('send');$('sh').textContent=tx('Saved');
$('psave').textContent=tx('Save');$('pname').placeholder=tx('name');$('msg').placeholder=mode=='note'?tx('notew'):tx('write');buildNav()}
/* ---- chat */
var STK=['♥','🥰','😘','✨','🌸','☕','🌙','💪'];
$('stk').innerHTML=STK.map(function(s){return '<button data-s="'+s+'">'+s+'</button>'}).join('');
$('stk').onclick=function(e){var b=e.target.closest('button');if(!b)return;$('msg').value+=b.dataset.s;$('msg').focus()};
$('m0').onclick=function(){mode='msg';$('m0').classList.add('on');$('m1').classList.remove('on');$('msg').placeholder=tx('write')};
$('m1').onclick=function(){mode='note';$('m1').classList.add('on');$('m0').classList.remove('on');$('msg').placeholder=tx('notew')};
$('msg').oninput=function(){this.style.height='46px';this.style.height=Math.min(120,this.scrollHeight)+'px'};
function scrollLog(force){var l=$('log');if(force||l.scrollHeight-l.scrollTop-l.clientHeight<90)l.scrollTop=l.scrollHeight}
function renderChat(){var c=S.chat||[],s=JSON.stringify(c);if(s===sig)return;sig=s;
var h=c.length?'':'<div class="empty">'+esc(tx('empty'))+'</div>';
c.forEach(function(m){var d=new Date(m.ts*1000),t=('0'+d.getHours()).slice(-2)+':'+('0'+d.getMinutes()).slice(-2);
h+='<div class="b '+(m.from=='pet'?'pet':m.from=='pc'?'pc':'me')+'">'+(m.from=='pc'?'<i>💻 Karolina</i>':'')+esc(m.text)+'<small>'+t+'</small></div>'});$('log').innerHTML=h;scrollLog(true);
var pcs=c.filter(function(m){return m.from=='pc'}).length;if(renderChat.pc!==undefined&&pcs>renderChat.pc){toast('💌 '+tx('newmsg'));try{navigator.vibrate(120)}catch(e){}}renderChat.pc=pcs}
$('send').onclick=function(){var v=$('msg').value.trim();if(!v)return;
api(mode=='note'?'/api/note':'/api/message',{text:v}).then(function(){$('msg').value='';$('msg').style.height='46px';toast(tx('sent'));happy();setTimeout(refresh,500)}).catch(function(){toast('!')})};
/* ---- outfit */
function renderOutfit(){var h='';(S.presets||[]).forEach(function(p,i){
h+='<div class="card" data-ap="'+i+'"><img src="'+av(p.worn,3)+'"><div>'+esc(p.name)+'</div><button class="x" data-dp="'+i+'">✕</button></div>'});$('pre').innerHTML=h||'<div class="empty" style="padding:8px">—</div>';
h='';S.slots.forEach(function(sl){h+='<h2>'+esc(tx(sl.name))+'</h2><div class="grid">';
(S.catalog[sl.slot]||[]).forEach(function(it){var w={};w[sl.slot]=it.id;
h+='<button class="tile'+(S.worn[sl.slot]==it.id?' on':'')+'" data-s="'+sl.slot+'" data-i="'+it.id+'"><img src="'+av(w,2)+'">'+esc(it.label)+'</button>'});
h+='<button class="tile'+(!S.worn[sl.slot]?' on':'')+'" data-s="'+sl.slot+'" data-i=""><span style="font-size:28px;line-height:62px">∅</span>'+tx('none')+'</button></div>'});$('slots').innerHTML=h}
function go(path,body,done){api(path,body).then(function(){if(done)done();refresh()}).catch(function(){toast('!')})}
$('p1').onclick=function(e){var b=e.target.closest('button,.card');if(!b)return;
if(b.dataset.dp!==undefined){go('/api/outfit_delete',{index:+b.dataset.dp});return}
if(b.dataset.s!==undefined){if(S){S.worn[b.dataset.s]=b.dataset.i||null;setAv('happy');clearTimeout(happy.h);happy.h=setTimeout(function(){setAv()},1300)}
go('/api/outfit',{slot:b.dataset.s,id:b.dataset.i})}
else if(b.dataset.ap!==undefined)go('/api/outfit_apply',{index:+b.dataset.ap},function(){toast(tx('ok'));happy()})};
$('psave').onclick=function(){var v=$('pname').value.trim();if(!v)return;go('/api/outfit_save',{name:v},function(){$('pname').value='';toast(tx('ok'))})};
/* ---- play */
function renderActs(){function mk(n){return '<button class="card" data-a="'+n+'"><b>'+(EJ[n]||'★')+'</b>'+esc(al(n))+'</button>'}
$('h_act').textContent=al('Actions');$('h_emo').textContent=al('Emotes');
$('acts').innerHTML=S.actions.filter(function(n){return EM.indexOf(n)<0}).map(mk).join('');
$('emos').innerHTML=S.actions.filter(function(n){return EM.indexOf(n)>=0}).map(mk).join('')}
$('p3').onclick=function(e){var b=e.target.closest('button');if(b&&b.dataset.a)go('/api/action',{name:b.dataset.a},function(){toast(tx('ok'));happy()})};
/* ---- games */
var HAND={rock:'✊',paper:'✋',scissors:'✌️'};
function sc(n){var s=(S&&S.scores&&S.scores[n])||{win:0,lose:0,draw:0};return tx('won')+': '+s.win+' – '+s.lose+' – '+s.draw}
function menu(){G=null;$('gview').style.display='none';$('gmenu').style.display='';
var d=[['rps','✊','rps','rpsd'],['ttt','✕','ttt','tttd'],['mem','✿','mem','memd']];
$('gmenu').innerHTML=d.map(function(g){return '<button class="card gcard" data-g="'+g[0]+'"><b>'+g[1]+'</b><span>'+tx(g[2])+'<small>'+tx(g[3])+' · '+sc(g[0])+'</small></span></button>'}).join('')}
$('gmenu').onclick=function(e){var b=e.target.closest('button');if(b)openGame(b.dataset.g)};
function openGame(g){G=g;$('gmenu').style.display='none';$('gview').style.display='';
var v=$('gview');v.innerHTML='<button class="back" id="gback">'+tx('back')+'</button><div id="gbody"></div>';$('gback').onclick=function(){menu();refresh()};
if(g=='rps')drawRps();else if(g=='ttt')tttInit();else memInit()}
function report(n,r){api('/api/game',{name:n,result:r}).then(function(){setTimeout(refresh,300)}).catch(function(){})}
/* RPS (pet / duel) */
function drawRps(){if(G!='rps'||!$('gbody'))return;var d=S&&S.duel&&S.duel.open,r=S&&S.rps;
var h='<div class="banner">'+tx(d?'duel':'solo')+'</div><div class="score">'+sc('rps')+'</div>';
var locked=(d&&S.duel.ready)||waiting,dis=locked||(d&&S.duel.stage=='reveal');
h+='<div class="rps">'+['rock','paper','scissors'].map(function(m){return '<button data-m="'+m+'"'+(dis?' disabled style="opacity:.5"':'')+'>'+HAND[m]+'</button>'}).join('')+'</div>';
if(locked)h+='<div class="res" style="font-size:13px;margin-top:12px">'+tx('locked')+'</div>';
if(r&&r.seq>0&&r.seq==shownSeq){h+='<div class="vs"><div>'+HAND[r.mine]+'<small>'+tx('you')+'</small></div><div style="font-size:20px">vs</div><div>'+HAND[r.other]+'<small>'+tx('them')+'</small></div></div><div class="res">'+tx(r.result)+'</div>'}
$('gbody').innerHTML=h}
var shownSeq=-1,pickedSeq0=null,waiting=false;
$('gview').onclick=function(e){var b=e.target.closest('button');if(!b||b.disabled)return;
if(b.dataset.m){waiting=true;drawRps();api('/api/rps_move',{move:b.dataset.m}).then(function(){var t=0,iv=setInterval(function(){t++;api('/api/state').then(function(s){S=s;
if(s.rps&&s.rps.seq!=pickedSeq0){shownSeq=s.rps.seq;pickedSeq0=s.rps.seq;waiting=false;clearInterval(iv);drawRps();happy()}else if(t>40){waiting=false;clearInterval(iv);drawRps()}}).catch(function(){})},500)}).catch(function(){waiting=false;toast('!');drawRps()})}};
/* Tic-Tac-Toe */
var B,over;var LN=[[0,1,2],[3,4,5],[6,7,8],[0,3,6],[1,4,7],[2,5,8],[0,4,8],[2,4,6]];
function win(b){for(var i=0;i<8;i++){var l=LN[i];if(b[l[0]]&&b[l[0]]==b[l[1]]&&b[l[1]]==b[l[2]])return b[l[0]]}return b.indexOf(0)<0?'d':0}
function mm(b,p){var w=win(b);if(w=='o')return 1;if(w=='x')return -1;if(w=='d')return 0;var best=p=='o'?-2:2;
for(var i=0;i<9;i++)if(!b[i]){b[i]=p;var s=mm(b,p=='o'?'x':'o');b[i]=0;if(p=='o'?s>best:s<best)best=s}return best}
function aiMove(){var e=[];B.forEach(function(v,i){if(!v)e.push(i)});if(Math.random()<.35)return e[Math.floor(Math.random()*e.length)];
var best=-2,bi=e[0];e.forEach(function(i){B[i]='o';var s=mm(B,'x');B[i]=0;if(s>best){best=s;bi=i}});return bi}
function tttInit(){B=[0,0,0,0,0,0,0,0,0];over=false;tttDraw(tx('yt'))}
function tttDraw(msg){var h='<div class="score">'+sc('ttt')+'</div><div class="res">'+msg+'</div><div class="ttt">';
for(var i=0;i<9;i++)h+='<button data-c="'+i+'">'+(B[i]=='x'?'<span style="color:var(--pink)">♥</span>':B[i]=='o'?'●':'')+'</button>';
h+='</div>'+(over?'<div class="row"><button class="pri" id="again">'+tx('again')+'</button></div>':'');$('gbody').innerHTML=h;
var a=$('again');if(a)a.onclick=tttInit;
document.querySelectorAll('.ttt button').forEach(function(b){b.onclick=function(){var i=+b.dataset.c;if(over||B[i])return;B[i]='x';
var w=win(B);if(w)return fin(w);tttDraw(tx('pt'));setTimeout(function(){B[aiMove()]='o';var w2=win(B);if(w2)return fin(w2);tttDraw(tx('yt'))},500)}})}
function fin(w){over=true;var r=w=='x'?'win':w=='o'?'lose':'draw';tttDraw(tx(r));report('ttt',r);if(r=='win')happy()}
/* Memory */
var M,flip,lock,mv,pairs;
function memInit(){var e=['♥','★','☺','✿','☾','♪','✦','☀'],a=e.concat(e);for(var i=a.length-1;i>0;i--){var j=Math.floor(Math.random()*(i+1)),t=a[i];a[i]=a[j];a[j]=t}
M=a.map(function(s){return{s:s,up:false,ok:false}});flip=[];lock=false;mv=0;pairs=0;memDraw()}
function memDraw(){var h='<div class="score">'+sc('mem')+' · '+tx('moves')+': '+mv+'</div><div class="mem">';
M.forEach(function(c,i){h+='<button data-c="'+i+'" class="'+(c.ok?'ok':c.up?'up':'')+'">'+(c.up||c.ok?c.s:'?')+'</button>'});h+='</div>';
if(pairs==8)h+='<div class="res">'+tx('win')+'</div><div class="row"><button class="pri" id="again">'+tx('again')+'</button></div>';
$('gbody').innerHTML=h;var a=$('again');if(a)a.onclick=memInit;
document.querySelectorAll('.mem button').forEach(function(b){b.onclick=function(){var i=+b.dataset.c,c=M[i];if(lock||c.up||c.ok)return;c.up=true;flip.push(i);
if(flip.length==2){mv++;lock=true;var x=M[flip[0]],y=M[flip[1]];
if(x.s==y.s){x.ok=y.ok=true;x.up=y.up=false;flip=[];lock=false;pairs++;memDraw();if(pairs==8){report('mem',mv<=14?'win':'draw');happy()}}
else{memDraw();setTimeout(function(){x.up=y.up=false;flip=[];lock=false;memDraw()},750)}}else memDraw()}})}
/* ---- state */
function refresh(){api('/api/state').then(function(s){S=s;if(pickedSeq0===null)pickedSeq0=(s.rps&&s.rps.seq)||0;$('st').textContent='';setAv();label();renderChat();renderOutfit();renderActs();
if(G=='rps')drawRps();else if(!G)menu()}).catch(function(){$('st').textContent=tx('off')})}
showTab(0);refresh();setInterval(function(){if(!(TAB==2&&(G=='mem'||G=='ttt')))refresh()},4000);
</script></body></html>"""


# ===========================================================================
#  PET
# ===========================================================================
MAIN_ITEMS = [("♪", "Dance", "dance"), ("☾", "Sleep", "sleep"), ("♥", "Kiss", "kiss"),
              ("☺", "Wave", "wave"), ("↑", "Jump", "jump"), ("↻", "Spin", "spin"),
              ("»", "Run", "run"), ("♡", "Hug", "hug"), ("✿", "Bag", "bag"),
              ("✎", "Notes", "notes"), ("✉", "Chat", "msgs"), ("◐", "Game mode", "hide"),
              ("⚙", "Settings", "settings"), ("×", "Quit", "quit")]

VISIT_ENERGY = {"chair": 0.9, "radio": -0.4, "mug": 0.3, "cupcake": 0.8, "teddy": 0.6}   # obje kullanırken enerji
AFF_DECAY = 0.18          # ilgi: saniyede düşüş (ilgilenilmezse)
ENERGY_PER_SEC = {"sleep": 1.6, "sit": 0.35, "sulk": 0.3, "yawn": 0.2, "dangle": 0.25,
                  "look": 0.15, "idle": 0.12, "walk": -0.12, "run": -0.7, "dance": -0.5,
                  "climb": -0.45, "kiss": -0.05, "wave": -0.05, "selfie": -0.1,
                  "jump": -0.2, "spin": -0.2, "flop": 0.6}


def clamp100(v):
    return max(0.0, min(100.0, v))


class Pet:
    DUR = {"walk": (90, 220), "run": (60, 120), "idle": (40, 90), "sit": (90, 170),
           "sleep": (260, 460), "dance": (110, 190), "wave": (70, 90), "kiss": (70, 90),
           "jump": (1, 1), "spin": (1, 1), "selfie": (80, 80), "hug": (80, 90),
           "bored": (120, 200), "sulk": (160, 280), "yawn": (45, 55),
           "dangle": (150, 320), "look": (80, 140), "climb": (900, 900), "dropoff": (1, 1),
           "visit": (6000, 6000), "stretch": (62, 62), "emote": (100, 100),
           "flop": (100, 120)}

    def __init__(self, save_path=None, watcher_provider=None):
        self.root = tk.Tk()
        r = self.root
        r.title("Pocket Karolina")
        r.overrideredirect(True)
        r.wm_attributes("-topmost", True)
        make_transparent(r)

        self.sprite_w = W * SCALE
        self.cw = self.sprite_w + 2 * PADX
        self.ch = H * SCALE + PADT
        self.cv = tk.Canvas(r, width=self.cw, height=self.ch, bg=KEY, highlightthickness=0)
        self.cv.pack()
        self.item = self.cv.create_image(PADX, PADT, anchor="nw")
        self.speech_font = tkfont.Font(family="Courier New", size=10, weight="bold")

        self.sw = r.winfo_screenwidth()
        self.sh = r.winfo_screenheight()
        self.ground = self.sh - self.ch - GROUND_MARGIN
        self.floor = self.ground                 # şu anki destek seviyesi (zemin veya tünek)
        self.x = float(random.randint(120, max(130, self.sw - 300)))
        self.y = 0.0
        self.vx = self.vy = 0.0

        # durum
        self.cache = {}
        self.cur_img = None
        self._warm, self._warm_on = [], False
        self._next_t = None
        self._geo = None
        self._fx_on = self._balloon_on = False
        self.sit_prog = 0.0           # oturma/kalkma geçişi (0 ayakta, 1 oturuyor)
        self.gaze = 0                 # imlece bakış yönü (-1, 0, 1)
        self.particles = []
        self.t = 0
        self.dir = 1
        self.phase = 0.0
        self.action = "idle"
        self.a_t, self.a_dur = 0, 40
        self.land_t = self.react_t = 0
        self.photo_done = False
        self.blink_t, self.next_blink = 0, 50
        self.dragging = False
        self.moved = 0
        self.press = self.off = (0, 0)
        self.samples = []
        self.hold_t = 0                   # tutulma süresi (tick)
        self.swing = self.swing_v = 0.0   # tutulurken sarkma (sarkaç)
        self.mouse_speed = 0.0
        self.last_ptr = self.grab = (0, 0)
        self.bubble = None
        self.menu_open = False
        self.frog = self.dog = None
        self.props = {}
        self.speech = None
        self.face_left = False
        self.cur_flip = False
        self.preview = {}
        self.style_tab = 0
        self.perch = self.perch_plat = None
        self.leaving = None           # tünekten yürüyerek ayrılıyor
        self.visit = None             # masa objesini kullanma (içme, koklama, uyku...)
        self.emote = None             # oynayan emote kimliği
        self.chaos = None             # kaos modu durumu (dict) ya da None
        self.chaos_fix = None         # kaos sonrası kıyafeti toparlama zamanlayıcısı
        self.treat = None             # Lila'ya atılan kuru et
        self.surprises = []           # masaüstündeki küçük hediyeler
        self.hidden = None            # oyun modu: None | "manual" | "auto"
        self.tray = None
        self.fs_t = 0
        self.skip_land = None         # (pencere id, bitiş tick'i): kısa süre tekrar konma
        self.climb = None
        self.climbing = False
        self.ball = self.ball_game = None
        self.rps_pose = None
        self.cheer_t = 0
        self.remote = self.remote_tr = None
        self.last_love = self.last_poke = self.last_any = -99999
        self.last_chat = {}
        self.dirty = False
        self.last_save = 0

        # kayıt
        self.save_path = save_path or default_save_path()
        d = load_save(self.save_path)
        self.stats = d["stats"]
        self.counters = d["counters"]
        self.worn = d["worn"]
        self.notes = d["notes"]
        self.prefs = d["prefs"]
        LANG[0] = self.prefs.get("lang", "en")
        self.games = d["games"]
        self.inbox = d["inbox"]
        self.presets = d["outfits"]
        self.found = d["found"]
        self.season = d["season"]
        self.phone_rps = {"seq": 0}
        self.apply_offline(d["saved_at"])
        self.check_date()
        interval = self.prefs["remind_every"] * 30
        self.next_remind = int(interval * random.uniform(0.7, 1.3))
        self.first_run = not d["saved_at"]
        self.next_surprise = random.randint(3 * 60 * 30, 7 * 60 * 30)
        self.greet_t = 70 if d["saved_at"] else 60
        self.away_hours = max(0.0, (time.time() - d["saved_at"]) / 3600) if d["saved_at"] else 0

        self.watcher = WindowWatcher(self, watcher_provider)

        cv = self.cv
        cv.bind("<ButtonPress-1>", self.on_press)
        cv.bind("<B1-Motion>", self.on_drag)
        cv.bind("<ButtonRelease-1>", self.on_release)
        cv.bind("<Double-Button-1>", lambda e: self.start("dance", user=True))
        for seq in ("<Button-3>", "<Button-2>", "<Control-Button-1>"):
            cv.bind(seq, lambda e: self.open_main())

        # yoldaşlar ve masa objeleri geri gelsin
        if d["companions"]["frog"]:
            self.frog = Frog(self)
        if d["companions"]["dog"]:
            self.dog = Dog(self)
        for p in d["props"]:
            self.props[p["kind"]] = DeskProp(self, p["kind"], p["x"], p["on"])

        atexit.register(self.save)
        r.report_callback_exception = lambda et, ev, tb: self.log_error(
            "".join(__import__("traceback").format_exception(et, ev, tb)))
        if self.prefs["remote"]:
            try:
                self.start_remote()
            except Exception:
                self.prefs["remote"] = False
                self.log_error()
        self.season_check(quiet=True)
        self.refresh_cache()
        self.tick()

    # ================================================================ KAYIT
    def collect_state(self):
        return {
            "version": SAVE_VERSION, "saved_at": time.time(),
            "stats": {k: round(v, 1) for k, v in self.stats.items()},
            "counters": dict(self.counters), "worn": dict(self.calm_worn()),
            "companions": {"frog": self.frog is not None, "dog": self.dog is not None},
            "props": [p.state() for p in self.props.values()],
            "notes": [dict(n) for n in self.notes], "prefs": dict(self.prefs),
            "games": {"rps": dict(self.games["rps"]), "ball": dict(self.games["ball"]),
                      "phone": {g: dict(v) for g, v in self.games["phone"].items()}},
            "outfits": [{"name": o["name"], "worn": dict(o["worn"])} for o in self.presets],
            "inbox": [dict(m) for m in self.inbox],
            "found": dict(self.found), "season": dict(self.season),
        }

    def save(self):
        ok = write_save(self.save_path, self.collect_state())
        self.dirty = not ok
        self.last_save = self.t
        return ok

    def save_soon(self):
        self.dirty = True

    def apply_offline(self, saved_at):
        """Uygulama kapalıyken geçen süre: enerji toparlanır, ilgi biraz düşer."""
        if not saved_at:
            return
        hrs = max(0.0, (time.time() - saved_at) / 3600.0)
        st = self.stats
        st["energy"] = clamp100(st["energy"] + min(70.0, hrs * 25))
        st["affection"] = clamp100(max(5.0, st["affection"] - min(30.0, hrs * 5)))
        target = 0.5 * st["affection"] + 0.35 * st["energy"] + 15
        st["mood"] = clamp100(st["mood"] * 0.8 + min(100.0, target) * 0.2)

    def check_date(self):
        today = datetime.date.today().isoformat()
        if self.counters.get("date") != today:
            self.counters = {"date": today, "cuddles": 0, "selfies": 0, "climbs": 0, "throws": 0}

    # ================================================== MOOD / ENERJİ / İLGİ
    def bump(self, mood=0.0, energy=0.0, aff=0.0):
        st = self.stats
        st["mood"] = clamp100(st["mood"] + mood)
        st["energy"] = clamp100(st["energy"] + energy)
        st["affection"] = clamp100(st["affection"] + aff)

    def love(self, aff=0.0, mood=0.0, kind=None):
        self.bump(mood=mood, aff=aff)
        self.last_love = self.t
        if kind == "cuddle":
            self.counters["cuddles"] += 1
        self.save_soon()

    def stats_step(self):
        """Saniyede bir çalışır."""
        st = self.stats
        en = ENERGY_PER_SEC.get(self.action, 0.0)
        if self.action == "visit" and self.visit and self.visit["stage"] == "do":
            en = VISIT_ENERGY.get(self.visit["kind"], 0.0)
        elif self.menu_open:
            en = 0.1
        recent = self.t - self.last_love < 300
        self.bump(energy=en, aff=0.0 if recent else -AFF_DECAY)
        target = (0.5 * st["affection"] + 0.35 * st["energy"] + 15 +
                  3 * ((self.frog is not None) + (self.dog is not None)) + 2 * len(self.props))
        st["mood"] = clamp100(st["mood"] + (min(100.0, target) - st["mood"]) * 0.03)
        if self.action == "dance":
            self.bump(mood=0.25)
        if self.dragging and self.hold_t > 240:             # uzun süre tutulmak rahatsız eder
            self.bump(mood=-1.2)
        self.check_date()
        if self.action == "sleep" and st["energy"] >= 95 and self.a_t > 60:
            self.a_dur = 0                                   # uyandı
            self.chat("wake", cooldown=300)

    # ======================================================= KONUŞMA / REPLİK
    def say(self, text, dur=100, kind="say"):
        if self.hidden:
            return
        if self.speech:
            self.speech.destroy()
        self.speech = Speech(self, text, kind, dur)

    def chat(self, kind, force=False, cooldown=600, dur=110, gap=True):
        """Rastgele tatlı replik. Ayarlardan 'Chatter' kapalıysa sessiz (force hariç)."""
        if not force and (not self.prefs["chatter"] or self.prefs["calm"]):
            return False
        if self.t - self.last_chat.get(kind, -99999) < cooldown:
            return False
        if gap and not force and self.t - self.last_any < 150:
            return False
        lines = LINES[self.prefs["lang"]].get(kind)
        if not lines:
            return False
        self.last_chat[kind] = self.last_any = self.t
        self.say(random.choice(lines), dur)
        return True

    # ================================================================ NOTLAR
    def add_note(self, raw):
        m = re.match(r"^\s*(\d{1,2})[:.](\d{2})\s+(.+)$", raw)
        due, text = None, raw.strip()
        if m and int(m.group(1)) < 24 and int(m.group(2)) < 60:
            due = "%02d:%02d" % (int(m.group(1)), int(m.group(2)))
            text = m.group(3).strip()
        now = datetime.datetime.now()
        alerted = now.date().isoformat() if (due and now.strftime("%H:%M") >= due) else ""
        self.notes.append({"text": text[:80], "done": False, "due": due, "alerted": alerted})
        if len(self.notes) > 60:
            for n in self.notes:
                if n["done"]:
                    self.notes.remove(n)
                    break
            else:
                self.notes.pop(0)
        self.bump(mood=2)
        for _ in range(3):
            self.spawn("spark", PADX + 16 * SCALE, PADT + 8 * SCALE)
        self.chat("noted", force=True, cooldown=120)
        self.save_soon()

    def toggle_note(self, n):
        n["done"] = not n["done"]
        if n["done"]:
            self.bump(mood=3)
            self.spawn("spark", PADX + 16 * SCALE, PADT + 8 * SCALE)
            self.chat("done", force=True, cooldown=200)
        self.save_soon()

    def delete_note(self, n):
        if n in self.notes:
            self.notes.remove(n)
            self.save_soon()

    def clear_done_notes(self):
        self.notes[:] = [n for n in self.notes if not n["done"]]
        self.save_soon()

    def diary_line(self):
        L, c, st = LINES[self.prefs["lang"]], self.counters, self.stats
        opts = []
        if c["cuddles"]:
            opts.append(L["d_cuddle"].format(n=c["cuddles"]))
        if c["selfies"]:
            opts.append(L["d_selfie"].format(n=c["selfies"]))
        if c["climbs"]:
            opts.append(L["d_climb"].format(n=c["climbs"]))
        if self.dog:
            opts.append(L["d_dog"])
        if self.frog:
            opts.append(L["d_frog"])
        if st["mood"] > 70:
            opts.append(L["d_happy"])
        elif st["affection"] < 35:
            opts.append(L["d_meh"])
        return random.choice(opts or [L["d_plain"]])

    def alert_note(self, n, due=False):
        L = LINES[self.prefs["lang"]]
        self.say(L["due" if due else "remind"].format(text=n["text"]), 230, "think")
        for _ in range(4):
            self.spawn("spark", PADX + 16 * SCALE, PADT + 4 * SCALE)
        if due and not self.perch and self.action not in ("sleep", "climb"):
            self.start("wave", 70)

    def check_due(self):
        now = datetime.datetime.now()
        today, hm = now.date().isoformat(), now.strftime("%H:%M")
        for n in self.notes:
            if n.get("due") and not n["done"] and n.get("alerted") != today and hm >= n["due"]:
                n["alerted"] = today
                self.alert_note(n, due=True)
                self.save_soon()
                return

    def do_remind(self):
        interval = self.prefs["remind_every"] * 30
        if self.action == "sleep" or self.menu_open or self.dragging:
            self.next_remind = self.t + 300            # biraz sonra tekrar dene
            return
        self.next_remind = self.t + int(interval * random.uniform(0.7, 1.3))
        pend = [n for n in self.notes if not n["done"]]
        if pend and random.random() < 0.75:
            self.alert_note(random.choice(pend))
        elif self.prefs["chatter"]:
            self.say(self.diary_line(), 230, "think")

    # ===================================================== EŞYALAR / PANELLER
    def eff_worn(self):
        w = dict(self.worn)
        for s, v in self.preview.items():           # panel üzerinde gezinirken anlık önizleme
            w[s] = v or None
        return w

    def eq_tuple(self):
        w = self.eff_worn()
        return tuple(w[s] for s in SLOTS)

    def sleeping_now(self):
        v = self.visit
        return self.action == "sleep"

    def excited_now(self):
        v = self.visit
        return (self.action in ("dance", "kiss", "jump", "spin") or
                bool(v and v["kind"] == "radio" and v["stage"] == "do"))

    def is_on(self, kind, iid):
        if kind == "worn":
            return self.worn.get(SLOT_OF[iid]) == iid
        if kind == "prop":
            return iid in self.props
        if kind == "pal":
            return (self.frog if iid == "frog" else self.dog) is not None
        if kind == "game":
            if iid == "chaos":
                return bool(self.chaos)
            if iid == "treat":
                return bool(self.treat or (self.dog and self.dog.chew))
            return iid == "ball" and bool(self.ball_game)
        return False

    def tile_action(self, kind, iid):
        if kind == "worn":
            self.toggle_item(iid)
        elif kind == "clear":
            self.chaos_fix = None
            for s in (("neck", "held") if iid == "gear" else (iid,)):
                self.worn[s] = None
            self.save_soon()
        elif kind == "prop":
            self.toggle_prop(iid)
        elif kind == "pal":
            self.toggle_pal(iid)
        elif kind == "emote":
            self.do_emote(iid, user=True)
        elif kind == "corner":
            self.arrange_corner()

    def sparkle(self, n=5):
        for _ in range(n):
            self.spawn("spark", PADX + 16 * SCALE, PADT + 8 * SCALE)

    def toggle_item(self, iid):
        self.chaos_fix = None
        slot = SLOT_OF[iid]
        if self.worn[slot] == iid:
            self.worn[slot] = None
            self.chat("unequip", cooldown=200)
        else:
            self.worn[slot] = iid
            self.bump(mood=2)
            self.chat("equip", cooldown=200)
        self.react_t = 36
        self.sparkle()
        self.save_soon()
        self.refresh_cache()

    def clear_worn(self):
        self.chaos_fix = None
        for s in SLOTS:
            self.worn[s] = None
        self.sparkle(6)
        self.save_soon()
        self.refresh_cache()

    def toggle_prop(self, kind):
        if kind in self.props:
            if self.visit and self.visit["kind"] == kind:
                self.cancel_visit()
                self.start("idle", 20)
            self.props.pop(kind).destroy()
        else:
            self.props[kind] = DeskProp(self, kind)
            self.bump(mood=3)
        self.sparkle(3)
        self.save_soon()

    def toggle_pal(self, which):
        if which == "frog":
            if self.frog:
                self.frog.destroy()
                self.frog = None
            else:
                self.frog = Frog(self)
                self.chat("frog", cooldown=300)
        else:
            if self.dog:
                self.end_ball(quiet=True)
                self.drop_treat()
                self.dog.destroy()
                self.dog = None
            else:
                self.dog = Dog(self)
                self.chat("dog", cooldown=300)
                self.root.after(500, lambda: self.dog and self.dog.bark("HAU!", 40))
        self.bump(mood=4)
        self.sparkle()
        self.save_soon()

    # ===================================================================== OYUNLAR
    def open_rps(self):
        if self.bubble:
            return
        self.menu_open = True
        cx, top = self._anchor()
        self.bubble = RPSPanel(self, cx, top)

    def toggle_ball(self):
        if self.ball_game:
            self.end_ball()
        else:
            self.start_ball()

    def start_ball(self):
        if self.ball_game:
            return
        if not self.dog:                                    # Lila oyuna katılsın
            self.dog = Dog(self)
        self.ball = Ball(self, self.x + self.cw / 2 + self.dir * 30, self.y + self.ch / 2,
                         self.dir * 11.0, -11.0)
        self.ball_game = {"touch": self.t, "fetches": 0}
        self.dog.begin_fetch()
        self.chat("ball_start", force=True, cooldown=0, dur=70)
        self.root.after(500, lambda: self.dog and self.dog.bark("HAU!", 40))
        self.save_soon()

    def end_ball(self, quiet=False):
        g = self.ball_game
        if not g:
            return
        self.ball_game = None
        if self.ball:
            self.ball.destroy()
            self.ball = None
        if self.dog:
            self.dog.end_fetch()
        if not quiet and g["fetches"]:
            self.chat("ball_end", force=True, cooldown=0, dur=80)
        self.save_soon()

    def touch_ball(self):
        if self.ball_game:
            self.ball_game["touch"] = self.t

    def on_fetch_done(self):
        g = self.ball_game
        if not g:
            return
        g["fetches"] += 1
        g["touch"] = self.t
        self.games["ball"]["fetches"] += 1
        self.love(aff=2, mood=3)
        self.cheer_t = 60
        if self.dog and self.action not in ("walk", "run", "climb", "visit", "sleep"):
            self.dir = 1 if self.dog.x > self.x else -1
        self.chat("ball_back", force=True, cooldown=0, dur=80)
        for _ in range(3):
            self.spawn("heart", PADX + (16 + 2 * self.dir) * SCALE, PADT + 14 * SCALE)

    def ball_game_step(self):
        g = self.ball_game
        if g and self.t - g["touch"] > 2700:                # ~90 sn ilgisiz kalırsa biter
            self.end_ball()

    # ===================================================== TELEFON / UZAKTAN KONTROL
    def remote_url(self):
        p = self.prefs
        host = lan_ip() if p["lan"] else "127.0.0.1"
        return "http://%s:%d/?k=%s" % (host, p["port"], p["token"])

    def remote_snapshot(self):
        cat = {s: [] for s in SLOTS}
        for _name, _slot, tiles in STYLE_TABS:
            for kind, iid, label in tiles:
                if kind == "worn":
                    cat[SLOT_OF[iid]].append({"id": iid, "label": L(label, self.prefs["lang"])})
        names = {"hat": "Hats", "glasses": "Eyes", "outfit": "Wear", "neck": "Neck", "held": "Hand"}
        return {"ok": True, "lang": self.prefs["lang"], "worn": dict(self.worn),
                "slots": [{"slot": s, "name": names.get(s, s)} for s in SLOTS if cat[s]],
                "catalog": cat, "actions": list(REMOTE_ACTIONS),
                "presets": [{"name": o["name"], "worn": o["worn"]} for o in self.presets],
                "chat": [{"from": m.get("from", "phone"), "text": m["text"], "ts": m["ts"]}
                         for m in self.inbox[-40:]],
                "scores": {g: dict(v) for g, v in self.games["phone"].items()},
                "rps": dict(self.phone_rps), "duel": self.duel_state()}

    def duel_state(self):
        b = self.bubble
        if isinstance(b, RPSPanel) and b.duel and b.state != "closing":
            return {"open": True, "stage": b.stage,
                    "ready": b.phone_move is not None and b.stage != "reveal"}
        return {"open": False}

    def publish_remote(self):
        if self.remote:
            self.remote.publish(self.remote_snapshot())

    def start_remote(self):
        if self.remote:
            return True
        p = self.prefs
        if not NET_OK:
            p["remote"] = False
            self.say(pick_line(p["lang"], "remote_fail"), 120, "think")
            return False
        if not p["token"]:
            p["token"] = secrets.token_urlsafe(9)
        core = RemoteCore(p["token"])
        tr = HttpTransport(core, "0.0.0.0" if p["lan"] else "127.0.0.1", p["port"], PHONE_PAGE)
        try:
            tr.start()
        except (OSError, OverflowError):                   # port dolu / izin yok
            p["remote"] = False
            self.say(pick_line(p["lang"], "remote_fail"), 120, "think")
            return False
        self.remote, self.remote_tr = core, tr
        p["remote"] = True
        self.publish_remote()
        self.export_pairing()
        self.save_soon()
        return True

    def stop_remote(self):
        if self.remote_tr:
            self.remote_tr.stop()
        self.remote = self.remote_tr = None
        self.prefs["remote"] = False
        self.save_soon()

    def export_pairing(self):
        """Eşleştirme bağlantısını dosyaya yazar ve panoya kopyalar."""
        url = self.remote_url()
        try:
            path = os.path.join(os.path.dirname(os.path.abspath(self.save_path)), "phone_link.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(url + "\n\nOpen this on the phone (same Wi-Fi). Keep it private: "
                        "anyone with the link can control the pet.\n")
        except OSError:
            pass
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(url)
        except tk.TclError:
            pass
        print("Phone link:", url)
        return url

    def pair_info(self):
        if not self.remote:
            self.say(pick_line(self.prefs["lang"], "remote_off"), 100, "think")
            return
        self.say(pick_line(self.prefs["lang"], "remote_on") + " " + self.export_pairing(), 360, "think")

    def remote_command(self, cmd):
        kind = cmd[0]
        if kind == "message":
            self.receive_message(cmd[1])
        elif kind == "note":
            self.add_note(cmd[1])
            self.chat_log("phone", "\u270e " + cmd[1])
            self.chat_log("pet", pick_line(self.prefs["lang"], "noted"))
        elif kind == "outfit_save":
            self.save_preset(cmd[1])
        elif kind == "outfit_apply":
            self.apply_preset(cmd[1])
        elif kind == "outfit_delete":
            if 0 <= cmd[1] < len(self.presets):
                del self.presets[cmd[1]]
                self.save_soon()
        elif kind == "game":
            self.phone_game(cmd[1], cmd[2])
        elif kind == "rps_move":
            self.phone_rps_move(cmd[1])
        elif kind == "outfit":
            self.remote_outfit(cmd[1], cmd[2])
        elif kind == "action" and cmd[1] == "poke":
            self.phone_poke()
        elif kind == "action" and self.hidden:
            pass                                             # oyun modunda: gösteri yok
        elif kind == "action" and cmd[1] == "treat":
            self.throw_treat()
        elif kind == "action" and cmd[1] == "chaos":
            self.toggle_chaos()
        elif kind == "action":
            if not (self.dragging or self.climbing or self.menu_open or self.visit):
                if cmd[1] in EMOTES:
                    self.do_emote(cmd[1], user=True)
                else:
                    self.start(cmd[1], user=True)
        self.publish_remote()

    def chat_log(self, who, text):
        self.inbox.append({"text": text, "ts": time.time(), "from": who})
        del self.inbox[:-60]

    def receive_message(self, text):
        self.chat_log("phone", text)
        last_pc = max((m["ts"] for m in self.inbox if m.get("from") == "pc"), default=0)
        if time.time() - last_pc > 900:                     # PC başında kimse yazmıyorsa tatlı cevap
            self.chat_log("pet", pick_line(self.prefs["lang"], random.choice(("poke", "poke", "hug", "kiss"))))
        if isinstance(self.bubble, ChatPanel):              # sohbet açık: zaten görünüyor
            self.love(aff=4, mood=3)
            self.save_soon()
            return
        hint = ""
        if self.prefs.get("chat_hint"):
            self.prefs["chat_hint"] = False
            hint = "\n" + pick_line(self.prefs["lang"], "chat_hint")
        self.say("✉ " + tk_safe(text) + hint, min(420, 150 + len(text) * 4), "love")
        for _ in range(4):
            self.spawn("heart", PADX + random.choice([4, 12, 20, 28]) * SCALE, PADT + 6 * SCALE)
        self.love(aff=6, mood=5)
        self.react_t = 36
        if self.action == "sleep":
            self.a_dur = 0
        self.save_soon()

    def send_from_pc(self, text):
        text = clean_text(text, MAX_MSG)
        if not text:
            return
        self.chat_log("pc", text)
        for _ in range(2):
            self.spawn("heart", PADX + 16 * SCALE, PADT + 8 * SCALE)
        self.publish_remote()
        self.save_soon()

    def phone_poke(self):
        self.chat_log("phone", pick_line(self.prefs["lang"], "poke_log"))
        if self.hidden:
            self.save_soon()
            return
        self.say(pick_line(self.prefs["lang"], "poke_phone"), 170, "love")
        for _ in range(5):
            self.spawn("heart", PADX + random.choice([4, 12, 20, 28]) * SCALE, PADT + 6 * SCALE)
        self.love(aff=5, mood=4)
        if not (self.dragging or self.climbing or self.visit or self.menu_open or self.chaos or self.perch):
            self.start("jump", user=False)
        self.react_t = 40
        self.save_soon()

    def save_preset(self, name):
        """Üzerindeki kombini isimle kaydeder (aynı isim varsa günceller, doluysa en eskiyi siler)."""
        entry = {"name": name, "worn": dict(self.worn)}
        for i, o in enumerate(self.presets):
            if o["name"].lower() == name.lower():
                self.presets[i] = entry
                break
        else:
            self.presets.append(entry)
            del self.presets[:-MAX_PRESETS]
        self.sparkle(3)
        self.save_soon()

    def apply_preset(self, i):
        self.chaos_fix = None
        if not 0 <= i < len(self.presets):
            return
        for sl in SLOTS:
            v = self.presets[i]["worn"].get(sl)
            self.worn[sl] = v if SLOT_OF.get(v) == sl else None
        self.bump(mood=2)
        self.react_t = 36
        self.sparkle()
        self.chat("outfit_new", force=True, cooldown=0)
        self.save_soon()
        self.refresh_cache()

    def phone_game(self, name, result):
        """Telefondaki oyunun sonucu: skor tut, karakter tepki versin (result telefon oyuncusu açısından)."""
        g = self.games["phone"][name]
        g[result] += 1
        key = {"win": "rps_lose", "lose": "rps_win", "draw": "rps_draw"}[result]
        if not self.bubble and not self.dragging:
            self.say(pick_line(self.prefs["lang"], key), 110)
        if result == "lose":
            self.cheer_t = 45
            self.spawn("note", PADX + random.choice([2, 28]) * SCALE, PADT + 10 * SCALE)
        else:
            for _ in range(2):
                self.spawn("heart", PADX + random.choice([8, 20]) * SCALE, PADT + 8 * SCALE)
        self.love(aff=3, mood=1 if result == "lose" else 2)
        self.save_soon()

    def phone_rps_move(self, move):
        """Telefondan gelen taş-kağıt-makas hamlesi: masaüstü düello açıksa onunla, değilse pet'le oynar."""
        b = self.bubble
        if isinstance(b, RPSPanel) and b.duel:
            if b.stage in ("pick", "count", "wait") and b.phone_move is None:
                b.phone_move = move
            return
        pm = random.choice(RPS_MOVES)
        r = rps_result(move, pm)
        self.set_phone_rps(move, pm, {"you": "win", "pet": "lose", "draw": "draw"}[r], False)

    def set_phone_rps(self, mine, other, result, duel):
        self.phone_rps = {"seq": self.phone_rps["seq"] + 1, "mine": mine, "other": other,
                          "result": result, "duel": duel}
        self.phone_game("rps", result)

    def remote_outfit(self, slot, iid):
        self.chaos_fix = None
        if slot not in SLOTS or (iid and SLOT_OF.get(iid) != slot):
            return
        self.worn[slot] = iid or None
        self.bump(mood=2)
        self.react_t = 36
        self.sparkle()
        self.chat("outfit_new", force=True, cooldown=0)
        self.save_soon()
        self.refresh_cache()

    # ----- ayarlar balonu
    def settings_items(self):
        climb_lab = "Climb" if self.watcher.available() else "Climb n/a"
        return [("A", lambda: L("Lang") + ": " + self.prefs["lang"].upper(), "lang"),
                ("…", "Chatter", "chat"), ("☾", "Calm", "calm"), ("▲", climb_lab, "climb"),
                ("✦", "Flash", "flash"), ("◐", "Auto hide", "autohide"),
                ("☎", "Phone", "remote"), ("✉", "Link", "pair"),
                ("‹", "Back", "back")]

    def use_item(self, cid):
        p = self.prefs
        if cid == "lang":
            langs = list(LINES)
            p["lang"] = langs[(langs.index(p["lang"]) + 1) % len(langs)]
            LANG[0] = p["lang"]
        elif cid == "chat":
            p["chatter"] = not p["chatter"]
        elif cid == "calm":
            p["calm"] = not p["calm"]
            if p["calm"]:
                self.say(pick_line(p["lang"], "calm_on"), 90)
        elif cid == "climb":
            p["climb"] = not p["climb"]
            if not p["climb"]:
                self.climb = None
                self.climbing = False
        elif cid == "flash":
            p["flash"] = not p["flash"]
        elif cid == "autohide":
            p["autohide"] = not p["autohide"]
        elif cid == "remote":
            if self.remote:
                self.stop_remote()
            else:
                self.start_remote()
        self.save_soon()

    def pref_on(self, cid):
        return {"chat": self.prefs["chatter"], "calm": self.prefs["calm"], "climb": self.prefs["climb"],
                "flash": self.prefs["flash"], "remote": bool(self.remote),
                "autohide": self.prefs["autohide"]}.get(cid, False)

    # ----- menü açma
    def _anchor(self):
        return int(self.x + self.cw / 2), int(self.y + PADT + 5 * SCALE)

    def open_main(self):
        if self.bubble:
            return
        self.menu_open = True
        cx, top = self._anchor()
        self.bubble = Bubble(self, cx, top, MAIN_ITEMS, "~ What now? ~", btnw=106)

    def open_style(self):
        if self.bubble:
            return
        self.menu_open = True
        cx, top = self._anchor()
        self.bubble = StylePanel(self, cx, top)

    def open_notes(self):
        if self.bubble:
            return
        self.menu_open = True
        cx, top = self._anchor()
        self.bubble = NotesPanel(self, cx, top)

    def open_chat(self):
        if self.bubble:
            return
        self.menu_open = True
        cx, top = self._anchor()
        self.bubble = ChatPanel(self, cx, top)

    def open_settings(self):
        if self.bubble:
            return
        self.menu_open = True
        cx, top = self._anchor()
        stay = ("lang", "chat", "calm", "climb", "flash", "autohide", "remote")
        self.bubble = Bubble(self, cx, top, self.settings_items(), "~ Settings ~", cols=2,
                             btnw=144, equipped=self.pref_on, stay=lambda c: c in stay)

    def close_bubble(self):
        if self.bubble:
            self.bubble.close()

    def bubble_closed(self, choice):
        self.bubble = None
        self.preview.clear()
        nxt = {"bag": self.open_style, "notes": self.open_notes, "msgs": self.open_chat,
               "settings": self.open_settings, "back": self.open_main}
        nxt["game_rps"] = self.open_rps
        if choice == "game_treat":
            self.menu_open = False
            self.root.after(40, self.throw_treat)
            return
        if choice == "hide":
            self.menu_open = False
            self.root.after(120, lambda: self.set_hidden("manual"))
            return
        if choice == "game_chaos":
            self.menu_open = False
            self.root.after(40, self.toggle_chaos)
            return
        if choice == "game_ball":
            self.menu_open = False
            self.root.after(40, self.toggle_ball)
            return
        if choice in nxt:
            self.root.after(40, nxt[choice])
            return
        self.menu_open = False
        if choice and choice.startswith("emote_"):
            self.root.after(60, lambda: self.do_emote(choice[6:], user=True))
            return
        if choice == "quit":
            self.shutdown()
        elif choice == "pair":
            self.pair_info()
        elif choice == "phone":
            self.start("selfie", user=True)
        elif choice:
            self.start(choice, user=True)

    def shutdown(self):
        self.save()
        if self.tray:
            self.tray.remove()
            self.tray = None
        if self.remote_tr:
            self.remote_tr.stop()
        if self.treat:
            self.treat.destroy()
        for sp in self.surprises:
            sp.destroy()
        if self.ball:
            self.ball.destroy()
        for c in (self.frog, self.dog):
            if c:
                c.destroy()
        for p in self.props.values():
            p.destroy()
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    # ===================================================================== FARE
    def image(self, key, flip):
        k = (key, flip)
        im = self.cache.get(k)
        if im is None:
            if len(self.cache) > 500:                       # sınırsız büyümesin
                self.cache.clear()                          # (cur_img ayrıca tutulur)
            im = self.cache[k] = grid_to_image(compose(key), PAL, flip, SCALE)
        return im

    def show(self, key, flip):
        key = key[:16] + self.eq_tuple() + key[21:]
        self.cur_flip = flip
        self.cur_img = self.image(key, flip)
        self.cv.itemconfig(self.item, image=self.cur_img)

    def warm_keys(self):
        """Yürüme / koşma / bekleme karelerini önceden üretir: ilk kullanımda takılma olmasın."""
        keys = [K(), K(hdy=1), K(eyes="closed"), K(eyes="closed", hdy=1),
                K(bdy=3, legs="sit"), K(bdy=3, legs="sit", hdy=1)]
        for T, mouth in ((WALK, "smile"), (RUN, "grin")):
            for p in range(8):
                ll, lr = T["ll"][p], T["lr"][p]
                keys.append(K(hdx=T["hx"][p], bdy=T["bob"][p], mouth=mouth, ald=-lr, ard=-ll,
                              ll=ll, lr=lr, ldx=1 if ll else 0, rdx=1 if lr else 0))
        return [(k, f) for k in keys for f in (False, True)][::-1]

    def refresh_cache(self):
        self._warm = self.warm_keys()
        if not self._warm_on:
            self._warm_on = True
            self.root.after(40, self.warm_step)

    def warm_step(self):
        for _ in range(2):
            if not self._warm:
                self._warm_on = False
                return
            key, flip = self._warm.pop()
            self.image(key[:16] + self.eq_tuple() + key[21:], flip)
        self.root.after(25, self.warm_step)

    def on_press(self, e):
        self.close_bubble()
        self.dragging = True
        self.moved = 0
        self.press = (e.x_root, e.y_root)
        self.off = (e.x, e.y)
        self.grab = (e.x, e.y)                              # tıklanan nokta -> yakaya kayar
        self.last_ptr = (e.x_root, e.y_root)
        self.hold_t = 0
        self.swing = self.swing_v = self.mouse_speed = 0.0
        self.cancel_visit()
        self.vx = self.vy = 0
        self.climb, self.climbing = None, False          # tutulunca tırmanma / tünek biter
        self.perch = self.perch_plat = None
        self.leaving = None
        self.floor = self.ground

    def on_drag(self, e):
        self.moved = max(self.moved, abs(e.x_root - self.press[0]) +
                         abs(e.y_root - self.press[1]))
        self.samples.append((time.time(), e.x_root, e.y_root))
        self.samples = self.samples[-8:]
        self.hold_pos()                                     # kare beklemeden imleci takip et
        self.place()

    def on_release(self, e):
        self.dragging = False
        now = time.time()
        sm = [p for p in self.samples if now - p[0] < 0.1]
        self.samples = []
        vx = vy = 0.0
        if len(sm) >= 2 and sm[-1][0] > sm[0][0]:
            k = TICK_MS / 1000.0 / (sm[-1][0] - sm[0][0])   # px/sn -> px/tick
            vx = (sm[-1][1] - sm[0][1]) * k
            vy = (sm[-1][2] - sm[0][2]) * k
        if self.moved < 5:
            if self.chaos:
                self.stop_chaos(early=True)
                return
            self.poke()
            return
        self.vx = max(-22.0, min(22.0, vx))                 # fırlatma
        self.vy = max(-40.0, min(30.0, vy))
        self.start("idle", 20)
        if self.hold_t > 240 and self.stats["mood"] < 70 and self.vy > -9:
            self.start("bored", 100)                        # uzun tutuldu: hafif triplenir
        if self.vy < -9:                                    # hızlıca yukarı = KURWA!
            self.y -= 2
            self.say("KURWA!", 75, "angry")
            self.bump(mood=-6, aff=-1)
            self.counters["throws"] += 1
            if self.dog:
                self.dog.bark("HAU HAU!", 50)
            for dx in (-22, 22):
                self.spawn("txt", PADX + 16 * SCALE + dx, PADT + 4 * SCALE,
                           text="!", col="#e63946", size=20, life=22)
            self.save_soon()

    def place(self, off=0):
        geo = f"+{round(self.x)}+{round(self.y) + off}"
        if geo != self._geo:
            self._geo = geo
            self.root.geometry(geo)

    def hold_pos(self):
        """Karakter yakasından tutulmuş gibi imlecin altında asılı durur."""
        px, py = self.root.winfo_pointerx(), self.root.winfo_pointery()
        k = min(1.0, self.hold_t / 10.0)                    # tutuş noktası yumuşakça yakaya kayar
        ox = self.grab[0] + (self.cw / 2 - self.grab[0]) * k
        oy = self.grab[1] + (PADT + 15 * SCALE - self.grab[1]) * k
        self.x, self.y = px - ox, py - oy
        return px, py

    def held_step(self):
        """Sarkaç fiziği + tepki: yavaşta sallanır, hızlıda panikler, uzun sürede triplenir."""
        px, py = self.hold_pos()
        vx, vy = px - self.last_ptr[0], py - self.last_ptr[1]
        self.last_ptr = (px, py)
        self.mouse_speed += (math.hypot(vx, vy) - self.mouse_speed) * 0.25
        self.swing_v += -vx * 0.05 - self.swing * 0.14 - self.swing_v * 0.12
        self.swing = max(-1.6, min(1.6, self.swing + self.swing_v))
        self.hold_t += 1
        mood = self.stats["mood"]
        if self.hold_t == 45 and mood >= 55:
            self.chat("held", cooldown=900)
        elif self.hold_t == (70 if mood < 55 else 160):
            self.chat("held_annoyed", cooldown=900)
        if self.mouse_speed > 9 and self.t % 40 == 0:
            self.chat("panic", cooldown=600)
        return self.held_pose()

    def held_pose(self):
        t, sw, sp = self.t, self.swing, self.mouse_speed
        sd = int(round(sw * 2.5))                           # bacaklar geriden gelir
        ad = int(round(sw * 1.5))
        hd = -int(round(sw * 0.8))
        if sp > 9:                                          # panik: kollar havada, tekmeliyor
            k = (t // 3) % 2
            return K(bdy=1, al="u", ar="u", ald=-k, ard=-(1 - k), alx=-k, arx=k,
                     eyes="wide", mouth="open", ll=2 * k, lr=2 * (1 - k), ldx=sd, rdx=sd, hdx=hd)
        grumpy = (self.stats["mood"] < 55 and self.hold_t > 60) or self.hold_t > 150
        kick = (t // 8) % 2 if sp > 3 else (t // 16) % 2
        if grumpy:                                          # rahatsız: somurtur, hafif sallanır
            return K(bdy=1, eyes="annoyed", mouth="kiss", ll=(t // 18) % 2, ldx=sd, rdx=sd,
                     alx=ad, arx=ad, hdx=hd)
        return K(bdy=1, eyes="happy", mouth="grin", ll=kick, lr=1 - kick, ldx=sd, rdx=sd,
                 alx=ad, arx=ad, hdx=hd)

    def poke(self):
        """Tek tık: sevgi. Küs / sıkkınsa daha büyük etki ve barışma."""
        gap = self.t - self.last_poke
        self.last_poke = self.t
        g = 7 if gap > 45 else 2
        sulking = self.action in ("sulk", "bored")
        extra = 6 if sulking else 0
        self.love(aff=g + extra, mood=g * 0.8 + extra, kind="cuddle")
        for _ in range(3):
            self.spawn("heart", PADX + 16 * SCALE, PADT + 8 * SCALE)
        v = self.visit
        if v:
            self.cancel_visit()
        if sulking:
            self.chat("forgive", force=True, cooldown=0)
            self.start("kiss", 60)
        else:
            self.chat("poke", cooldown=240)
            self.start("wave", 45)

    # ================================================================== AKSİYON
    def start(self, name, dur=None, user=False):
        self.action = name
        self.a_t = 0
        lo, hi = self.DUR.get(name, (60, 60))
        self.a_dur = dur or random.randint(lo, hi)
        if name in ("walk", "run"):
            self.dir = random.choice([-1, 1])
        if name != "climb":
            self.climb, self.climbing = None, False
        if name != "visit":
            self.cancel_visit()
        self.land_t = 0
        self.photo_done = False
        if name in ("jump", "spin"):
            self.bump(energy=-3)
        if user:                                            # kullanıcı ilgisi
            gain = {"dance": (3, 6, None), "kiss": (5, 5, "cuddle"), "wave": (2, 3, None),
                    "hug": (14, 8, "cuddle"), "jump": (1, 3, None), "spin": (1, 3, None),
                    "selfie": (4, 8, None)}.get(name)
            if gain:
                self.love(aff=gain[0], mood=gain[1], kind=gain[2])
        if name == "stretch":
            self.a_dur = 62
        if name == "hug" or (name == "kiss" and user):
            self.chat(name, cooldown=300)
        elif name == "sulk":
            self.chat("sulk", cooldown=900)
        elif name == "bored":
            self.chat("bored", cooldown=900)
        elif name == "yawn" or name == "sleep":
            self.chat("sleepy", cooldown=900)

    def weights(self):
        st = self.stats
        e, a, m = st["energy"], st["affection"], st["mood"]
        if self.perch:
            w = {"dangle": 48, "look": 22, "wave": 6, "kiss": 4, "walk": 10, "dropoff": 6,
                 "sleep": 12 if e < 50 else 3}
            if a < 28:
                w["sulk"] = 20
            return w
        w = {"walk": 38, "run": 8, "idle": 12, "sit": 7, "sleep": 8, "dance": 10,
             "wave": 6, "jump": 6, "kiss": 4, "spin": 3, "stretch": 5}
        if e < 30:
            w.update(run=0, dance=0, jump=0, spin=0, walk=14, sit=22, sleep=30, yawn=12,
                     stretch=9)
        elif e > 75:
            w.update(run=16, dance=18, jump=12, spin=7, sleep=1, sit=3)
        if a < 45:
            w["bored"] = 16
        if a < 28:
            w.update(sulk=24, kiss=0, wave=1, dance=2)
        if m > 78:
            w["dance"] = w["dance"] * 1.4
            w["kiss"] += 4
            w["wave"] += 4
        if self.climb_targets():
            w["climb"] = 7
        if self.props:
            w["visit"] = min(26, 10 + 4 * len(self.props))
        if m > 55 and e > 35 and not self.prefs["calm"]:
            w["emote"] = 5                                   # ara sıra kendiliğinden ifade yapar
        if self.prefs["calm"]:                               # sakin mod: az hareket, az gürültü
            for k, f in (("run", 0), ("dance", .25), ("jump", .2), ("spin", .2), ("climb", .15),
                         ("walk", .45), ("visit", .5), ("wave", .4)):
                if k in w:
                    w[k] = w[k] * f
            w["sit"] = w.get("sit", 0) + 18
            w["idle"] = w.get("idle", 0) + 12
        return w

    def next_action(self):
        if self.chaos:
            self.chaos_next()
            return
        st = self.stats
        if self.action == "sleep" and st["energy"] < 55:     # toparlanana dek uyu
            self.start("sleep", 300)
            return
        if self.action == "sleep" and not self.perch:       # uyanınca esner
            self.start("stretch")
            return
        if st["energy"] < 10:
            self.start("sleep", 600)
            return
        for _ in range(4):
            w = {k: v for k, v in self.weights().items() if v > 0}
            pick = random.choices(list(w), weights=list(w.values()))[0]
            if pick == "dropoff":
                self.drop_off()
                return
            if pick == "climb" and not self.begin_climb():
                continue
            if pick == "visit" and not self.begin_visit():
                continue
            if pick == "emote":
                self.do_emote(random.choice(AUTO_EMOTES[:] if self.stats["affection"] > 40 else AUTO_EMOTES[2:]))
                return
            if pick not in ("climb", "visit"):
                self.start(pick)
            return
        self.start("idle")

    # ================================================================ TIRMANMA
    def climb_targets(self):
        if not self.prefs["climb"] or self.perch or self.climb:
            return []
        lim = self.ground + self.ch - 130
        return [p for p in list(self.watcher.platforms)
                if p["y"] <= lim and p["x2"] - p["x1"] >= 140]

    def begin_climb(self):
        ts = self.climb_targets()
        if not ts:
            return False
        p = random.choice(ts)
        cx = self.x + self.cw / 2
        side = -1 if cx < (p["x1"] + p["x2"]) / 2 else 1
        for _ in range(2):
            tx = p["x1"] - 8 if side == -1 else p["x2"] + 8
            if 20 <= tx <= self.sw - 20:
                break
            side = -side
        else:
            return False
        self.start("climb")
        self.climb = {"id": p["id"], "side": side, "tx": tx, "stage": "walk", "t": 0, "over": 0}
        return True

    def platform(self, pid):
        return next((q for q in list(self.watcher.platforms) if q["id"] == pid), None)

    def climb_step(self):
        """(anahtar, flip) döndürür; iptal olursa None."""
        c = self.climb
        p = self.platform(c["id"])
        if p is None or not self.prefs["climb"]:
            self.climb, self.climbing = None, False
            return None
        c["t"] += 1
        py = p["y"] - self.ch
        cx = self.x + self.cw / 2
        c["tx"] = p["x1"] - 8 if c["side"] == -1 else p["x2"] + 8
        if c["stage"] == "walk":                            # pencerenin yanına yürü
            dx = c["tx"] - cx
            if abs(dx) < 6:
                c["stage"], self.climbing, self.vx = "up", True, 0.0
            else:
                self.dir = 1 if dx > 0 else -1
                self.vx += (self.dir * 3.2 - self.vx) * 0.2
                self.x += self.vx
                self.phase += abs(self.vx) * 0.14
                self.face_left = self.vx < 0
                return self.moving_pose(False), self.vx < 0
        if c["stage"] == "up":                              # kenardan tırman
            self.climbing = True
            self.x += (c["tx"] - cx) * 0.3
            self.y -= 2.8
            if self.y <= py:
                self.y, c["stage"], c["over"] = py, "over", 0
            flip = c["side"] == 1
            self.face_left = flip
            k = (self.t // 5) % 2
            return K(al="u", ar="u", ald=-k, ard=-(1 - k), ll=k, lr=1 - k,
                     eyes=self.eyes(), mouth="grin"), flip
        # over: kenarın üstüne adım at
        self.y = py
        c["over"] += 1
        step = 1 if c["side"] == -1 else -1
        self.x += step * 3.0
        self.phase += 0.4
        self.face_left = step < 0
        if c["over"] >= 14:
            self.set_perch(p, self.y)
            self.climb, self.climbing = None, False
            self.counters["climbs"] += 1
            self.spawn("dust", PADX + 16 * SCALE - 14, PADT + 30 * SCALE)
            self.spawn("dust", PADX + 16 * SCALE + 14, PADT + 30 * SCALE)
            self.chat("perch", cooldown=900)
            self.start("dangle")
            self.save_soon()
        return self.moving_pose(False), step < 0

    def set_perch(self, p, y):
        """Pencere kenarına tüne: bir süre sonra kendiliğinden iner."""
        self.perch = {"id": p["id"], "x1": p["x1"], "t": 0,
                      "limit": random.randint(750, 1800)}        # ~25-60 sn
        self.perch_plat = p
        self.floor = y

    def track_perch(self):
        """Tünek penceresini takip et: küçük kaymada eşlik et, kapanır/uzağa giderse düş."""
        pr = self.perch
        p = self.platform(pr["id"])
        if p is None or not self.prefs["climb"]:
            self.leave_perch()
            return False
        py = p["y"] - self.ch
        cx = self.x + self.cw / 2
        dx = p["x1"] - pr["x1"]
        if abs(py - self.y) > 90 or abs(dx) > 200 or not (p["x1"] - 30 <= cx <= p["x2"] + 30):
            self.leave_perch()
            return False
        self.x += dx
        pr["x1"] = p["x1"]
        pr["t"] += 1
        if pr["t"] > pr["limit"] and not self.leaving and not self.menu_open:
            self.drop_off()                                    # yeterince oturdu: inmeye karar ver
        d = py - self.y
        self.y += d * 0.5 if abs(d) > 1 else d
        self.floor = self.y
        self.perch_plat = p
        return True

    def leave_perch(self, hop=False, quiet=False):
        self.perch = self.perch_plat = None
        self.leaving = None
        self.floor = self.ground
        if hop:
            self.vy, self.vx = -4.0, self.dir * 3.0
        if not quiet:
            self.chat("fall", cooldown=300)

    def drop_off(self):
        """Tünekte en yakın kenara yürü, oradan aşağı atla."""
        p = self.perch_plat
        if not p:
            return
        cx = self.x + self.cw / 2
        direction = -1 if (cx - p["x1"]) < (p["x2"] - cx) else 1
        self.start("walk", 900)
        self.dir = direction
        self.leaving = p["id"]

    def step_off(self):
        pid = self.perch["id"] if self.perch else None
        self.leave_perch(hop=True, quiet=True)
        self.leaving = None
        if pid is not None:
            self.skip_land = (pid, self.t + 90)
        self.start("idle", 20)

    def find_landing(self, prev_y):
        if self.vy <= 0 or not self.prefs["climb"]:
            return None
        cx = self.x + self.cw / 2
        best = None
        for p in list(self.watcher.platforms):
            if self.skip_land and p["id"] == self.skip_land[0] and self.t < self.skip_land[1]:
                continue
            py = p["y"] - self.ch
            if prev_y <= py + 1 and self.y >= py and p["x1"] + 10 <= cx <= p["x2"] - 10:
                if best is None or py < best[0]:
                    best = (py, p)
        return best

    def on_land(self, impact):
        feet_y = PADT + 30 * SCALE
        if impact > 3:
            self.spawn("dust", PADX + 16 * SCALE - 14, feet_y)
            self.spawn("dust", PADX + 16 * SCALE + 14, feet_y)
            self.land_t = 5
        if self.perch:
            self.chat("perch", cooldown=900)

    # ================================================================ OBJELERLE ETKİLEŞİM
    def pick_visit_kind(self):
        """Saate, enerjiye ve mood'a göre hangi objeyi kullanacağını seçer."""
        hour = datetime.datetime.now().hour
        night = hour >= 19 or hour < 6
        e, m, a = self.stats["energy"], self.stats["mood"], self.stats["affection"]
        w = {}
        for kind, prop in self.props.items():
            if prop.hidden:
                continue
            if kind == "chair":
                w[kind] = 12 if e < 60 else 4
            elif kind == "mug":
                w[kind] = 12 if e < 60 else 7
            elif kind == "plant":
                w[kind] = 8
            elif kind == "lamp":                             # geceyse aç, gündüzse kapat
                w[kind] = 30 if (night and not prop.on) or (not night and prop.on) else 3
            elif kind == "radio":
                w[kind] = 0 if e < 20 else (12 if (m > 55 and e > 40) else 4)
            elif kind == "mirror":
                w[kind] = 6 if m > 50 else 2
            elif kind == "cupcake":
                w[kind] = 12 if e < 50 else 5
            elif kind == "teddy":
                w[kind] = 14 if (m < 50 or a < 50) else 5
            elif kind == "books":
                w[kind] = 8 if night else 5
            elif kind == "cactus":
                w[kind] = 4
        w = {k: v for k, v in w.items() if v > 0}
        return random.choices(list(w), weights=list(w.values()))[0] if w else None

    def begin_visit(self, kind=None, user=False):
        if self.perch or self.climb or self.climbing or not self.props:
            return False
        kind = kind or self.pick_visit_kind()
        prop = self.props.get(kind) if kind else None
        if prop is None or prop.hidden:
            return False
        self.start("visit", 6000)
        self.visit = {"kind": kind, "stage": "walk", "t": 0, "walk_t": 0, "user": user}
        if user:
            self.love(mood=1)
        return True

    def visit_prop(self, kind):
        """Objeye tıklanınca karakter gelip onu kullanır."""
        if self.dragging or self.menu_open or self.perch or self.climbing:
            return
        if self.visit and self.visit["kind"] == kind:
            return
        self.begin_visit(kind, user=True)

    def cancel_visit(self):
        if self.visit:
            for p in self.props.values():
                p.hidden = False
                if p.kind in ("radio", "mirror"):
                    p.on = False
        self.visit = None

    def finish_visit(self):
        self.cancel_visit()
        self.start("idle", 40)

    def visit_step(self):
        """(anahtar, flip) döndürür; bitince / iptalde None."""
        v = self.visit
        prop = self.props.get(v["kind"])
        if prop is None:
            self.cancel_visit()
            return None
        cx = self.x + self.cw / 2
        tx = prop.x + prop.pw / 2
        if v["stage"] == "walk":                            # objenin yanına yürü
            v["walk_t"] += 1
            dx = tx - cx
            if abs(dx) < 8 or v["walk_t"] > 1500:
                v["stage"], v["t"] = "do", 0
                self.vx = 0.0
                self.root.lift()                            # karakter objenin önünde dursun
            else:
                self.dir = 1 if dx > 0 else -1
                self.vx += (self.dir * 3.0 - self.vx) * 0.2
                self.x += self.vx
                self.phase += abs(self.vx) * 0.14
                self.face_left = self.vx < 0
                return self.moving_pose(False), self.vx < 0
        v["t"] += 1
        if v["t"] % 120 == 0:
            self.root.lift()
        fn = getattr(self, "_v_" + v["kind"], None)
        if fn is None:
            self.finish_visit()
            return None
        key = fn(prop, v["t"], v)
        if key is None:
            self.finish_visit()
            return None
        flip = (self.t // 24) % 2 == 0 if v["kind"] == "radio" else self.dir < 0
        return key, flip

    # --- bitki: koklar, "ohh!" der
    def _v_plant(self, prop, t, v):
        if t == 30:
            self.chat("sniff", cooldown=0, gap=False)
        if t % 16 == 0 and 18 < t < 80:
            self.spawn("spark", PADX + 16 * SCALE, PADT + 14 * SCALE)
        if t < 18:
            return K(bdy=1, hdy=1, eyes=self.eyes())
        if t < 80:
            return K(bdy=1, hdy=1 + (t // 9) % 2, eyes="closed", mouth="smile")
        if t == 80:
            self.bump(mood=4)
            self.spawn("txt", PADX + 16 * SCALE, PADT + 2 * SCALE, text="!", col="#58b368",
                       size=20, life=22)
        if t < 105:
            return K(eyes="happy", mouth="open", al="u", ar="u", hdy=(t // 6) % 2)
        return None

    # --- kupa: yerden alır, içer, geri koyar
    def _v_mug(self, prop, t, v):
        if t == 12:
            prop.hidden = True
        if t == 36:
            self.chat("sip", cooldown=0, gap=False)
        if t == 96:
            prop.hidden = False
            self.bump(energy=6, mood=3)
        if t < 12:
            return K(bdy=2, hdy=1, eyes=self.eyes(), ard=1)
        if t < 30:
            return K(ar="u", arx=-5, ph=2, eyes=self.eyes())
        if t < 78:
            if t % 18 == 0:
                self.spawn("txt", PADX + 22 * SCALE, PADT + 12 * SCALE, text="~",
                           col="#cfd6e4", size=9, life=22)
            sip = (t // 12) % 2
            return K(ar="u", arx=-5, ph=2, hdy=sip, eyes="closed" if sip else "happy",
                     mouth="smile")
        if t < 96:
            return K(bdy=2, hdy=1, eyes=self.eyes(), ard=1)
        if t < 114:
            return K(eyes="happy", mouth="grin")
        return None

    # --- lamba: uzanıp açar / kapatır
    def _v_lamp(self, prop, t, v):
        if t == 12:
            prop.on = not prop.on
            self.spawn("txt", PADX + 16 * SCALE, PADT + 2 * SCALE, text="CLICK!",
                       col="#ffd23f", size=14, life=16)
            self.chat("lamp_on" if prop.on else "lamp_off", cooldown=0, gap=False)
            self.save_soon()
        if t < 12:
            return K(ar="u", arx=-1, hdx=1, eyes=self.eyes())
        if t < 40:
            return K(eyes="happy", mouth="grin")
        return None

    # --- ayna: pozlar verir; kullanıcı tıklarsa kombin de değiştirir
    def _v_mirror(self, prop, t, v):
        if t == 1:
            prop.on = True
        if t == 24 and v.get("user"):
            self.random_outfit()
        if t == 36:
            self.chat("mirror", cooldown=0, gap=False)
        if t % 22 == 0 and 10 < t < 90:
            self.spawn("spark", PADX + 16 * SCALE + random.choice((-14, 14)), PADT + 10 * SCALE)
        if t < 24:
            k = (t // 6) % 2
            return K(al="u", ar="u", ald=-k, ard=-(1 - k), eyes=self.eyes())
        if t < 90:
            p = (t // 14) % 3
            return K(eyes="happy" if p != 1 else "wink", mouth="grin",
                     hdx=(-1, 0, 1)[p], hdy=p % 2, ar="u" if p == 2 else "d", arx=p % 2)
        if t < 110:
            return K(eyes="happy", mouth="grin", hdy=(t // 8) % 2)
        prop.on = False
        return None

    # --- kek: alır, yer, kırıntı saçar
    def _v_cupcake(self, prop, t, v):
        if t == 12:
            prop.hidden = True
        if t == 40:
            self.chat("cupcake", cooldown=0, gap=False)
        if t == 100:
            prop.hidden = False
            self.bump(energy=5, mood=4)
            self.spawn("spark", PADX + 16 * SCALE, PADT + 10 * SCALE)
        if t < 12:
            return K(bdy=2, hdy=1, eyes=self.eyes(), ard=1)
        if t < 100:
            if t % 20 == 0:
                self.spawn("txt", PADX + 14 * SCALE, PADT + 14 * SCALE, text="~",
                           col="#ff9ebd", size=9, life=18)
            bite = (t // 10) % 2
            return K(ar="u", arx=-5, ph=0, hdy=bite, eyes="closed" if bite else "happy",
                     mouth="open" if bite else "grin")
        if t < 118:
            return K(eyes="happy", mouth="grin", hdy=(t // 6) % 2)
        return None

    # --- ayıcık: sarılır, kalpler çıkar
    def _v_teddy(self, prop, t, v):
        if t == 20:
            self.chat("teddy", cooldown=0, gap=False)
        if t % 24 == 0 and t >= 20:
            self.spawn("heart", PADX + 16 * SCALE, PADT + 8 * SCALE)
        if t == 110:
            self.bump(mood=5)
            self.love(aff=3)
        if t < 14:
            return K(al="u", ar="u", eyes=self.eyes())
        if t < 110:
            k = (t // 18) % 2
            return K(eyes="happy" if k else "closed", mouth="smile", al="u", ar="u", ald=1,
                     ard=1, alx=3, arx=-3, hdy=1, hdx=(t // 30) % 2)
        if t < 128:
            return K(eyes="happy", mouth="grin", hdy=(t // 8) % 2)
        return None

    # --- kitaplar: bir tane alıp okur
    def _v_books(self, prop, t, v):
        dur = v.setdefault("dur", random.randint(160, 260))
        end = 14 + dur
        if t == 14:
            self.chat("read", cooldown=0, gap=False)
        if t == end + 14:
            self.bump(mood=4)
        if t < 14:
            return K(al="u", ar="u", eyes=self.eyes())
        if t < end:
            if (t - 14) % 70 == 40:
                self.spawn("spark", PADX + 16 * SCALE, PADT + 24 * SCALE)
            return K(alx=3, arx=-3, ph=3, hdy=1, eyes="normal", mouth="smile")
        if t < end + 14:
            return K(al="u", ar="u", eyes=self.eyes())
        return None

    # --- kaktüs: dürter, "ouch!" der, güler
    def _v_cactus(self, prop, t, v):
        if t == 30:
            self.chat("cactus", cooldown=0, gap=False)
            self.spawn("txt", PADX + 24 * SCALE, PADT + 6 * SCALE, text="!", col="#e63946",
                       size=20, life=22)
        if t < 22:
            return K(ar="u", arx=(t // 5) % 2, hdy=1, eyes=self.eyes())
        if t < 34:
            return K(eyes="wide", mouth="open", al="u", ar="u", bdy=-2, hdy=-1)
        if t < 74:
            f = (t // 4) % 2
            return K(eyes="happy", mouth="laugh", hdy=f, bdy=f)
        return None

    # --- radyo: açar, müzikle dans eder, kapatır
    def _v_radio(self, prop, t, v):
        dur = v.setdefault("dur", random.randint(220, 320))
        end = 12 + dur
        if t == 12:
            prop.on = True
            self.chat("radio", cooldown=0, gap=False)
        if t == end:
            prop.on = False
            self.bump(mood=6, energy=-2)
        if t < 12:
            return K(ar="u", hdx=1, eyes=self.eyes())
        if t < end:
            if t % 9 == 0:
                self.spawn("note", PADX + random.choice([2, 28]) * SCALE, PADT + 10 * SCALE)
            d = DANCE[(t // 6) % 4]
            return K(eyes="happy", mouth="grin", alx=(t // 3) % 2, arx=-((t // 3) % 2), **d)
        if t < end + 16:
            return K(eyes="happy", mouth="grin")
        return None

    # --- koltuk: oturup dinlenir
    def _v_chair(self, prop, t, v):
        dur = v.setdefault("dur", random.randint(260, 420))
        if t == 1:
            self.chat("chair", cooldown=0, gap=False)
        if t < 20:
            return K(bdy=min(3, t // 5), legs="sit" if t >= 10 else "stand", eyes=self.eyes())
        if t < 20 + dur:
            return K(bdy=3, legs="sit", eyes=self.eyes(), mouth=self.mouth(), hdy=(t // 22) % 2)
        if t < 32 + dur:
            return K(bdy=2, eyes=self.eyes())
        return None

    def random_outfit(self):
        w = self.worn
        w["outfit"] = random.choice([o for o in OUTFITS if o != w["outfit"]])
        if random.random() < 0.5:
            w["hat"] = random.choice([None] + list(HATS))
        if random.random() < 0.35:
            w["glasses"] = random.choice([None] + list(GLASSES))
        self.sparkle(8)
        self.bump(mood=3)
        self.react_t = 60
        self.save_soon()
        self.refresh_cache()

    # ================================================================ KURU ET
    def throw_treat(self):
        if self.hidden or self.dragging:
            return
        if self.treat or (self.dog and self.dog.chew):
            self.chat("treat_busy", force=True, cooldown=0, gap=False)
            return
        self.end_ball(quiet=True)
        if not self.dog:
            self.dog = Dog(self)
            self.save_soon()
        hx = self.x + self.cw / 2 + self.dir * 20
        self.treat = Treat(self, hx - Treat.W / 2, self.y + PADT + 20 * SCALE,
                           self.dir * random.uniform(7.5, 12.5), -random.uniform(10, 13))
        self.dog.begin_chew()
        self.chat("treat_throw", force=True, cooldown=0, gap=False, dur=70)
        self.root.after(300, lambda: self.dog and self.dog.bark("HAU!", 30))
        if not (self.perch or self.climbing or self.visit):
            self.start("wave", 40)

    def on_treat_done(self):
        if self.treat:
            self.treat.destroy()
            self.treat = None
        self.love(aff=3, mood=5)
        self.chat("treat_done", force=True, cooldown=0, gap=False, dur=90)
        for _ in range(3):
            self.spawn("heart", PADX + 16 * SCALE, PADT + 10 * SCALE)
        self.save_soon()

    def drop_treat(self):
        if self.treat:
            self.treat.destroy()
            self.treat = None
        if self.dog:
            self.dog.stop_chew()

    # ============================================================ SÜRPRİZLER
    def surprise_step(self):
        for sp in self.surprises[:]:
            if not sp.update():
                sp.destroy()
                self.surprises.remove(sp)
            elif (sp.pet_ok and abs(self.vx) > 0.7 and not (self.dragging or self.perch or self.climbing)
                  and self.y >= self.ground - 1 and abs(sp.cx - (self.x + self.cw / 2)) < 16):
                self.collect_surprise(sp, False)
        if self.t >= self.next_surprise:
            self.next_surprise = self.t + random.randint(6 * 60 * 30, 14 * 60 * 30)
            if not (self.prefs["calm"] or self.chaos or len(self.surprises) >= 2):
                self.spawn_surprise()

    def spawn_surprise(self, kind=None):
        px = self.x + self.cw / 2
        for _ in range(8):
            x = random.randint(60, max(70, self.sw - 100))
            if abs(x - px) > 220:
                break
        sp = Surprise(self, kind or random.choice(list(SURPRISES)), x)
        self.surprises.append(sp)
        self.chat("surprise_new", cooldown=600)
        return sp

    def collect_surprise(self, sp, by_user):
        if sp.gone or sp not in self.surprises:
            return
        self.surprises.remove(sp)
        sp.destroy()
        self.found[sp.kind] = self.found.get(sp.kind, 0) + 1
        n = sum(self.found.values())
        self.bump(mood=4)
        self.love(aff=2 if by_user else 0, mood=0)
        self.sparkle(6)
        self.save_soon()
        if self.hidden:
            return
        self.say(pick_line(self.prefs["lang"], "found") + "  ♥ " + str(n), 90)
        self.react_t = 30
        self.save_soon()

    # ============================================================ MEVSİMLER
    def season_check(self, quiet=False):
        if self.chaos or self.chaos_fix:
            return
        cur = season_of(datetime.date.today())
        st = self.season
        if cur and st.get("key") != cur[1]:
            sid, key, look = cur
            prev = {sl: self.worn.get(sl) for sl in look}
            self.worn.update(look)
            self.season = {"key": key, "prev": prev, "look": dict(look)}
            self.refresh_cache()
            self.save_soon()
            if not quiet:
                self.sparkle(8)
            self.greet_season = sid
        elif not cur and st.get("prev"):
            look = st.get("look") or {}
            if all(self.worn.get(sl) == v for sl, v in look.items()):   # hâlâ kostümdeyse geri al
                self.worn.update(st["prev"])
                self.refresh_cache()
            self.season = {"key": st.get("key", "")}
            self.save_soon()

    # ============================================================ OYUN MODU
    def all_windows(self):
        ws = [self.root]
        ws += [p.win for p in self.props.values()]
        ws += [c.win for c in (self.frog, self.dog, self.ball, self.treat) if c]
        ws += [sp.win for sp in self.surprises]
        if self.speech:
            ws.append(self.speech.win)
        if self.bubble:
            ws.append(self.bubble.win)
        return ws

    def set_hidden(self, mode):
        if mode == self.hidden:
            return
        if mode:
            if self.bubble:
                self.bubble.close()
            if self.chaos:                                    # kaos sessizce biter, kıyafet geri
                self.worn.update(self.chaos["worn"])
                self.chaos = None
                self.refresh_cache()
            if self.speech:
                self.speech.destroy()
                self.speech = None
            self.dragging = False
            for w in self.all_windows():
                try:
                    w.withdraw()
                except tk.TclError:
                    pass
            self.hidden = mode
            if mode == "manual":
                self.make_tray()
            self.save_soon()
        else:
            if self.tray:
                self.tray.remove()
                self.tray = None
            self.hidden = None
            for w in self.all_windows():
                try:
                    w.deiconify()
                    w.wm_attributes("-topmost", True)
                except tk.TclError:
                    pass
            self._geo = None
            for o in list(self.props.values()) + [c for c in (self.frog, self.dog, self.ball, self.treat) if c]:
                o._geo = None
            for sp in self.surprises:
                sp._geo = None
            self._next_t = None
            self.chat("unhide", force=True, cooldown=0, gap=False, dur=70)
            if not (self.perch or self.climbing):
                self.start("wave", 45)

    def make_tray(self):
        tip = pick_line(self.prefs["lang"], "hide_tip")
        if IS_WIN:
            try:
                import tempfile
                ico = write_ico(os.path.join(tempfile.gettempdir(), "pocket_karolina_tray.ico"),
                                head_icon_grid(), PAL)
                self.tray = TrayIcon(self.root, ico, "Pocket Karolina")
                self.tray.balloon("Pocket Karolina", tip)
                return
            except Exception:
                self.log_error()
        self.tray = RestoreChip(self)

    def fullscreen_step(self):
        """Saniyede bir: tam ekran uygulama öndeyse saklan, çıkınca geri gel."""
        if not self.prefs["autohide"] or self.hidden == "manual" or self.dragging:
            return
        fs = fullscreen_app_active()
        if fs is None:
            return
        if fs and not self.hidden:
            self.set_hidden("auto")
        elif not fs and self.hidden == "auto":
            self.set_hidden(None)

    def poll_instance(self):
        """İkinci kez açılmaya çalışıldıysa (bat / kısayol): gizliyse geri gel."""
        sock = globals().get("INSTANCE_SOCK", [None])[0]
        if sock is None:
            return
        try:
            conn, _a = sock.accept()
        except (BlockingIOError, OSError):
            return
        try:
            conn.settimeout(0.3)
            msg = conn.recv(16)
        except OSError:
            msg = b""
        finally:
            conn.close()
        if msg.startswith(b"show") and self.hidden:
            self.set_hidden(None)

    def hidden_step(self):
        """Gizliyken: çizim yok, sadece arka plan işleri."""
        self.t += 1
        t = self.t
        if self.tray is not None and getattr(self.tray, "clicked", False):
            self.tray.clicked = False
            self.set_hidden(None)
            return
        if t % 15 == 0:
            self.poll_instance()
        if t % 30 == 0:
            self.stats_step()
            self.fullscreen_step()
        if self.remote and t % 6 == 0:
            self.remote.drain(self)
        if t % 240 == 0:
            self.publish_remote()
        if (self.dirty and t - self.last_save >= 90) or t - self.last_save >= 900:
            self.save()

    # ================================================================ KAOS
    def calm_worn(self):
        """Kaos sırasında / toparlanmadan önce kaydedilecek asıl kıyafet."""
        if self.chaos:
            return self.chaos["worn"]
        if self.chaos_fix:
            return self.chaos_fix["worn"]
        return self.worn

    def toggle_chaos(self):
        if self.chaos:
            self.stop_chaos(early=True)
        else:
            self.start_chaos()

    def start_chaos(self):
        if self.chaos or self.dragging:
            return False
        base = dict(self.calm_worn())
        self.chaos_fix = None
        self.close_bubble()
        self.end_ball(quiet=True)
        self.cancel_visit()
        if self.perch:
            self.leave_perch(hop=True, quiet=True)
        self.climb, self.climbing = None, False
        dur = random.randint(*CHAOS_TICKS)
        k = random.randint(*CHAOS_FOLDERS)
        when = [int(dur * (0.2 + 0.6 * i / max(1, k - 1))) + random.randint(-25, 25) for i in range(k)]
        self.chaos = {"t": 0, "dur": dur, "worn": base, "folders": sorted(when), "opened": 0,
                      "next_spree": random.randint(90, 160), "spree": None,
                      "next_pal": random.randint(30, 70), "knocked": {}, "bonk": -99}
        self.chat("chaos_start", force=True, cooldown=0, gap=False, dur=80)
        for dx in (-20, 0, 20):
            self.spawn("txt", PADX + 16 * SCALE + dx, PADT + 2 * SCALE, text="!",
                       col="#e63946", size=18, life=24)
        self.start("jump")
        self.publish_remote()
        return True

    def stop_chaos(self, early=False):
        c = self.chaos
        if not c:
            return
        self.chaos = None
        if isinstance(self.bubble, StylePanel):
            self.bubble.close()
        self.chaos_fix = {"t": self.t + random.randint(240, 360), "worn": c["worn"]}
        self.bump(mood=6, energy=-8 if early else -15)
        self.vx = 0.0
        if early:
            self.chat("chaos_stop", force=True, cooldown=0, gap=False)
            self.start("flop", 60)
        else:
            self.chat("chaos_end", force=True, cooldown=0, gap=False)
            self.start("flop")
        self.save_soon()
        self.publish_remote()

    def chaos_next(self):
        r = random.random()
        if r < 0.58:
            self.start("run", random.randint(25, 70))
        elif r < 0.74:
            self.start("jump")
        elif r < 0.84:
            self.start("spin")
        else:
            self.start("emote", 45)
            self.emote = random.choice(["dizzy", "laugh", "super", "wow", "shock"])

    def chaos_bonk(self):
        c = self.chaos
        if self.t - c["bonk"] < 20:
            return
        c["bonk"] = self.t
        self.spawn("txt", PADX + 16 * SCALE, PADT + 2 * SCALE, text="BONK!", col="#e63946",
                   size=14, life=22)
        if not self.perch:
            self.vx, self.vy = 0.0, -6.0
            self.y -= 1

    def chaos_folder(self):
        path = downloads_dir()
        if path and open_folder(path):
            self.chaos["opened"] += 1
        self.chat("chaos_oops", force=True, cooldown=0, gap=False, dur=70)
        self.start("emote", 50)
        self.emote = "shock"

    def chaos_click(self, panel):
        """Kendi stil panelinde rastgele sekme + kıyafet 'tıklar' (yalnızca uygulamanın içi)."""
        panel.tab = random.choice([0, 0, 1, 2, 2, 3])
        tiles = [i for i, (k, _iid, _l) in enumerate(panel.tiles()) if k == "worn"]
        if not tiles:
            return
        i = random.choice(tiles)
        panel.hover = i
        iid = panel.tiles()[i][1]
        self.worn[SLOT_OF[iid]] = iid
        self.react_t = 12
        self.sparkle(2)
        self.spawn("txt", PADX + 26 * SCALE, PADT + 4 * SCALE, text="click!", col="#ff5c8a",
                   size=9, life=14)
        self.refresh_cache()

    def chaos_step(self):
        c = self.chaos
        if self.dragging:
            return
        c["t"] += 1
        t = c["t"]
        if t >= c["dur"]:
            self.stop_chaos()
            return
        busy = self.bubble is not None or self.y < self.floor or self.vy < 0
        if c["folders"] and t >= c["folders"][0] and not busy:
            c["folders"].pop(0)
            self.chaos_folder()
            return
        sp = c["spree"]
        if sp is None:
            if t >= c["next_spree"] and not busy and t < c["dur"] - 90:
                self.open_style()
                if isinstance(self.bubble, StylePanel):
                    c["spree"] = {"n": random.randint(4, 7), "next": 10, "until": t + 200}
                else:
                    c["next_spree"] = t + 120
        else:
            b = self.bubble
            if not isinstance(b, StylePanel) or b.state == "closing":
                c["spree"] = None
                c["next_spree"] = t + random.randint(160, 280)
            elif t > sp["until"]:                            # panel takıldıysa bekleme
                b.close()
            elif b.state == "idle":
                sp["next"] -= 1
                if sp["next"] <= 0:
                    if sp["n"] <= 0:
                        b.close()
                    else:
                        sp["n"] -= 1
                        sp["next"] = random.randint(9, 15)
                        self.chaos_click(b)
        if t >= c["next_pal"]:
            c["next_pal"] = t + random.randint(35, 80)
            for f in (self.frog, self.dog):
                if f and random.random() < 0.7:
                    f.poke()
            if self.dog and random.random() < 0.5:
                self.dog.bark(random.choice(["HAU!", "HAU HAU!"]), 30)
        if self.action == "run" and random.random() < 0.012:
            self.dir = -self.dir                             # ani fren / geri dönüş
        if abs(self.vx) > 3 and not self.perch:
            cx = self.x + self.cw / 2
            for p in list(self.props.values()):
                if (not p.hidden and p.x - 6 <= cx <= p.x + p.pw + 6 and
                        t - c["knocked"].get(p.kind, -999) > 45):
                    c["knocked"][p.kind] = t
                    p.knock(1 if self.vx > 0 else -1)
                    self.spawn("txt", PADX + 16 * SCALE, PADT + 4 * SCALE,
                               text=random.choice(["BAM!", "oops", "CRASH!"]), col="#e63946",
                               size=12, life=20)

    # ================================================================ KÖŞE
    def arrange_corner(self):
        """Tüm masa objelerini ekranın sol / sağ alt köşesine düzenler (her tıkta taraf değişir)."""
        if not self.props:
            return
        side = self.prefs["corner"]
        self.cancel_visit()
        if side == "left":
            cur = 10
            for k in PROP_ORDER:
                p = self.props.get(k)
                if p:
                    p.x = float(cur)
                    cur += p.pw + 8
        else:
            cur = self.sw - 10
            for k in PROP_ORDER:
                p = self.props.get(k)
                if p:
                    p.x = float(cur - p.pw)
                    cur -= p.pw + 8
        self.prefs["corner"] = "right" if side == "left" else "left"
        self.sparkle(4)
        self.save_soon()

    # =============================================================== PARÇACIK
    def spawn(self, kind, x, y, text=None, col=None, size=None, life=None):
        P = self.particles
        if kind == "heart":
            P.append(dict(k="t", ch="♥", x=x, y=y, vx=random.uniform(-.8, .8),
                          vy=-1.4, life=42, size=random.randint(11, 16),
                          col=random.choice(["#ff5c8a", "#ff8fb1", "#ff3d7f"]), wob=True))
        elif kind == "note":
            P.append(dict(k="t", ch=random.choice("♪♫"), x=x, y=y,
                          vx=random.uniform(-.6, .6), vy=-1.1, life=38,
                          size=random.randint(12, 16),
                          col=random.choice(["#7a5cff", "#2fa8ff", "#ff9f1c"]), wob=True))
        elif kind == "z":
            P.append(dict(k="t", ch=random.choice("zZ"), x=x, y=y, vx=.5, vy=-.7,
                          life=55, size=random.randint(10, 15), col="#6f7cff", wob=True))
        elif kind == "spark":
            P.append(dict(k="t", ch="✦", x=x + random.uniform(-16, 16),
                          y=y + random.uniform(-10, 10), vx=random.uniform(-.4, .4),
                          vy=random.uniform(-.9, -.2), life=28,
                          size=random.randint(10, 16),
                          col=random.choice(["#ffd23f", "#fff2a8", "#ffb3c7"]), wob=False))
        elif kind == "txt":
            P.append(dict(k="t", ch=text, x=x, y=y, vx=0, vy=-.4, life=life or 16,
                          size=size or 18, col=col or "#ff5c8a", wob=False))
        elif kind == "tear":
            for d in (-1, 1):
                P.append(dict(k="r", x=x + d * 7, y=y, vx=d * random.uniform(.2, .6),
                              vy=random.uniform(0, .5), life=22, size=2, col="#7cc4ff",
                              wob=False))
        elif kind == "rainbow":
            P.append(dict(k="t", ch="✦", x=x + random.uniform(-26, 26),
                          y=y + random.uniform(-18, 14), vx=random.uniform(-.3, .3),
                          vy=random.uniform(-.8, -.1), life=34, size=random.randint(10, 17),
                          col=random.choice(["#ff4f6b", "#ff9f1c", "#ffd23f", "#4fd16b",
                                             "#3aa0ff", "#a366ff"]), wob=False))
        elif kind == "dust":
            for d in (-1, 1):
                P.append(dict(k="r", x=x, y=y, vx=d * random.uniform(.8, 1.8),
                              vy=random.uniform(-.8, -.2), life=14,
                              size=random.randint(3, 5), col="#e8dccf", wob=False))

    def update_particles(self):
        cv = self.cv
        if not self.particles:
            if self._fx_on:
                cv.delete("fx")
                self._fx_on = False
            return
        self._fx_on = True
        cv.delete("fx")
        alive = []
        for p in self.particles:
            p["life"] -= 1
            if p["life"] <= 0:
                continue
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            if p["wob"]:
                p["x"] += math.sin(p["life"] * 0.35) * 0.7
            if p["k"] == "r":
                p["vy"] += 0.08
            alive.append(p)
            fade = min(1.0, p["life"] / 10)
            if p["k"] == "t":                               # yazı değil piksel glif
                cv.create_image(p["x"], p["y"], tags="fx",
                                image=text_image(p["ch"], p["col"],
                                                 glyph_scale(p["size"], p["life"])))
            else:
                s = max(1, p["size"] * fade)
                cv.create_rectangle(p["x"] - s, p["y"] - s, p["x"] + s, p["y"] + s,
                                    fill=p["col"], outline="", tags="fx")
        self.particles = alive[-50:]

    # ======================================================== BALON
    def draw_balloon(self):
        cv = self.cv
        if self.eff_worn().get("held") != "balloon":
            if self._balloon_on:
                cv.delete("balloon")
                self._balloon_on = False
            return
        self._balloon_on = True
        cv.delete("balloon")
        hx = PADX + (8 if self.cur_flip else 23) * SCALE
        hy = PADT + 27 * SCALE
        bx = hx + 7 * math.sin(self.t * 0.07)
        by = 19 + 3 * math.sin(self.t * 0.05)
        cv.create_line(hx, hy, bx, by + 12, fill="#6d6d7a", width=1, tags="balloon")
        cv.create_oval(bx - 11, by - 12, bx + 11, by + 12, fill="#ff5c8a", outline="#3a1f1c",
                       width=2, tags="balloon")
        cv.create_oval(bx - 6, by - 8, bx - 2, by - 3, fill="#ffd0de", outline="", tags="balloon")
        cv.create_polygon(bx - 3, by + 12, bx + 3, by + 12, bx, by + 16, fill="#3a1f1c",
                          outline="", tags="balloon")

    # ===================================================================== POZLAR
    def eyes(self, base="normal"):
        if base != "normal":
            return base
        if self.blink_t > 0:
            return "closed"
        if self.react_t > 0:
            return "happy"
        return "annoyed" if self.stats["mood"] < 28 else "normal"

    def mouth(self):
        return "grin" if self.stats["mood"] > 80 else "smile"

    def do_emote(self, eid, user=False):
        """Bir emote oynatır (panelden ya da telefondan)."""
        e = EMOTES.get(eid)
        if not e:
            return
        if self.dragging or self.climbing:
            return
        if not user and (self.speech or self.visit or self.perch):   # kendiliğinden: kimseyi bölme
            return
        if self.visit:
            self.cancel_visit()
        if self.speech:
            self.speech.destroy()
            self.speech = None
        self.start("emote", e["dur"])
        self.emote = eid
        if user:
            self.love(aff=2, mood=3)
        self.chat("e_" + eid, force=user, cooldown=0, dur=70, gap=False)
        self.save_soon()

    def emote_pose(self):
        e = EMOTES.get(self.emote) or EMOTES["love"]
        s, t, eid = self.a_t, self.t, self.emote
        cx, hy = PADX + 16 * SCALE, PADT + 8 * SCALE
        eyes, mouth = e["eyes"], e["mouth"]
        sp = self.spawn
        if eid == "love":
            if s % 14 == 0:
                sp("heart", cx, hy)
            k = (t // 8) % 2
            return K(eyes=eyes, mouth="smile" if (t // 20) % 2 else "kiss", al="u", ar="u",
                     ald=-k, ard=-(1 - k), hdy=(t // 10) % 2)
        if eid == "wow":
            if s % 9 == 0:
                sp("spark", cx, hy)
            return K(eyes=eyes, mouth=mouth if s > 8 else "grin", al="u", ar="u",
                     bdy=-2 if s < 6 else 0, hdy=(t // 6) % 2)
        if eid == "super":
            if s % 5 == 0:
                sp("rainbow", cx, hy + 6 * SCALE)
            k = (t // 6) % 2
            return K(eyes=eyes, mouth=mouth, al="u", ar="u", ald=-k, ard=-(1 - k),
                     bdy=-(k + 1), hdy=k, ll=k, lr=1 - k)
        if eid == "wink":
            if s == 14:
                sp("spark", cx + 10 * SCALE, hy)
                sp("heart", cx + 8 * SCALE, hy)
            return K(eyes="normal" if s < 12 else eyes, mouth=mouth, ar="u" if s > 28 else "d",
                     arx=(t // 4) % 2 if s > 28 else 0, hdx=1 if 12 <= s < 60 else 0)
        if eid == "shy":
            if s % 26 == 0:
                sp("heart", cx, hy)
            return K(eyes=eyes, mouth=mouth, al="u", ar="u", alx=4, arx=-4, ald=1, ard=1,
                     hdx=-1 if (t // 14) % 2 else 0, hdy=1)
        if eid == "laugh":
            if s % 18 == 0:
                sp("txt", cx + 18 * SCALE, hy - 6, text="HA", col="#ff8a3d", size=14, life=16)
            f = (t // 3) % 2
            return K(eyes=eyes, mouth=mouth, hdy=f, bdy=f, al="u" if s % 30 < 15 else "d",
                     ald=-f, hdx=(t // 3) % 3 - 1)
        if eid == "cry":
            if s % 7 == 0:
                sp("tear", cx, hy + 6 * SCALE)
            return K(eyes=eyes, mouth=mouth, al="u", ar="u", alx=3, arx=-3, ald=2, ard=2,
                     hdy=1 + (t // 5) % 2, bdy=1)
        if eid == "angry":
            if s % 22 == 0:
                sp("txt", cx + 14 * SCALE, hy - 8, text="✖", col="#e63946", size=14, life=18)
            f = (t // 2) % 2
            return K(eyes=eyes, mouth=mouth, hdx=f * 2 - 1 if s % 40 < 24 else 0,
                     ll=(t // 6) % 2, lr=1 - (t // 6) % 2, bdy=0)
        if eid == "dizzy":
            ang = t * 0.28
            if s % 5 == 0:
                sp("txt", cx + math.cos(ang) * 22, hy - 14 + math.sin(ang) * 6, text="✦",
                   col="#ffd23f", size=10, life=10)
            return K(eyes=eyes, mouth=mouth, hdx=(0, 1, 0, -1)[(t // 8) % 4],
                     bdy=(t // 16) % 2, ll=(t // 10) % 2)
        if eid == "shock":
            if s == 2:
                sp("txt", cx, hy - 10, text="!?", col="#e63946", size=20, life=30)
            return K(eyes=eyes, mouth=mouth, al="u", ar="u", bdy=-2 if s < 8 else 0,
                     hdy=-1 if s < 40 else 0, hdx=(t // 3) % 2 if s > 10 else 0)
        return K(eyes=eyes, mouth=mouth)

    def moving_pose(self, run):
        T = RUN if run else WALK
        p = int(self.phase) % 8
        ll, lr = T["ll"][p], T["lr"][p]
        return K(hdx=T["hx"][p], bdy=T["bob"][p], eyes=self.eyes(),
                 mouth="grin" if run else self.mouth(),
                 ald=-lr, ard=-ll, ll=ll, lr=lr,
                 ldx=1 if ll else 0, rdx=1 if lr else 0)

    def action_pose(self, a):
        t = self.t
        if self.rps_pose and a not in ("sleep", "visit"):
            k = self.rps_pose()
            if k is not None:
                return k
        if self.cheer_t > 0 and a not in ("sleep", "visit"):         # Lila topu getirdi: sevinç
            self.cheer_t -= 1
            b = (t // 8) % 2
            return K(eyes="happy", mouth="grin", al="u", ar="u", ald=-b, ard=-(1 - b),
                     hdy=(t // 6) % 2)
        if a == "emote":
            return self.emote_pose()
        if a == "sleep":
            return K(bdy=3, legs="sit", eyes="closed", hdy=(t // 28) % 2)
        if a == "flop":                                     # kaostan sonra yığılır
            s = self.a_t
            if s < 8:
                return K(bdy=min(3, s // 2), eyes="dizzy", mouth="open", al="u", ar="u")
            if s % 9 == 0 and s < 70:
                self.spawn("txt", PADX + (16 + 6 * math.cos(s)) * SCALE, PADT + 6 * SCALE,
                           text="✦", col="#ffd23f", size=10, life=12)
            return K(bdy=3, legs="sit", eyes="dizzy" if s < 70 else "closed", mouth="wavy",
                     hdy=1, hdx=(0, 1, 0, -1)[(t // 10) % 4] if s < 70 else 0)
        if a == "sit":
            return K(bdy=3, legs="sit", eyes=self.eyes(), hdy=(t // 22) % 2,
                     mouth=self.mouth())
        if a == "dangle":                                   # tünekte ayak sallama
            k = (t // 10) % 2
            return K(bdy=3, legs="sit", ll=k, lr=1 - k, eyes=self.eyes(), mouth=self.mouth(),
                     hdy=(t // 30) % 2)
        if a == "look":
            return K(hdx=(0, -1, 0, 1)[(t // 18) % 4], hdy=(t // 20) % 2, eyes=self.eyes(),
                     mouth=self.mouth())
        if a == "stretch":                                  # kollar yukarı, gözler kapalı, esneme
            s = self.a_t
            if s < 12:
                return K(al="u", ar="u", eyes="closed", mouth="open", hdy=-(s // 6))
            if s < 44:
                sh = (t // 2) % 2
                return K(al="u", ar="u", ald=-1, ard=-1, alx=sh, arx=-sh, bdy=-1, hdy=-1,
                         eyes="closed", mouth="open")
            return K(eyes="happy", mouth="smile", hdy=(t // 8) % 2)
        if a == "dance":
            d = DANCE[(t // 6) % 4]
            return K(eyes="happy", mouth="grin", alx=(t // 3) % 2, arx=-((t // 3) % 2), **d)
        if a == "wave":
            return K(eyes="happy", mouth="grin", ar="u", arx=(t // 4) % 2,
                     ard=-((t // 4) % 2), hdy=(t // 10) % 2)
        if a == "kiss":
            return K(eyes="happy", mouth="kiss", ar="u", hdy=(t // 12) % 2, hdx=(t // 12) % 2)
        if a == "hug":
            k = (t // 8) % 2
            return K(eyes="happy", mouth="grin", al="u", ar="u", ald=-k, ard=-(1 - k),
                     hdy=(t // 10) % 2)
        if a == "bored":                                    # ayak tıklatma, sıkkın bakış
            return K(eyes=self.eyes("annoyed"), mouth="smile", ll=(t // 10) % 2,
                     hdx=(t // 50) % 2, hdy=(t // 25) % 2)
        if a == "sulk":                                     # küs: yan dönüp somurtuyor
            return K(bdy=3, legs="sit", eyes="annoyed", mouth="kiss",
                     hdx=-1 if (t // 45) % 2 else 0)
        if a == "yawn":
            return K(eyes="closed", mouth="open", al="u", ar="u", ald=-1, ard=-1,
                     hdy=(t // 8) % 2)
        if a == "selfie":
            s = self.a_t
            if s < 12:
                return K(ar="u", ph=1, eyes=self.eyes(), mouth="smile")
            if s < 40:
                return K(ar="u", ph=1, al="u", hdx=1, eyes="happy", mouth="grin")
            if s < 52:
                return K(ar="u", ph=1, al="u", hdx=1, eyes="wide", mouth="open")
            return K(eyes="happy", mouth="grin", hdy=(t // 6) % 2)
        return K(eyes=self.eyes(), mouth=self.mouth(), hdy=(t // 20) % 2)   # idle

    # ===================================================================== SELFIE
    def flash(self):
        if not self.prefs["flash"]:
            return
        try:
            w = tk.Toplevel(self.root)
            w.overrideredirect(True)
            w.wm_attributes("-topmost", True)
            w.configure(bg="white")
            w.geometry(f"{self.sw}x{self.sh}+0+0")
            state = {"a": 0.75}
            w.attributes("-alpha", state["a"])

            def fade():
                state["a"] -= 0.12
                if state["a"] <= 0:
                    w.destroy()
                    return
                try:
                    w.attributes("-alpha", state["a"])
                except tk.TclError:
                    pass
                w.after(28, fade)
            w.after(40, fade)
        except tk.TclError:
            pass

    def make_photo(self):
        """Selfie'yi polaroid olarak üretir ve diske kaydeder."""
        key = K(eyes="happy", mouth="grin", al="u", ar="u")
        key = key[:16] + self.eq_tuple() + key[21:]
        grid = compose(key)
        PW, PH = 40, 46
        p = tk.PhotoImage(width=PW, height=PH)
        p.put("#fffdf8", to=(0, 0, PW, PH))
        for y in range(32):                                  # gün batımı arka planı
            c = _lerp("#ffb3c7", "#ffd9a0", y / 16) if y < 16 else _lerp("#ffd9a0", "#9ad4ff", (y - 16) / 16)
            p.put(c, to=(4, 4 + y, 36, 5 + y))
        p.put("#7fc97f", to=(4, 4 + 30, 36, 4 + 32))
        for _ in range(9):
            p.put("#ffffff", (4 + random.randint(1, 30), 4 + random.randint(1, 14)))
        for y, row in enumerate(grid):
            for x, ch in enumerate(row):
                if ch in PAL:
                    p.put(PAL[ch], (4 + x, 4 + y))
        big = p.zoom(6)
        path = None
        try:
            folder = os.path.join(os.path.expanduser("~"), "Pictures", "PocketKarolina")
            os.makedirs(folder, exist_ok=True)
            path = os.path.join(folder, time.strftime("selfie_%Y%m%d_%H%M%S.png"))
            big.write(path, format="png")
        except (OSError, tk.TclError):
            path = None
        return big, path

    def take_photo(self):
        self.photo_done = True
        self.counters["selfies"] += 1
        self.bump(mood=3)
        self.flash()
        self.spawn("txt", PADX + 27 * SCALE, PADT + 2 * SCALE, text="CLICK!",
                   col="#ffffff", size=16, life=18)
        self.chat("selfie", cooldown=300)
        self.save_soon()
        self.root.after(260, self._show_polaroid)

    def _show_polaroid(self):
        big, path = self.make_photo()
        Polaroid(self, big, path)

    # ================================================================== ZAMANLAYICILAR
    def timers(self):
        t = self.t
        if t % 30 == 5:
            self.poll_instance()
        if t % 30 == 15 and IS_WIN:
            self.fullscreen_step()
            if self.hidden:
                return
        if t % 900 == 450:
            self.season_check()
        if getattr(self, "greet_season", None) and t > 90 and not self.speech:
            self.chat("season_" + self.greet_season, force=True, cooldown=0, gap=False, dur=130)
            self.greet_season = None
        if not self.dragging:
            self.surprise_step()
        if self.chaos:
            self.chaos_step()
        elif self.chaos_fix and t >= self.chaos_fix["t"] and not (self.dragging or self.bubble):
            self.worn.update(self.chaos_fix["worn"])
            self.chaos_fix = None
            self.sparkle(8)
            self.refresh_cache()
            self.chat("chaos_fixed", cooldown=0, gap=False)
            self.save_soon()
        if t % 30 == 0:
            self.stats_step()
        if self.greet_t and t >= self.greet_t:
            self.greet_t = 0
            if self.first_run:                                # ilk açılış: nasıl kullanılacağını söyle
                self.first_run = False
                self.say(pick_line(self.prefs["lang"], "intro"), 330, "love")
            else:
                self.chat("welcome_long" if self.away_hours > 3 else "welcome", force=True)
        if t % 150 == 0:
            self.check_due()
        if self.remote and t % 6 == 0:
            self.remote.drain(self)
        if t % 240 == 0:
            self.publish_remote()
        if t >= self.next_remind:
            self.do_remind()
        if t % 90 == 0 and not self.menu_open:               # ortam replikleri
            st = self.stats
            if st["affection"] < 40:
                self.chat("neglect", cooldown=1800)
            elif st["energy"] < 25:
                self.chat("sleepy", cooldown=1500)
            elif st["mood"] > 85:
                self.chat("happy", cooldown=2400)
        if (self.dirty and t - self.last_save >= 90) or t - self.last_save >= 900:
            self.save()
        if self.speech and not self.speech.update():
            self.speech.destroy()
            self.speech = None

    # ================================================================== ANA DÖNGÜ
    def log_error(self, tb=None):
        """Hatayı pet_error.log dosyasına yazar (uygulama sessizce kapanmasın / donmasın)."""
        import traceback
        tb = tb or traceback.format_exc()
        print(tb, file=sys.stderr)
        try:
            path = os.path.join(os.path.dirname(os.path.abspath(self.save_path)), "pet_error.log")
            if os.path.exists(path) and os.path.getsize(path) > 200000:
                os.remove(path)
            with open(path, "a", encoding="utf-8") as f:
                f.write("--- %s  v11.1  py%s  %s\n%s\n" % (datetime.datetime.now().isoformat(" ", "seconds"),
                        sys.version.split()[0], sys.platform, tb))
        except OSError:
            pass

    def tick(self):
        """Kare döngüsü: tek bir hata tüm uygulamayı dondurmasın."""
        if self.hidden:
            try:
                self.hidden_step()
            except Exception:
                self.log_error()
            self._next_t = None
            self.root.after(TICK_MS, self.tick)
            return
        try:
            self._tick()
            self.err_streak = 0
        except Exception:
            self.err_streak = getattr(self, "err_streak", 0) + 1
            if self.err_streak <= 3 or self.err_streak % 300 == 0:
                self.log_error()
            if self.err_streak == 5:
                try:
                    self.end_ball(quiet=True)
                except Exception:
                    pass
                self.rps_pose, self.cheer_t = None, 0
            self.schedule()

    def _tick(self):
        self.t += 1
        t = self.t
        self.timers()
        if self.react_t > 0:
            self.react_t -= 1
        if self.blink_t > 0:
            self.blink_t -= 1
        elif t >= self.next_blink:
            self.blink_t = 4
            self.next_blink = t + random.randint(60, 170)

        flip = self.dir < 0
        feet_x = PADX + 16 * SCALE
        feet_y = PADT + 30 * SCALE
        act = self.action
        key = K()
        smooth = False

        if self.dragging:
            key = self.held_step()
        elif (self.y < self.floor or self.vy < 0) and not self.climbing:
            if self.perch:                                   # tünekten düşüyor
                self.perch = self.perch_plat = None
                self.floor = self.ground
            prev_y = self.y
            self.vy += 1.0
            self.y += self.vy
            self.x += self.vx
            self.vx *= 0.985
            lo, hi = -PADX + 4, self.sw - self.cw + PADX - 4
            if self.x < lo:
                self.x, self.vx = lo, abs(self.vx) * 0.6
            elif self.x > hi:
                self.x, self.vx = hi, -abs(self.vx) * 0.6
            if self.y < 0 and self.vy < 0:
                self.y, self.vy = 0.0, abs(self.vy) * 0.35
            land = self.find_landing(prev_y)
            if land:                                         # pencere kenarına kondu
                py, p = land
                impact = self.vy
                self.y, self.vy = py, 0.0
                self.set_perch(p, py)
                self.on_land(impact)
            elif self.y >= self.ground:
                impact = self.vy
                self.y, self.vy, self.floor = self.ground, 0.0, self.ground
                self.on_land(impact)
            if act in ("jump", "spin"):
                key = K(bdy=-1, al="u", ar="u", eyes="happy", mouth="grin", ll=2, lr=2)
                if act == "spin":
                    flip = (t // 3) % 2 == 0
            else:
                key = K(al="u", ar="u", eyes="wide", mouth="open", ll=1, lr=1)
        elif self.land_t > 0:
            self.land_t -= 1
            key = K(bdy=1, eyes="happy", mouth="smile")
            if self.land_t == 0 and act in ("jump", "spin"):
                self.next_action()
        else:
            if self.perch:
                self.track_perch()
            elif not self.climbing:
                self.floor = self.y = self.ground
            if self.vy > 0:
                self.vy = 0.0
            self.a_t += 1
            if self.menu_open and act != "visit":
                act = "idle"
            elif act == "climb" and not self.climb:
                self.next_action()
                act = self.action
            elif act == "visit" and not self.visit:
                self.next_action()
                act = self.action
            elif (self.a_t > self.a_dur and not self.leaving and
                  act not in ("jump", "spin", "climb", "visit")):
                self.next_action()
                act = self.action
            smooth = act not in ("visit", "climb", "jump", "spin")

            if act in ("jump", "spin") and not self.menu_open:
                if self.a_t < 6:
                    key = K(bdy=1)
                    self.vx *= 0.8
                else:
                    self.vy = -13.0
                    self.y -= 1
                    self.vx = self.dir * (2.5 if act == "jump" else 1.5)
                    self.show(K(bdy=-1, al="u", ar="u", eyes="happy", mouth="grin", ll=2, lr=2), flip)
                    self.place()
                    self.schedule()
                    return
            elif act == "climb" and self.climb and not self.menu_open:
                res = self.climb_step()
                if res is not None:
                    key, flip = res
            elif act == "visit" and self.visit:
                res = self.visit_step()
                if res is not None:
                    key, flip = res
            else:
                speed = {"walk": 2.4, "run": 9.0 if self.chaos else 6.2}.get(act, 0.0)
                if act == "walk":                            # yorgun karakter yavaş yürür
                    speed *= 0.55 + 0.45 * self.stats["energy"] / 100.0
                self.vx += (self.dir * speed - self.vx) * 0.14
                if speed == 0:
                    self.vx *= 0.86
                self.x += self.vx
                lo, hi = -PADX + 4, self.sw - self.cw + PADX - 4
                if self.x < lo:
                    self.x, self.dir = lo, 1
                    if self.chaos:
                        self.chaos_bonk()
                elif self.x > hi:
                    self.x, self.dir = hi, -1
                    if self.chaos:
                        self.chaos_bonk()
                if self.perch and self.perch_plat:           # tünek kenarında dön / aşağı atla
                    p = self.perch_plat
                    cxp = self.x + self.cw / 2
                    if cxp < p["x1"] + 14 or cxp > p["x2"] - 14:
                        if self.leaving or (speed > 0 and random.random() < 0.4):
                            self.step_off()
                        else:
                            left = cxp < p["x1"] + 14
                            self.x = (p["x1"] + 14 if left else p["x2"] - 14) - self.cw / 2
                            self.dir, self.vx = (1 if left else -1), 0.0
                if abs(self.vx) > 0.2:
                    self.phase += abs(self.vx) * (0.10 if abs(self.vx) > 4 else 0.14)
                if abs(self.vx) > 0.7:
                    key = self.moving_pose(abs(self.vx) > 4)
                    flip = self.vx < 0
                    self.face_left = flip
                else:
                    key = self.action_pose(act)
                    if act == "dance":
                        flip = (t // 24) % 2 == 0

            # efektler
            if act == "sleep" and t % 26 == 0:
                self.spawn("z", PADX + 22 * SCALE, PADT + 12 * SCALE)
            if act == "dance" and t % 9 == 0:
                self.spawn("note", PADX + random.choice([2, 28]) * SCALE, PADT + 10 * SCALE)
            if act in ("kiss", "hug") and t % 8 == 0:
                self.spawn("heart", PADX + (16 + 2 * self.dir) * SCALE, PADT + 18 * SCALE)
            if act == "sulk" and t % 70 == 0:
                self.spawn("txt", PADX + 24 * SCALE, PADT + 10 * SCALE, text="…",
                           col="#6d6d7a", size=16, life=30)
            if act == "bored" and t % 80 == 0:
                self.spawn("txt", PADX + 22 * SCALE, PADT + 12 * SCALE, text="~",
                           col="#9aa3b2", size=16, life=26)
            if act == "yawn" and t % 20 == 0:
                self.spawn("z", PADX + 22 * SCALE, PADT + 12 * SCALE)
            if self.eff_worn().get("held") == "coffee" and t % 26 == 0:
                self.spawn("txt", PADX + (5 if self.cur_flip else 28) * SCALE,
                           PADT + 21 * SCALE, text="~", col="#cfd6e4", size=9, life=22)
            if act == "selfie":
                if self.a_t in (14, 22, 30):
                    self.spawn("txt", PADX + 27 * SCALE, PADT + 2 * SCALE,
                               text=str(3 - (self.a_t - 14) // 8), col="#ff5c8a",
                               size=20, life=14)
                if self.a_t >= 38 and not self.photo_done:
                    self.take_photo()

        key = self.smooth_posture(key, smooth)
        if smooth:
            key = self.apply_gaze(key, flip, act)
        self.show(key, flip)
        off = 6 if (self.perch and key[11] == "sit") else 0    # kenara oturunca biraz çök
        self.update_particles()
        self.draw_balloon()
        self.place(off)
        for friend in (self.frog, self.dog):
            if friend:
                friend.update()
        for p in list(self.props.values()):
            p.update()
        if self.ball:
            self.ball.update()
            self.ball_game_step()
        if self.treat:
            self.treat.update()
        self.schedule()

    def schedule(self):
        """Sapma telafili kare zamanlayıcı: işlem süresi kadar erken tetiklenir, takılırsa yeniden senkronlar."""
        now = time.perf_counter()
        if self._next_t is None:
            self._next_t = now
        self._next_t += TICK_MS / 1000.0
        if self._next_t < now - 0.12:
            self._next_t = now
        self.root.after(max(1, int((self._next_t - now) * 1000)), self.tick)

    def smooth_posture(self, key, active):
        """Ayaktan oturmaya / oturmadan kalkmaya 3 karelik yumuşak geçiş."""
        target = 1.0 if (active and key[11] == "sit") else 0.0
        if not active:
            self.sit_prog = 0.0
            return key
        if self.sit_prog < target:
            self.sit_prog = min(target, self.sit_prog + 0.2)
        elif self.sit_prog > target:
            self.sit_prog = max(target, self.sit_prog - 0.25)
        p = self.sit_prog
        if p <= 0.0 or p >= 1.0:
            return key
        k = list(key)
        k[2] = max(1, round(p * 3))                         # gövde yavaşça iner / kalkar
        k[11] = "sit" if p >= 0.5 else "stand"
        k[12] = k[13] = k[14] = k[15] = 0
        return tuple(k)

    def apply_gaze(self, key, flip, act):
        """Boştayken kafayı yakındaki imlece doğru hafifçe çevirir."""
        if act not in ("idle", "sit", "dangle", "bored") or key[0] != 0:
            return key
        if self.t % 4 == 0:
            try:
                dx = self.root.winfo_pointerx() - (self.x + self.cw / 2)
                dy = self.root.winfo_pointery() - (self.y + self.ch / 2)
                near = math.hypot(dx, dy) < 480 and abs(dx) > 70
                self.gaze = (1 if dx > 0 else -1) if near else 0
            except tk.TclError:
                self.gaze = 0
        if not self.gaze:
            return key
        k = list(key)
        k[0] = -self.gaze if flip else self.gaze            # ayna çevrilmişse yön ters
        return tuple(k)

    def run(self):
        self.root.mainloop()


INSTANCE_PORT = 47613
INSTANCE_SOCK = [None]          # ana kopyanın dinlediği yerel soket (ikinci açılış "show" yollar)


def claim_single_instance():
    """Aynı anda tek Pocket Karolina: yerel bir portu tutar. Zaten açıksa None döner."""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if IS_WIN:
            s.setsockopt(socket.SOL_SOCKET, getattr(socket, "SO_EXCLUSIVEADDRUSE", 4), 1)
        s.bind(("127.0.0.1", INSTANCE_PORT))
        s.listen(4)
        s.setblocking(False)
        INSTANCE_SOCK[0] = s
        return s
    except OSError:
        s.close()
        return None


if __name__ == "__main__":
    print("Pocket Karolina v14 | Python %s | %s" % (sys.version.split()[0], sys.platform))
    _instance = claim_single_instance()
    if _instance is None:
        print("Pocket Karolina is already running (brought her back to the screen).")
        try:
            import socket
            with socket.create_connection(("127.0.0.1", INSTANCE_PORT), timeout=1) as _c:
                _c.sendall(b"show")
        except OSError:
            pass
        sys.exit(0)
    try:
        Pet().run()
    except Exception:
        import traceback
        msg = traceback.format_exc()
        print(msg, file=sys.stderr)
        try:
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "pet_error.log"), "a",
                      encoding="utf-8") as f:
                f.write("--- startup py%s %s\n%s\n" % (sys.version.split()[0], sys.platform, msg))
        except OSError:
            pass
        try:
            from tkinter import messagebox
            messagebox.showerror("Pocket Karolina", "Could not start:\n\n" + msg[-900:] +
                                 "\n(also saved to pet_error.log)")
        except Exception:
            pass
        raise
