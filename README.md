# Unified Radio Faceplate for SDR & Receivers

A compact and elegant **Python / PyQt5** application that combines a customizable analog S-meter, an interactive rotary VFO dial, and real-time serial CAT control for software-defined radios and receivers (such as SDR Console).

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![PyQt5](https://img.shields.io/badge/PyQt5-GUI-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 🚀 Key Features

* **Fluid Analog S-Meter:** Features realistic needle damping and multiple interchangeable graphic skins (`imageyellow.png`, `imagewhite.png`, `imageblue.png`, `imageblack.png`, `imagegreen.png`).
* **Interactive VFO Dial:** Smooth frequency tuning via mouse dragging, mouse wheel, or step buttons.
* **Stepped Tuning:** Quick adjustment steps ranging from 1 Hz up to 10 kHz.
* **Direct Numeric Keypad:** Built-in keypad to punch in frequencies directly and apply them instantly with the `SET` button.
* **Real-time Serial CAT Integration:** Bidirectional serial communication polling frequency (`FA;`) and signal meter (`SM;`) status continuously.
* **Always on Top:** Quick pin toggle button to keep the faceplate floating above your main SDR software window.

---

## 🛠 Prerequisites & Dependencies

Make sure you have Python installed along with the required libraries:

    pip install PyQt5 pyserial

---

## ⚙️ Usage

1. Clone or download this repository.
2. Ensure you have your S-meter skin images in the same directory (or adjust the filenames in the script).
3. Configure your virtual serial port (e.g., using `com0com` or hardware CAT bridge) to match your SDR software.
4. Run the application:

    python unified_faceplate.py

5. Go to the **Setup CAT** tab, enter your COM port and baud rate (default is `COM6` at `57600`), and click **Riconnetti CAT**.

---

## 🎛 Interface Overview

* **S-Meter Header:** Displays current signal level in S-units / dB over S9 and a live CAT status indicator.
* **Skins Switcher:** Instantly swap between different aesthetic faceplate styles.
* **VFO Console:** Rotate the dial or use step buttons to navigate bands seamlessly.

---

## 📄 License

This project is open-source and available under the [MIT License](LICENSE).




<img width="1918" height="1079" alt="image" src="https://github.com/user-attachments/assets/06d98efa-3e42-48c4-b18c-fb98de5edc68" />
