"""
Pocket Karolina başlatıcı: uygulamayı çalıştırır, ne olursa olsun hatayı GÖSTERİR ve dosyaya yazar
(pencere sessizce kapanmaz). Kullanım:  python start_pocket_karolina.py
(ya da start_pocket_karolina.bat'a çift tık). Aynı klasördeki en yeni pocket_karolina_v*.py açılır.
"""
import faulthandler
import os
import runpy
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "pet_error.log")
target = None
for prefix in ("pocket_karolina_v", "masaustu_pet_v"):             # en yeni sürüm; eskiler yedek
    names = sorted((n for n in os.listdir(HERE) if n.startswith(prefix) and n.endswith(".py")),
                   key=lambda n: [int(x) if x.isdigit() else 0 for x in
                                  "".join(c if c.isdigit() else " " for c in n).split()],
                   reverse=True)
    if names:
        target = os.path.join(HERE, names[0])
        break
print("Python", sys.version)
print("Platform", sys.platform)
print("Başlatılıyor:", target)
try:
    faulthandler.enable(open(os.path.join(HERE, "pet_crash.log"), "a"))
except Exception:
    pass
try:
    if not target:
        raise FileNotFoundError("pocket_karolina_v*.py bu klasörde yok")
    import tkinter                                                   # tkinter var mı?
    print("tkinter", tkinter.TkVersion)
    runpy.run_path(target, run_name="__main__")
except SystemExit:
    raise
except BaseException:
    msg = traceback.format_exc()
    print("\n=== HATA ===\n" + msg)
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("--- launcher py%s %s\n%s\n" % (sys.version.split()[0], sys.platform, msg))
    except OSError:
        pass
    input("\nBu yazıyı bana gönder (pet_error.log dosyasına da yazıldı). Kapatmak için Enter...")
