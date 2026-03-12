# ESP-USB2CAN app (Windows, Mac, Linux)

**ESP-USB2CAN app** – Cross-platform GUI for the **ESP USB to CAN** (ESP-USB2CAN firmware) ESP32-C3 bridge. Uses PyQt6 and pyserial; implements the same binary protocol as the firmware.

## Requirements

- Python 3.9+
- PyQt6, pyserial (see `requirements.txt`)

## Run from source

From the **ESP-USB2CAN-app** directory:

```bash
pip install -r requirements.txt
python main.py
```

Or with the package on `PYTHONPATH`:

```bash
pip install -r requirements.txt
python -m usb2can_gui
```

Or install in editable mode and use the script:

```bash
pip install -e .
esp-usb2can-app
```

## Serial port

- The app uses a **fixed serial baud rate** of **921600** for the USB link (the ESP32-C3 USB Serial/JTAG is effectively a CDC device).
- The **CAN bus bitrate** (125 / 250 / 500 / 1000 kbit/s) is set via the protocol (`CMD_SET_BAUD`) and selected in the GUI before connecting.

## Usage

1. Connect the ESP32-C3 with the ESP-USB2CAN firmware; it will appear as a serial port (e.g. `COM3` on Windows, `/dev/cu.usbmodem*` on macOS, `/dev/ttyACM*` on Linux).
2. Select the port and CAN baud rate, then click **Connect**. The device will open the CAN bus and reply with ACK; when you see “CAN ready”, you can send and receive frames.
3. Optional: enable **Loopback** before connecting to use TWAI self-test/self-reception mode. In this mode, frames you send should also appear back in the RX log, which is useful to verify the ESP USB to CAN path without another CAN node.
4. Received frames appear in the log table; use the **Send frame** panel to transmit (ID in hex, optional Extended/RTR, DLC, data in hex).
5. **Disconnect** closes the CAN bus and the serial port.

## Building standalone executables (PyInstaller)

Build on each target OS for best compatibility.

1. Install PyInstaller and dependencies:

   ```bash
   pip install -r requirements.txt pyinstaller
   ```

2. From **ESP-USB2CAN-app** (use `run_gui.py` so the package is found via `--paths src`):

   **Windows** (no console window):

   ```bash
   pyinstaller --name esp-usb2can-app --windowed --onefile --paths src run_gui.py
   ```

   **macOS / Linux:**

   ```bash
   pyinstaller --name esp-usb2can-app --onefile --paths src run_gui.py
   ```

   Output is in `dist/` as `esp-usb2can-app.exe` (Windows) or `esp-usb2can-app` (macOS/Linux).

3. For a more controlled build, use a `.spec` file and run `pyinstaller esp-usb2can-app.spec`. Ensure the spec uses `run_gui.py` as the entry point and includes `--paths src` so the `usb2can_gui` package is found.

## Project layout

- `src/usb2can_gui/` – Package: `protocol.py`, `bridge.py`, `main_window.py`, `can_log.py`, `send_frame.py`, `__main__.py`
- `requirements.txt` – PyQt6, pyserial
- `main.py` – Launcher when run from ESP-USB2CAN-app without installing
