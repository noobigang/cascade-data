# Running Cascade

> **Cascade is a local-first tool. There is no "deployment" in the cloud sense.**
> You run it on your own machine. This document shows you the few ways to do that.

---

## Option A — Run directly (recommended for most users)

You need **Python 3.11 or newer** on your machine. Nothing else.

```bash
# 1. Clone
git clone https://github.com/noobigang/cascade-data.git
cd cascade-data

# 2. Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows PowerShell

# 3. Install
pip install -r requirements.txt

# 4. Run
streamlit run app.py
```

The app opens at **http://localhost:8502** in your browser.

For platform-specific instructions, see [SETUP_WINDOWS.md](../SETUP_WINDOWS.md) or [SETUP_UNIX.md](../SETUP_UNIX.md).

---

## Option B — Install as a CLI tool

After step 3 above, you can also install Cascade as a package:

```bash
pip install -e .
```

This registers a `cascade` command:

```bash
cascade
# same as: streamlit run app.py
```

Useful if you want to run Cascade from any directory without cd-ing to the repo.

---

## Option C — Docker (for reproducibility)

If you prefer containers, a minimal `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY lineage/ ./lineage/
COPY ui/ ./ui/
COPY demo/ ./demo/

EXPOSE 8502

# Bind to localhost only — never 0.0.0.0
ENV STREAMLIT_SERVER_ADDRESS=127.0.0.1
ENV STREAMLIT_SERVER_PORT=8502

CMD ["streamlit", "run", "app.py"]
```

Build and run:

```bash
docker build -t cascade .
docker run -it --rm -p 127.0.0.1:8502:8502 cascade
```

> ⚠️ The `-p 127.0.0.1:8502:8502` syntax binds the host port to `127.0.0.1` only.
> **Do not** use `-p 8502:8502` (which would bind to all interfaces and expose the
> app to your network). See [SECURITY.md](../SECURITY.md) for why.

---

## Option D — Share with a teammate (without a server)

The simplest way to share Cascade with someone is: **they run their own copy.**

```bash
# You send them this:
git clone https://github.com/noobigang/cascade-data.git
cd cascade-data
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

That's 4 lines. Each teammate runs it on their own machine, with their own `manifest.json` if they have one, or the bundled demo. No shared server, no data leak.

---

## Why no cloud deployment?

We deliberately do not ship a one-click "deploy to cloud" button. A dbt `manifest.json` typically contains:

- All table and column names in your project
- Compiled SQL (which can reveal business logic and joins)
- Database and schema names (which can reveal your data warehouse provider)
- Test definitions and macros

This is **proprietary metadata**. Even if you trust the cloud provider, you probably don't want your column names, descriptions, and SQL stored on a third-party server.

Read [SECURITY.md](../SECURITY.md) for the full argument.

If you have a compelling reason to deploy Cascade centrally (e.g. a small team behind a corporate VPN, with a service account, with audit logging), see [SECURITY.md](../SECURITY.md#hardening-optional) for hardening guidelines.
