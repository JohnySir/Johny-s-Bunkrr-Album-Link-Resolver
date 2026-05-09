# 🚀 Johny's Bunkrr Album Link Resolver PRO

A high-performance, standalone desktop CLI tool specifically engineered to resolve entire Bunkrr albums into direct, downloadable media links with a modern Terminal User Interface (TUI).

Inspired by the resolution mechanisms of [bonkrr](https://github.com/najahiiii/bonkrr), this PRO version focuses on a premium user experience, extreme stability for large albums, and modern terminal aesthetics.

---

## 📸 Preview

![Application Demo Placeholder](https://via.placeholder.com/800x450.png?text=Johny's+Bunkrr+Resolver+Pro+Demo+GIF+Placeholder)
*A sleek, neon-themed dashboard for all your link resolution needs.*

---

## ✨ Features

- **🎨 Modern TUI**: Built with the `Textual` library for a professional, dashboard-like experience.
- **⚡ High-Speed Resolution**: Optimized concurrency (12 parallel workers) to handle even the largest albums in seconds.
- **🌐 Dynamic Domain Support**: Future-proof logic that automatically adapts to Bunkr domain changes (e.g., .su, .cr, .ru).
- **🛡️ Intelligent Link Check**: Automatically validates link health using `HEAD` and Ranged `GET` requests to ensure your links are active.
- **📁 Smart Export**: Generates sanitized `.txt` files compatible with IDM, aria2, and other download managers.
- **📉 Efficiency**: Implements batch UI updates to ensure the application stays responsive when processing thousands of files.
- **😴 Idle Mode**: Subtle status indicators to let you know exactly what the engine is doing.

---

## 🛠️ Noob-Friendly Installation Guide

Follow these steps to get the tool running on your Windows machine in less than 2 minutes!

### 1. Clone or Download
Download the source code to your computer and open a terminal (PowerShell or CMD) in that folder.

### 2. Set Up a Virtual Environment (Recommended)
This keeps the tool's requirements separate from your system's Python.

```powershell
# Create the virtual environment
python -m venv venv

# Activate it
# On Windows:
.\venv\Scripts\activate
```

### 3. Install Dependencies
Install the necessary libraries to power the UI and the resolver engine.

```powershell
pip install -r resolver_tool/requirements.txt
```

---

## 🚀 How to Use

1. **Start the App**:
   ```powershell
   python resolver_tool/main.py
   ```
2. **Paste & Resolve**:
   - Simply copy a Bunkr album link (e.g., `https://bunkr.su/a/XXXX`).
   - Paste it into the input box and hit **Enter**.
3. **Download**:
   - Once finished, the tool will create a `.txt` file named after the album in the same directory.
   - Import this file into your favorite download manager!

---

## ⌨️ Shortcuts

- **`CTRL + C`** or **`Q`**: Quit the application gracefully.
- **`CTRL + L`**: Clear the logs.

---

## ⚖️ Disclaimer & License

This tool is intended for resolving links from publicly accessible sources that you are authorized to use. Please respect the terms of service of the content providers.

Licensed under the MIT License. 

---
*Developed with ❤️ by Johny.*
