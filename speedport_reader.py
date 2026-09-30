"""Offline reader for Speedport W724V Type A backups, firmware 05011603.06.003."""
from pathlib import Path
import argparse
import sys
import zlib
import xml.etree.ElementTree as ET

# Recovered from security source 0x30000 in the specified firmware.
# These are firmware constants, not a user's credentials.
KEY = bytes.fromhex('6C28B1FEB2B82A9D129AB6BF1D139EF2FF58EF5A0478282DF25E84E46816E5CB')
IV = bytes.fromhex('3304ADCE208C07E6655B009A10F8AC53')
MAX_INPUT = 16 * 1024 * 1024
MAX_XML = 32 * 1024 * 1024


def read_backup(path):
    from Crypto.Cipher import AES
    path = Path(path)
    if not 0 < path.stat().st_size <= MAX_INPUT:
        raise ValueError('File is empty or larger than 16 MiB.')
    data = path.read_bytes()
    if len(data) % 16:
        raise ValueError('Invalid backup file size.')
    plain = AES.new(KEY, AES.MODE_CBC, IV).decrypt(data)
    decoder = zlib.decompressobj()
    try:
        xml = decoder.decompress(plain, MAX_XML + 1)
    except zlib.error as exc:
        raise ValueError('Unsupported or corrupted W724V Type A backup.') from exc
    if len(xml) > MAX_XML or decoder.unconsumed_tail or not decoder.eof:
        raise ValueError('Compressed data is incomplete or too large.')
    # The firmware appends a NUL to the XML; AES padding follows the zlib stream.
    xml = xml.rstrip(b'\x00')
    if b'<!DOCTYPE' in xml.upper() or b'<!ENTITY' in xml.upper():
        raise ValueError('Unexpected XML declaration.')
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as exc:
        raise ValueError('Decrypted data is not valid XML.') from exc
    if root.tag != 'InternetGatewayDeviceConfig':
        raise ValueError('Unexpected configuration format.')
    profiles = []
    for node in root.findall('./Device/PPP/Interface/InterfaceInstance'):
        attrs = node.attrib
        fields = [(label, attrs.get(user, ''), attrs.get(password, ''))
                  for label, user, password in [
                      ('PPP', 'Username', 'Password'),
                      ('Telekom', 'X_DtUsername', 'X_DtPassword'),
                      ('Other provider', 'X_OtherUsername', 'X_OtherPassword'),
                      ('BNG', 'X_BngUsername', 'X_BngPassword')]]
        seen = set()
        for label, user, password in fields:
            if not (user or password) or (user, password) in seen:
                continue
            seen.add((user, password))
            profiles.append({'profile': attrs.get('InstanceID', '?'),
                             'name': attrs.get('Name', ''), 'kind': label,
                             'enabled': attrs.get('Enable', '?'),
                             'username': user, 'password': password})
    if not profiles:
        raise ValueError('No PPP credentials found.')
    return profiles


def gui():
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    root = tk.Tk()
    root.title('Speedport Config Reader')
    root.geometry('680x340')
    frame = ttk.Frame(root, padding=12)
    frame.pack(fill='both', expand=True)
    ttk.Label(frame, text='Speedport W724V Type A', font=('', 11, 'bold')).pack(anchor='w')
    ttk.Label(frame, text='Type A / 05011603.06.003 / Offline').pack(anchor='w', pady=(4, 14))
    status = tk.StringVar(value='Select a .config file.')
    choice = tk.StringVar()
    username = tk.StringVar()
    password = tk.StringVar()
    reveal = tk.BooleanVar(value=False)
    records = []

    def display(*_):
        i = selector.current()
        if 0 <= i < len(records):
            username.set(records[i]['username'])
            password.set(records[i]['password'])

    def select_file():
        path = filedialog.askopenfilename(filetypes=[('Config backup', '*.config'), ('All files', '*')])
        if not path:
            return
        records.clear()
        username.set('')
        password.set('')
        selector['values'] = ()
        choice.set('')
        try:
            records.extend(read_backup(path))
        except ImportError:
            messagebox.showerror('Missing dependency', 'Run:\npy -m pip install pycryptodome')
            status.set('pycryptodome is not installed.')
            return
        except (OSError, ValueError) as exc:
            messagebox.showerror('Cannot read backup', str(exc))
            status.set('No credentials loaded.')
            return
        selector['values'] = [f"Profile {r['profile']} · {r['kind']} · Enable={r['enabled']}" for r in records]
        selector.current(0)
        display()
        status.set(f'{Path(path).name}: Decrypted successfully.')

    def copy(value):
        if value.get():
            root.clipboard_clear()
            root.clipboard_append(value.get())
            status.set('Copied.')

    ttk.Button(frame, text='Open config', command=select_file).pack(anchor='w')
    selector = ttk.Combobox(frame, textvariable=choice, state='readonly')
    selector.pack(fill='x', pady=12)
    selector.bind('<<ComboboxSelected>>', display)
    for label, variable in [('Username', username), ('Password', password)]:
        ttk.Label(frame, text=label).pack(anchor='w')
        row = ttk.Frame(frame)
        row.pack(fill='x', pady=(2, 8))
        entry = ttk.Entry(row, textvariable=variable, state='readonly', show='*' if label == 'Password' else '')
        entry.pack(side='left', fill='x', expand=True)
        if label == 'Password':
            password_entry = entry
        ttk.Button(row, text='Copy', command=lambda v=variable: copy(v)).pack(side='right', padx=(8, 0))
    ttk.Checkbutton(frame, text='Show password', variable=reveal,
                    command=lambda: password_entry.configure(show='' if reveal.get() else '*')).pack(anchor='w')
    ttk.Label(frame, textvariable=status, wraplength=710).pack(anchor='w', pady=(14, 0))
    root.mainloop()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('config', nargs='?', help='Open the GUI when no file is specified.')
    parser.add_argument('--show-password', action='store_true', help='Print the password in the terminal.')
    args = parser.parse_args()
    if not args.config:
        gui()
        return 0
    try:
        for r in read_backup(args.config):
            print(f"Profile {r['profile']} / {r['kind']} / Enable={r['enabled']}")
            print('Username:', r['username'])
            print('Password:', r['password'] if args.show_password else '[hidden; use --show-password]')
    except (ImportError, OSError, ValueError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
