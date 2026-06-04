# Screen On Click v0.3.0083
import io
import json
import os
import random
import socket
import threading
import time
import sys
from PIL import Image, ImageGrab, ImageDraw, ImageFont
import win32api
from flask import Flask, Response, request, session, redirect, url_for

try:
    from ctypes import windll
    windll.user32.SetProcessDPIAware()
except:
    pass

TTS_AVAILABLE = True
tts_engine = None
try:
    import pyttsx3
except ImportError:
    TTS_AVAILABLE = False
    print("Warning: loading pyttsx3 fail, TTS disabled.")

app = Flask(__name__)
app.secret_key = os.urandom(24)

latest_frame = None
frame_lock = threading.Lock()
frame_event = threading.Event()
config = {}
auth_code = ""


def load_config():
    default = {
        "port": 10086, "quality": 50, "fps": 8, "max_edge": 1000, "auth_code": "",
        "tts_enabled": True, "show_cursor": True, "cursor_radius": 8
    }
    if not os.path.exists("soc.json"):
        with open("soc.json", "w") as f:
            json.dump(default, f, indent=4)
        return default
    try:
        with open("soc.json", "r") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"Config file corrupted: {e}")
        backup = "soc.json.bak"
        os.replace("soc.json", backup)
        print(f"Backup saved as {backup}, creating new soc.json")
        with open("soc.json", "w") as f:
            json.dump(default, f, indent=4)
        return default


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip


def init_tts():
    global tts_engine, TTS_AVAILABLE
    if not config.get("tts_enabled", True) or not TTS_AVAILABLE:
        return None
    try:
        engine = pyttsx3.init()
        for v in engine.getProperty('voices'):
            if 'english' in v.name.lower() or 'zira' in v.name.lower() or 'david' in v.name.lower():
                engine.setProperty('voice', v.id)
                break
        engine.setProperty('rate', 150)
        engine.setProperty('volume', 0.9)
        tts_engine = engine
        return engine
    except (RuntimeError, ImportError) as e:
        print(f"TTS init failed: {e}. Voice disabled.")
        TTS_AVAILABLE = False
        return None


def generate_auth_code():
    return f"{random.randint(0, 999999):06d}"


def create_error_image(error_text):
    max_edge = config.get("max_edge", 1000)
    w, h = 640, 360
    if max_edge < 800:
        w = h = max_edge
    img = Image.new('RGB', (w, h), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default()
    except:
        font = None
    lines = error_text.split('\n')
    y = h // 2 - 30
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text(((w - tw) // 2, y), line, fill=(255, 80, 80), font=font)
        y += th + 5
    return img


def capture_screen():
    global latest_frame
    fps = config.get("fps", 15)
    quality = config.get("quality", 50)
    max_edge = config.get("max_edge", 1000)
    show_cursor = config.get("show_cursor", True)
    cursor_r = config.get("cursor_radius", 8)

    phys_w = win32api.GetSystemMetrics(0)
    phys_h = win32api.GetSystemMetrics(1)

    error_state = False

    while True:
        t0 = time.time()
        try:
            img = ImageGrab.grab()
            orig_w, orig_h = img.size
            sx = orig_w / phys_w
            sy = orig_h / phys_h

            mouse_x, mouse_y = win32api.GetCursorPos()
            mouse_img_x = int(mouse_x * sx)
            mouse_img_y = int(mouse_y * sy)

            scale = min(1.0, max_edge / max(orig_w, orig_h))
            if scale < 1.0:
                new_size = (int(orig_w * scale), int(orig_h * scale))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
                mouse_img_x = int(mouse_img_x * scale)
                mouse_img_y = int(mouse_img_y * scale)

            if show_cursor and 0 <= mouse_img_x < img.width and 0 <= mouse_img_y < img.height:
                draw = ImageDraw.Draw(img)
                r = cursor_r
                draw.ellipse((mouse_img_x - r, mouse_img_y - r,
                              mouse_img_x + r, mouse_img_y + r),
                             outline='white', fill=None)
                dot_r = 3
                draw.ellipse((mouse_img_x - dot_r, mouse_img_y - dot_r,
                              mouse_img_x + dot_r, mouse_img_y + dot_r),
                             fill='black')
            buf = io.BytesIO()
            img.save(buf, format='JPEG', quality=quality, optimize=True)
            buf.seek(0)
            with frame_lock:
                latest_frame = buf.getvalue()
            frame_event.set()

            if error_state:
                print("Screen capture recovered.")
                error_state = False

        except Exception as e:
            if not error_state:
                print(f"Capture error: {e}")
                error_state = True
            error_msg = f"Screen capture failed.\nReason: {str(e)[:80]}\nMay UAC or lock screen."
            img = create_error_image(error_msg)
            buf = io.BytesIO()
            img.save(buf, format='JPEG', quality=60, optimize=True)
            buf.seek(0)
            with frame_lock:
                latest_frame = buf.getvalue()
            frame_event.set()

        elapsed = time.time() - t0
        sleep_time = max(0, (1.0 / fps) - elapsed)
        time.sleep(sleep_time)


@app.route('/')
def index():
    if session.get('authenticated'):
        return render_viewer()
    code = request.args.get('code')
    if code and code == auth_code:
        session['authenticated'] = True
        return redirect(url_for('index'))
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>ScreenOnClick · Auth</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                background: #000;
                font-family: 'Segoe UI', 'Inter', system-ui, sans-serif;
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
            }
            .card {
                background: #1e1e1e;
                border-radius: 3px;
                padding: 40px 32px;
                box-shadow: 0 20px 35px rgba(0,0,0,0.5);
                width: 360px;
                text-align: center;
                border: 1px solid #2c2c2c;
            }
            h2 {
                color: #ffffff;
                font-weight: 500;
                margin-bottom: 12px;
                letter-spacing: -0.3px;
            }
            .sub {
                color: #aaa;
                margin-bottom: 32px;
                font-size: 14px;
            }
            input {
                width: 100%;
                padding: 14px 18px;
                background: #0a0a0a;
                border: 1px solid #2c2c3a;
                border-radius: 5px;
                color: #ffffff;
                font-size: 20px;
                letter-spacing: 4px;
                text-align: center;
                outline: none;
                transition: 0.2s;
                margin-bottom: 20px;
            }
            input:focus {
                border-color: #000000;
                box-shadow: 0 0 0 2px rgba(0,255,0,0.2);
            }
            button {
                background: #000000;
                border: none;
                padding: 12px 24px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 16px;
                color: #ffffff;
                cursor: pointer;
                width: 100%;
                transition: 0.2s;
            }
            button:hover {
                background: #0c0;
                transform: scale(0.98);
            }
            .footer {
                margin-top: 28px;
                font-size: 12px;
                color: #555;
            }
        </style>
    </head>
    <body>
        <div class="card">
            <h2>ScreenOnClick</h2>
            <div class="sub">Enter 6-digit code</div>
            <form method="get">
                <input type="text" name="code" placeholder="—  —  —  —  —  —" autocomplete="off" autofocus>
                <button type="submit">Verify</button>
            </form>
            <div class="footer">Code shown in console / spoken at startup</div>
        </div>
    </body>
    </html>
    '''


def render_viewer():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>ScreenOnClick · Live</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
        body {
            background: #000;
            margin: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh
        }

        img {
            max-width: 98vw;
            max-height: 98vh;
            border: 2px solid #333
        }
        </style>
    </head>
    <body>
        <img id="screen" alt="screen">
        <script>
            var img = document.getElementById('screen');
            function fetchFrame() {
                var xhr = new XMLHttpRequest();
                xhr.open('GET', '/frame.jpg?t=' + Date.now(), true);
                xhr.responseType = 'blob';
                xhr.onload = function() {
                    if (xhr.status === 200) {
                        var url = URL.createObjectURL(xhr.response);
                        img.onload = function() {
                            URL.revokeObjectURL(url);
                            img.style.opacity = '1';
                            fetchFrame();
                        };
                        img.src = url;
                    } else {
                        setTimeout(fetchFrame, 200);
                    }
                };
                xhr.onerror = function() {
                    setTimeout(fetchFrame, 500);
                };
                xhr.send();
            }
            fetchFrame();
        </script>
    </body>
    </html>
    '''


@app.route('/frame.jpg')
def frame():
    frame_event.wait(timeout=1.0)
    frame_event.clear()
    with frame_lock:
        if latest_frame is None:
            return b'', 204
        return Response(latest_frame, mimetype='image/jpeg')


def main():
    print("ScreenOnClick By GududaoStudio")
    print("Version:0.3.0083")
    print("GitHub:GududaoNet/ScreenOnClick   https://GududaoNet.GitHub.io")
    global auth_code, config, tts_engine, TTS_AVAILABLE
    config = load_config()

    if config.get("auth_code"):
        auth_code = str(config["auth_code"])
    else:
        auth_code = generate_auth_code()

    if config.get("tts_enabled", True) and TTS_AVAILABLE:
        init_tts()
        if tts_engine is not None:
            ip = get_local_ip()
            port = config.get("port", 10086)

            def digit_words(s):
                return ' '.join(['zero,', 'one,', 'two,', 'three,', 'four,', 'five,', 'six,', 'seven,', 'eight,', 'nine,'][int(ch)] for ch in s if ch.isdigit())
            msg = (f"ScreenOnClick ready. IP address {ip}. Port {digit_words(str(port))}. "
                   f"Auth code, {digit_words(auth_code)}.")
            tts_engine.say(msg)
            tts_engine.runAndWait()

    ip = get_local_ip()
    port = config.get("port", 10086)
    print(f"Auth code: {auth_code}")
    print(f"Serving on http://{ip}:{port}")

    threading.Thread(target=capture_screen, daemon=True).start()

    import logging
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    max_attempts = 10
    for attempt in range(max_attempts):
        try:
            app.run(host='0.0.0.0', port=port, debug=False,
                    use_reloader=False, threaded=True)
            break
        except OSError as e:
            if '10048' in str(e) or 'Address already in use' in str(e):
                print(f"Port {port} busy, trying {port+1}")
                port += 1
                continue
            else:
                raise
    else:
        print("Failed to find free port after 10 attempts. Exiting.")
        sys.exit(1)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n[Fatal] Unhandled error: {e}")
        sys.exit(1)
