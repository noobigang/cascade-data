# Setup on Windows

Step-by-step for Windows 10 / 11. If anything is unclear, scroll to **Troubleshooting** at the bottom.

## 1. Install Python 3.11 or newer

Check if you already have it:

```powershell
python --version
```

If you see `Python 3.11.x` or higher, skip to step 2.

If you see `Python 3.10.x` or lower, or `'python' is not recognized`, install Python:

1. Go to https://www.python.org/downloads/windows/
2. Click the big yellow **Download Python 3.X.X** button
3. Run the installer
4. **Important:** on the first screen, check the box that says **"Add python.exe to PATH"** — this is what lets you type `python` in any terminal
5. Click **Install Now**
6. Wait for it to finish
7. **Close and reopen** your terminal (PowerShell or cmd) so it picks up the new PATH

Verify:

```powershell
python --version
# Expected: Python 3.11.x or higher
```

## 2. Install Git (if you don't have it)

Check:

```powershell
git --version
```

If you get an error, install from https://git-scm.com/download/win and use the default options. Reopen your terminal after install.

## 3. Open a terminal in the folder where you want Cascade

For example, `C:\Users\YourName\Projects`. In File Explorer, navigate to that folder, click the address bar, type `powershell`, press Enter. A terminal will open in that folder.

## 4. Clone the repo

```powershell
git clone https://github.com/noobigang/cascade-data.git
cd cascade-data
```

## 5. Create a virtual environment

A virtual environment keeps Cascade's dependencies isolated from the rest of your system. **You do this once per project.**

```powershell
python -m venv .venv
.venv\Scripts\activate
```

You'll see `(.venv)` at the start of your prompt when it's active. To deactivate later, just run `deactivate`.

## 6. Install dependencies

```powershell
pip install -r requirements.txt
```

This will take 1-3 minutes. You should see something like:

```
Successfully installed streamlit-1.58.0 networkx-3.6.1 sqlglot-30.10.0 ...
```

If you see `ERROR: ...`, scroll to **Troubleshooting** below.

## 7. Run the app

```powershell
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

```powershell
cd path\to\cascade-data
.venv\Scripts\activate
streamlit run app.py
```

---

## Troubleshooting

### `'python' is not recognized as an internal or external command`

Python isn't on your PATH. Two options:

- **Reinstall Python** and check **"Add python.exe to PATH"** during install.
- **Add it manually:** Win+R → `sysdm.cpl` → Advanced → Environment Variables → Path → Edit → New → `C:\Users\YourName\AppData\Local\Programs\Python\Python311\` and `C:\Users\YourName\AppData\Local\Programs\Python\Python311\Scripts\` → OK → reopen terminal.

### `'streamlit' is not recognized`

You forgot to activate the virtual environment. Run `.venv\Scripts\activate` first.

### `ERROR: No matching distribution found for streamlit>=1.40.0`

Your pip is too old. Upgrade it:

```powershell
python -m pip install --upgrade pip
```

Then retry `pip install -r requirements.txt`.

### `OSError: [Errno 98] Address already in use` (port 8502 taken)

Either close whatever's using port 8502, or run on a different port:

```powershell
streamlit run app.py --server.port 8503
```

### `ModuleNotFoundError: No module named 'streamlit_js_eval'`

Re-run the install:

```powershell
pip install -r requirements.txt
```

### Tests fail with `ModuleNotFoundError: No module named 'lineage'`

Make sure you're in the `cascade-data/` root directory (the one with `app.py`), not a subdirectory.

```powershell
cd cascade-data
pytest tests/ -v
```

### `git` not recognized

Install from https://git-scm.com/download/win. Reopen terminal after.

### Still stuck?

Open an issue at https://github.com/noobigang/cascade-data/issues with:
1. The exact command you ran
2. The full error output (copy-paste, don't summarize)
3. Your `python --version` and `pip --version` output
