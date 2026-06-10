# Setup on macOS / Linux

Step-by-step for macOS 12+ and Linux (Ubuntu, Debian, Fedora, Arch). If anything is unclear, scroll to **Troubleshooting** at the bottom.

## 1. Install Python 3.11 or newer

### macOS

The system Python on macOS is too old. Install a modern one with Homebrew:

```bash
# Install Homebrew if you don't have it
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python
brew install python@3.11
```

Make sure `/opt/homebrew/bin` (Apple Silicon) or `/usr/local/bin` (Intel) is on your PATH. Verify:

```bash
python3 --version
# Expected: Python 3.11.x or higher

which python3
# Should print a path under homebrew or /usr/local
```

### Linux

**Ubuntu / Debian:**

```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip git
```

If `python3.11` isn't in the default repos on your distro, use the deadsnakes PPA:

```bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt install -y python3.11 python3.11-venv python3-pip
```

**Fedora:**

```bash
sudo dnf install -y python3.11 python3-pip git
```

**Arch:**

```bash
sudo pacman -S python python-pip git
```

Verify:

```bash
python3 --version
# Expected: Python 3.11.x or higher
```

## 2. Install Git (if you don't have it)

```bash
git --version
```

If missing:

- **macOS:** `xcode-select --install` (then accept the license)
- **Linux:** already installed via the steps above

## 3. Open a terminal in your project folder

```bash
cd ~/Projects    # or wherever you keep code
```

## 4. Clone the repo

```bash
git clone https://github.com/noobigang/cascade-data.git
cd cascade-data
```

## 5. Create a virtual environment

A virtual environment keeps Cascade's dependencies isolated from the rest of your system. **You do this once per project.**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

You'll see `(.venv)` at the start of your prompt when it's active. To deactivate later, just run `deactivate`.

## 6. Install dependencies

```bash
pip install -r requirements.txt
```

This will take 1-3 minutes. You should see something like:

```
Successfully installed streamlit-1.58.0 networkx-3.6.1 sqlglot-30.10.0 ...
```

If you see `ERROR: ...`, scroll to **Troubleshooting** below.

## 7. Run the app

```bash
streamlit run app.py
```

You should see:

```
You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8502
  Network URL: http://192.168.x.x:8502
```

The browser should open automatically. If not, manually visit http://localhost:8502.

## 8. Stop the app

Press `Ctrl+C` in the terminal where Streamlit is running.

## Next time you want to run Cascade

You don't need to re-clone or re-install. Just:

```bash
cd ~/path/to/cascade-data
source .venv/bin/activate
streamlit run app.py
```

---

## Troubleshooting

### `python3: command not found`

Python isn't installed or not on PATH. Re-do step 1. On macOS with Homebrew, you may also need to add Homebrew's bin dir to PATH — follow the instructions Homebrew prints at the end of install.

### `'streamlit' is not recognized` / `command not found: streamlit`

You forgot to activate the virtual environment. Run `source .venv/bin/activate` first. The prompt should show `(.venv)` at the start.

### `error: externally-managed-environment` (PEP 668)

Newer Python (3.12+) on Debian/Ubuntu blocks system-wide pip installs. Use a venv (steps 5–6 above) — that's exactly what it's for. If you insist on a global install, use `pip install --break-system-packages`, but don't.

### `ERROR: No matching distribution found for streamlit>=1.40.0`

Your pip is too old. Upgrade:

```bash
python3 -m pip install --upgrade pip
```

Then retry `pip install -r requirements.txt`.

### `OSError: [Errno 98] Address already in use` (port 8502 taken)

Either close whatever's using port 8502, or run on a different port:

```bash
streamlit run app.py --server.port 8503
```

### `ModuleNotFoundError: No module named 'streamlit_js_eval'`

Re-run the install:

```bash
pip install -r requirements.txt
```

### Tests fail with `ModuleNotFoundError: No module named 'lineage'`

Make sure you're in the `cascade-data/` root directory (the one with `app.py`), not a subdirectory.

```bash
cd cascade-data
pytest tests/ -v
```

### `ssl.SSLCertVerificationError` on macOS

Run the macOS installer that updates your certificates, or use Homebrew's Python (which has certs bundled):

```bash
brew install python@3.11
brew install openssl
```

Then re-create your venv with the Homebrew Python.

### Still stuck?

Open an issue at https://github.com/noobigang/cascade-data/issues with:
1. The exact command you ran
2. The full error output (copy-paste, don't summarize)
3. Your `python3 --version` and `pip --version` output
4. Your OS version (`sw_vers` on macOS, `lsb_release -a` on Ubuntu)
