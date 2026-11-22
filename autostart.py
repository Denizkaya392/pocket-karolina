"""
Pocket Karolina: Windows açılınca kendiliğinden, konsol penceresi OLMADAN başlasın.

  install_autostart.bat    -> açılışa ekler ve pet'i hemen (penceresiz) başlatır
  uninstall_autostart.bat  -> açılıştan kaldırır

Nasıl çalışır: Başlangıç (Startup) klasörüne küçük bir PocketKarolina.vbs koyar. O dosya oturum
açılınca bu klasördeki en yeni pocket_karolina_v*.py dosyasını pythonw.exe ile (siyah pencere
açmadan) çalıştırır. Hata olursa pet_error.log dosyasına yazılır. Yönetici izni gerekmez.

Komutlar:  python autostart.py install | uninstall | status | run
"""
import os
import runpy
import subprocess
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "pet_error.log")
VBS_NAME = "PocketKarolina.vbs"


def newest_app():
    for prefix in ("pocket_karolina_v", "masaustu_pet_v"):
        names = sorted((n for n in os.listdir(HERE) if n.startswith(prefix) and n.endswith(".py")),
                       key=lambda n: [int(x) if x.isdigit() else 0 for x in
                                      "".join(c if c.isdigit() else " " for c in n).split()],
                       reverse=True)
        if names:
            return os.path.join(HERE, names[0])
    return None


def startup_dir():
    appdata = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Roaming")
    return os.path.join(appdata, "Microsoft", "Windows", "Start Menu", "Programs", "Startup")


def pythonw_path():
    exe = sys.executable or ""
    d = os.path.dirname(exe)
    for cand in (os.path.join(d, "pythonw.exe"), exe.replace("python.exe", "pythonw.exe")):
        if cand and os.path.basename(cand).lower() == "pythonw.exe" and os.path.isfile(cand):
            return cand
    import shutil
    return shutil.which("pyw.exe") or shutil.which("pythonw.exe") or "pythonw.exe"


def vbs_text(pyw, script):
    q = lambda s: s.replace('"', '""')
    return ('\' Pocket Karolina otomatik baslatma (autostart.py tarafindan olusturuldu)\r\n'
            'Set sh = CreateObject("WScript.Shell")\r\n'
            'sh.CurrentDirectory = "%s"\r\n'
            'sh.Run """%s"" ""%s"" run", 0, False\r\n') % (q(HERE), q(pyw), q(script))


def install():
    if not sys.platform.startswith("win"):
        print("Bu özellik sadece Windows için.")
        return 1
    if not newest_app():
        print("HATA: bu klasörde pocket_karolina_v*.py yok. Önce onu buraya koy.")
        return 1
    pyw = pythonw_path()
    sd = startup_dir()
    os.makedirs(sd, exist_ok=True)
    path = os.path.join(sd, VBS_NAME)
    with open(path, "w", encoding="utf-16") as f:          # wscript UTF-16'yı Türkçe yollarda da okur
        f.write(vbs_text(pyw, os.path.abspath(__file__)))
    print("Tamam! Windows her açıldığında Pocket Karolina kendiliğinden başlayacak.")
    print("Başlangıç dosyası:", path)
    print("Python:", pyw)
    try:
        subprocess.Popen(["wscript.exe", path])
        print("Şimdi de başlatıldı (siyah pencere olmadan).")
    except OSError as e:
        print("Şimdi başlatılamadı:", e)
    return 0


def uninstall():
    path = os.path.join(startup_dir(), VBS_NAME)
    if os.path.exists(path):
        os.remove(path)
        print("Kaldırıldı. Artık açılışta başlamayacak.")
    else:
        print("Zaten kurulu değil.")
    print("Açık olan pet'i kapatmak için: sağ tık > Quit.")
    return 0


def status():
    path = os.path.join(startup_dir(), VBS_NAME)
    print("Açılışta başlıyor:", "EVET" if os.path.exists(path) else "hayır")
    print("Açılacak dosya:", newest_app())
    return 0


def run():
    """Başlangıçta pythonw ile çağrılır: konsol yok, hata olursa log'a yaz."""
    os.chdir(HERE)
    try:
        target = newest_app()
        if not target:
            raise FileNotFoundError("pocket_karolina_v*.py bulunamadı: " + HERE)
        runpy.run_path(target, run_name="__main__")
    except SystemExit:
        pass
    except BaseException:
        try:
            with open(LOG, "a", encoding="utf-8") as f:
                f.write("--- autostart py%s\n%s\n" % (sys.version.split()[0], traceback.format_exc()))
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    sys.exit({"install": install, "uninstall": uninstall, "status": status, "run": run}.get(cmd, status)())
