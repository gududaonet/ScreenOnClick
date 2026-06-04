# ScreenOnClick

**🎉 GududaoStudio 6th Anniversary Work**

> ⚡ Just one click.
> Access a computer with a broken display from any web browser.

A lightweight browser-based desktop viewer designed for emergency access and display failure recovery.

---

## Features

* 📺 View desktop from any web browser
* 🔑 Random 6-digit access code (Customizable)
* 🔊 TTS announces IP, port and access code 
* 🖱 Mouse cursor visualization
* 📏 Automatic image scaling
* 🚀 Single-file deployment
* 💻 Supports Windows 7 and later
   (Linux and macOS are not currently supported)
* 🪶 Standalone executable available (usually via Relaese)

---

## Quick Start

### Option 1 — Executable (Recommended)

1. Copy the executable to a USB drive or any accessible location.
2. Start Windows Narrator (`Win + Ctrl + Enter` on newer Windows versions).
3. Open Command Prompt.
4. Run:

```cmd
SOC.exe
```

No configuration required.

The program will announce:

* IP address
* Port
* Access code

using TTS automatically.

---

### Option 2 — Python

Download 

Install dependencies:

```bash
pip install flask pillow pywin32 pyttsx3
```

Run:

```bash
python SOC.py
```

---

## Usage

After startup, open any browser on the same network:

```text
http://<IP>:<PORT>
```

Enter the 6-digit access code.

Done.

---

## Typical Scenarios

* Broken monitor
* Headless computer (maybe you need to buy one of those fake HDMI dongles from Temu.)
* Display troubleshooting (can't magically fix your GPU, sorry.)
* Temporary desktop access
* Recovering a machine without a working screen
* Finishing a fucking paper because your fucking Surface Pro decided to die the night before the deadline

---


## Why?

My Surface Pro 9 was dying.

The screen was fucked.

The deadline was not.

So I wrote this.

ScreenOnClick simply asks:

> What if the monitor is optional?

---
## Why not VNC?

VNC is great.

Seriously.

If you need a full-featured remote desktop solution, use VNC.

ScreenOnClick was built for a much dumber problem:

> "My monitor is dead and I need to see the screen right now."

No installation on the client.

No viewer application.

No setup guide.

Just run it and open a browser.

---

## Release

Prebuilt executables may be provided in Releases.

Or may not.

It depends on whether I feel like booting a Windows 7 virtual machine that day.

---

## License

MIT

If this project saves your computer at 3 AM, we're even.
