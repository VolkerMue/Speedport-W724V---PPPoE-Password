# Speedport W724V – PPPoE Config Reader

A small offline tool to recover PPPoE credentials from a **Telekom Speedport W724V Type A** configuration backup.

Available as a standalone **browser tool** (no installation required) and as a **Python script** with a Tkinter GUI.

Verified against a real W724V Type A backup with firmware `05011603.06.003`.  
Type B / Type C and other firmware versions are not yet supported.

---

## Features

- Decrypts the `.config` backup file entirely **offline**
- Extracts all stored PPP profiles (Telekom, other ISPs, BNG) Shows username and masked password
- Two interfaces: a single HTML file for the browser, and a Python script with GUI or CLI

---

## Browser Tool

1. Download `Speedport_W724V_TypA_Browsertool.html`
2. Open it by double-clicking — works in any recent Chrome, Edge or Firefox
3. Select or drag-and-drop your `.config` backup file
4. Username and password appear immediately

The page contains no external resources and cannot make network connections (enforced by Content Security Policy).

---

## Python Tool

**Requirements:** Python 3.10 or newer with Tkinter (included in the standard Windows installer)

### Install dependency

```bash
pip install -r requirements.txt
```

### GUI

```bash
python speedport_reader.py
```

or on Windows:

```bash
py speedport_reader.py
```

### Command line

```bash
python speedport_reader.py "724V.config"
```

To show the password in plain text:

```bash
python speedport_reader.py "724V.config" --show-password
```

---

## How it works

The `.config` backup is encrypted with **AES-256-CBC**, followed by **zlib compression** and an XML structure.

The fixed key and IV were recovered from security source `0x30000` of the specified firmware by interleaving four 524-byte blocks from `libxmlapi.so`, `libhttpapi.so`, `libcfmapi.so` and `libmsgapi.so`, then decrypting them with the firmware's own white-box AES routine.

Only the resulting firmware constants are included in this tool — no personal credentials.


---

## Limitations

- Tested with **W724V Type A**, firmware `05011603.06.003` only
- Stored credentials do not prove that the ISP currently accepts them

---

## License

MIT
