# -*- coding: utf-8 -*-
"""
Medical AI Workstation - Engine Launcher
Port: 8081
Auto-managed: Environment, Dependencies, Port Cleanup, Model Loading, Health Polling, and Browser Launch.
"""
import os
import sys
import time
import socket
import urllib.request
import webbrowser
import subprocess

# 1. Force UTF-8 Console Output
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

# 2. Enable Windows ANSI Terminal Support & Set Window Title
try:
    import ctypes
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    kernel32.SetConsoleTitleW(f"Medical AI [8081] - منظومة رداك للتشخيص الشعاعي بالذكاء الاصطناعي (Radiology AI Workstation)")
except Exception:
    pass

PORT = 8081
URL = f"http://localhost:8081/"
HEALTH_URL = f"http://localhost:8081/health"
TITLE = "منظومة رداك للتشخيص الشعاعي بالذكاء الاصطناعي (Radiology AI Workstation)"
COLLEAGUE = "الزميل 1: تخصص الأشعة والتصوير المقطعي (Radiology Dark Theme)"
DESC = "واجهة داكنة مخصصة لغرف الأشعة والتحليل الدقيق للأنسجة والتكلسات"

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def free_port(target_port):
    """Kills any process currently listening on the target port."""
    try:
        res = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, errors="ignore")
        pids = set()
        for line in res.stdout.splitlines():
            if f":{target_port}" in line and "LISTENING" in line:
                parts = line.strip().split()
                if len(parts) >= 5:
                    try:
                        pids.add(int(parts[-1]))
                    except ValueError:
                        pass
        current_pid = os.getpid()
        for pid in pids:
            if pid > 0 and pid != current_pid:
                subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
    except Exception:
        pass

def check_and_install_dependencies():
    """Verifies that all required neural network & web libraries are installed."""
    try:
        import flask
        import flask_cors
        import tensorflow
        import PIL
        import numpy
        return True
    except ImportError as e:
        print(f"\n[!] تنبيه: إحدى مكتبات الذكاء الاصطناعي غير مثبتة في هذه البيئة ({e}).")
        print("[+] جاري تثبيت المكتبات تلقائياً من requirements.txt...")
        req_path = os.path.join(CURRENT_DIR, "requirements.txt")
        if os.path.exists(req_path):
            try:
                subprocess.run([sys.executable, "-m", "pip", "install", "-r", req_path], check=True)
                return True
            except Exception as install_err:
                print(f"[!] فشل تثبيت المكتبات: {install_err}")
                return False
        return False

def open_browser(target_url):
    """Opens default browser with fallbacks."""
    try:
        success = webbrowser.open(target_url, new=2)
        if not success:
            os.system(f'start "" "{target_url}"')
    except Exception:
        try:
            os.system(f'start "" "{target_url}"')
        except Exception:
            pass

def main():
    clear_screen()
    print("=" * 80)
    print(f"  {TITLE}")
    print(f"  {COLLEAGUE}")
    print(f"  {DESC}")
    print(f"  الرابط المخصص : {URL}")
    print("=" * 80)
    print()

    # Step 1: Port Cleanup
    print(f"[1/4] تنظيف وتحرير المنفذ {PORT} من أي عمليات أو جلسات سابقة...")
    free_port(PORT)
    time.sleep(0.5)

    # Step 2: Check Libraries
    print("[2/4] التحقق من حزم الذكاء الاصطناعي ومفسر بايثون...")
    check_and_install_dependencies()

    # Step 3: Spawn AI Server with log capture
    print(f"[3/4] إطلاق خادم الاستدلال الطبي app.py على المنفذ {PORT}...")
    app_py = os.path.join(CURRENT_DIR, "app.py")
    log_file_path = os.path.join(CURRENT_DIR, "server.log")
    
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["TF_ENABLE_ONEDNN_OPTS"] = "0"
    
    log_file = open(log_file_path, "w", encoding="utf-8")
    server_proc = subprocess.Popen(
        [sys.executable, app_py],
        cwd=CURRENT_DIR,
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT
    )

    # Step 4: Health Polling Loop
    print("[4/4] جاري تحميل أوزان النموذج (VGG16) في الذاكرة وفحص استجابة الخادم...")
    is_ready = False
    for sec in range(1, 46):
        if server_proc.poll() is not None:
            log_file.flush()
            with open(log_file_path, "r", encoding="utf-8", errors="ignore") as lf:
                err_text = lf.read()
            print(f"\n[!] تنبيه: توقف خادم بايثون بشكل غير متوقع برمز: {server_proc.returncode}")
            print("--- تفاصيل سجل الخادم ---")
            print(err_text[-1200:])
            print("-------------------------")
            break

        try:
            req = urllib.request.Request(HEALTH_URL, headers={"User-Agent": "MedicalAIHealthCheck/1.0"})
            with urllib.request.urlopen(req, timeout=1.2) as response:
                if response.status == 200:
                    is_ready = True
                    break
        except Exception:
            pass

        print(f"  ⏳ بانتظار اكتمال تحميل أوزان الشبكة العصبية (112 MB)... ({sec}/45 ثانية)", end="\r", flush=True)
        time.sleep(0.8)

    print() # New line after polling

    # Step 5: Browser Launch & Success Banner
    if is_ready:
        print()
        print("=" * 80)
        print("  [جاهز ومكتمل] تم إقلاع المنظومة بنجاح وفتح واجهة الفحص في المتصفح!")
        print("=" * 80)
        print(f"  المشروع : {TITLE}")
        print(f"  الزميل  : {COLLEAGUE}")
        print(f"  الرابط  : {URL}")
        print(f"  المنفذ  : {PORT}")
        print("  الحالة  : النموذج محمل في الذاكرة وجاهز للتشخيص الفوري (دقة 93.47%)")
        print("=" * 80)
        print()
        open_browser(URL)
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception:
            pass
    else:
        print(f"[!] تنبيه: استغرق الإقلاع وقتاً أطول من المعتاد. جاري فتح الرابط: {URL}")
        open_browser(URL)

    print("  💡 لإيقاف الخادم والخروج بأمان، اضغط مفتاح [Enter] في هذه النافذة...")
    try:
        input()
    except (KeyboardInterrupt, EOFError):
        pass

    # Step 6: Safe Termination
    print(f"\nجاري إيقاف الخادم وتحرير المنفذ {PORT} بأمان...")
    try:
        server_proc.terminate()
        server_proc.wait(timeout=2.0)
    except Exception:
        try:
            server_proc.kill()
        except Exception:
            pass
    
    try:
        log_file.close()
    except Exception:
        pass

    free_port(PORT)
    print(f"[OK] تم إيقاف المنظومة بنجاح. نتمنى لكم يوماً سعيداً!")
    time.sleep(0.8)

if __name__ == "__main__":
    main()
