# 💬 WhatsApp Chat Viewer

> Turn an exported WhatsApp chat into a beautiful, **offline**, WhatsApp-style HTML viewer — with real media, date-range filtering, and smooth handling of **huge** chats (1 GB – 10 GB+).

<p align="left">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.7%2B-blue?logo=python&logoColor=white">
  <img alt="Pillow" src="https://img.shields.io/badge/Pillow-optional-orange">
  <img alt="Dependencies" src="https://img.shields.io/badge/runtime%20deps-stdlib%20only-success">
  <img alt="Platform" src="https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-green">
</p>

A single self-contained Python script (`whatsapp_chat_viewer.py`) that reads a WhatsApp **"Export chat"** folder (the `.txt` transcript plus its media files) and generates a polished, **WhatsApp-like** web page you can open by double-clicking — no server, no internet, no browser extension, and **no CORS errors**.

---

## ✨ Features

- 🟢 **Authentic WhatsApp interface** — chat bubbles, sender colors, date dividers, system-message badges, and a familiar dark/light theme.
- 📅 **Date-range / time-frame viewing** — pick a **From → To** month, or use one-tap quick filters: **Last Month**, **Last 3 Months**, **Last 6 Months**, **All Messages**.
- 🚀 **Handles massive chats (1–10 GB+)** — messages are split into **per-month chunks** that load **on demand**, so the page stays fast even for years of history.
- 🧩 **No CORS errors** — chunks are emitted as `.js` files (not `.json`), so the viewer works straight from `file://` by **double-clicking**, with no local web server required.
- 🖼️ **Rich media support** — inline **images** (with auto thumbnails), **video** & **audio** players, and **document** cards (PDF, DOCX, XLSX, PPTX, ZIP, VCF, and more) with type-colored icons.
- 🔍 **Full-screen image lightbox** — zoom (buttons / scroll / pinch), pan/drag, double-tap to zoom, and keyboard shortcuts (`+`, `-`, `0`, `Esc`).
- 🧠 **Universal file detection** — matches attachments by indexing the media folder, by the `(file attached)` marker, **and** by file-extension heuristics, so oddly-named files are still recognized.
- 🫥 **Graceful missing-media handling** — if a file referenced in the chat isn't present on disk, a clean "File not available" placeholder is shown instead of breaking the layout.
- 📎 **"Media omitted" placeholder** — when media wasn't included in the export, the message shows a clear placeholder instead of an empty bubble.
- ✏️ **Edited-message indicator** — messages WhatsApp marked as edited show a subtle **"Edited"** tag rather than literal marker text.
- 🛡️ **Safe rendering** — message text and file names are HTML-escaped, so unusual characters (`<`, `>`, `&`) display correctly and never break the page. Unicode and emoji (including non-Latin scripts) are fully supported.
- 🌗 **Dark / light theme toggle** — remembered between visits via `localStorage`.
- 🔒 **100% offline & private** — everything runs locally on your machine; no data ever leaves your computer.
- 📦 **Zero runtime dependencies** — pure Python standard library. [Pillow](https://python-pillow.org/) is **optional** and only used to generate image thumbnails.

---

## 🧠 How It Works

The script processes your exported chat in three stages:

1. **Parse** — `whatsapp_chat_viewer.py` reads the `.txt` transcript line by line with a flexible regex that understands WhatsApp's `DD/MM/YYYY, HH:MM - Sender: Message` format (12- or 24-hour time, 2- or 4-digit years, and multi-line messages). It classifies each line as a normal message, a **system message** (group created, encryption notice, "message was deleted", etc.), or an **attachment**, recognizes WhatsApp's `<Media omitted>`, `(file attached)` and edited-message markers, and groups everything by `YEAR-MONTH`.

2. **Chunk** — messages are written into a `chat_data/` folder as one **JavaScript file per month** (e.g. `2024-03.js`). Each file assigns its data to a `window.CHAT_DATA_YYYY_MM` variable. Using `.js` instead of `.json` is the key trick: browsers block `fetch()` of local `.json` files under the `file://` protocol (CORS), but a `<script src="...">` loads fine — so the viewer needs **no web server**.

3. **Render** — a single self-contained `chat_viewer.html` (all CSS + JS inlined) is generated. When you pick a date range, it dynamically injects only the relevant month `.js` files, then renders the messages. Image **thumbnails** (and small <2 MB audio/video) are embedded as base64 for instant preview, while full-resolution media is loaded from the folder on demand.

```
Exported chat folder ──► whatsapp_chat_viewer.py ──►  chat_viewer.html   (the viewer — open this)
   (.txt + media)                                 └►  chat_data/*.js     (per-month message chunks)
```

---

## 📦 Requirements

- **Python 3.7+**
- **[Pillow](https://python-pillow.org/) (optional)** — only needed for image thumbnails. Without it, the script still runs; image previews simply fall back to the embedded/full file where available.

```bash
# Optional, recommended for nicer image thumbnails:
pip install Pillow
```

> Pillow 9.1+ is recommended (the script uses `Image.Resampling.LANCZOS`).

---

## 🚀 Installation

```bash
git clone https://github.com/udhay8005/whatsapp-chat-viewer.git
cd whatsapp-chat-viewer
```

That's it — the tool is a single script with no required dependencies.

---

## 📖 Usage

### 1. Export your chat from WhatsApp
On your phone: open the chat → **⋮ / contact name → More → Export chat → Include media**. This produces a `.txt` transcript along with the chat's media files.

### 2. Put everything in one folder
Place the exported `.txt` file **and** all its media files together in a single folder, for example:

```
My WhatsApp Export/
├── WhatsApp Chat with Family.txt
├── IMG-20240312-WA0001.jpg
├── VID-20240312-WA0002.mp4
├── PTT-20240312-WA0003.opus
└── Invoice.pdf
```

### 3. Run the script

```bash
python whatsapp_chat_viewer.py
```

You'll be prompted for the folder path (press **Enter** to use the current folder). The script auto-detects the `.txt` file (or asks you to choose if there are several), then builds the viewer.

### 4. Open the viewer
Double-click the generated **`chat_viewer.html`** inside your export folder. Pick a date range (or a quick filter) and click **Load**. Change the range anytime with the 📅 button, and toggle dark/light with the ☀️/🌙 button.

---

## 🗂️ Supported Attachment Types

| Category    | Extensions (examples) |
|-------------|-----------------------|
| 🖼️ Images   | `jpg`, `jpeg`, `png`, `gif`, `webp`, `bmp`, `tiff`, `heic`, `svg`, `ico` |
| 🎬 Videos   | `mp4`, `mkv`, `avi`, `mov`, `3gp`, `m4v`, `webm`, `flv`, `wmv` |
| 🎵 Audio    | `mp3`, `opus`, `m4a`, `aac`, `amr`, `flac`, `ogg`, `wav`, `wma` |
| 📄 Documents| `pdf`, `doc`, `docx`, `xls`, `xlsx`, `ppt`, `pptx`, `txt`, `zip`, `rar`, `7z`, `vcf`, `csv`, `epub`, `apk`, `html` |

> Images get auto-generated thumbnails (Pillow). Small audio/video (<2 MB) is embedded directly; larger files are referenced from the folder so they stream on demand.

---

## 📂 What Gets Generated

Running the script adds the following to your export folder (these are produced at runtime and are **not** part of this repository):

```
chat_viewer.html      ← the viewer you open
chat_data/
├── 2024-01.js        ← one chunk per month
├── 2024-02.js
└── ...
```

To share or archive the result, keep `chat_viewer.html`, the `chat_data/` folder, and your original media files together.

---

## 🔒 Privacy

This tool is fully **offline**. Your chat content and media are processed locally and embedded into files on your own disk — nothing is uploaded anywhere. This repository intentionally contains **only the script** and its documentation; no chat exports or media are included.

---

## ❓ Troubleshooting

| Symptom | Fix |
|--------|------|
| *"No .txt files found"* | Make sure the exported `.txt` transcript is directly inside the folder you point the script at. |
| Many messages show "📎 Media omitted" | Those media weren't included in the export. Re-export **with media included** to embed them. |
| Images show but no thumbnails | Install Pillow: `pip install Pillow`. |
| Media shows "File not available" | The chat referenced a file that isn't in the folder. Re-export **with media included**, or add the missing files. |
| Dates look wrong | The parser expects WhatsApp's `day/month/year` ordering. Exports using a different locale order may need adjustment. |
| Page won't open / blank | Open `chat_viewer.html` by double-clicking it from the **same folder** that contains `chat_data/`. |

---

## ⚠️ Known Limitations

- **Replies / quoted messages** and **reactions** are **not** shown — WhatsApp's text export strips this information, so it cannot be reconstructed from the `.txt` file.
- The parser targets WhatsApp's standard `day/month/year` export format.

---

## 📜 License

Released under the [MIT License](LICENSE) — free to use, modify, and distribute.

---

## 👤 Author

**udhay8005**
GitHub: [@udhay8005](https://github.com/udhay8005)

> If this project is useful to you, consider giving it a ⭐ on GitHub!
