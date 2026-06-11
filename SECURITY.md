# Security & privacy

## TL;DR

Cascade runs entirely on your local machine. No data leaves your computer. No account, no API key, no cloud service.

## What the app does

Cascade reads a `manifest.json` file you upload (or the bundled demo `manifest.json`) and renders an interactive column-level lineage graph. That's it.

Specifically, it does the following, all in your local Python process:

1. Parses the `manifest.json` JSON into a `LineageGraph` data structure.
2. For each model node, runs SQLGlot on the compiled SQL to extract column-level dependencies.
3. Computes blast-radius and risk scores using NetworkX.
4. Renders the result as HTML/JS in your browser via Streamlit's `components.html()`.

No network calls. No telemetry. No analytics. No third-party APIs.

## What the app does NOT do

- It does not send your `manifest.json` to any server.
- It does not contact any cloud API (OpenAI, Google, etc.).
- It does not write your `manifest.json` to disk. It is parsed in memory and discarded when the app stops.
- It does not require an account, login, or API key.
- It does not track who you are.

The only external network requests the app makes are:

1. **Google Fonts** (fonts.googleapis.com / fonts.gstatic.com) — to load the Inter and JetBrains Mono web fonts for the UI. This is a standard practice and does not transmit any of your data. To block this, run with offline fonts (see "Hardening" below).
2. **Streamlit's component runtime** (streamlit.io) — to load the static JS for `components.html()` and `streamlit-js-eval`. Same as above — no data is sent.

If you want zero outbound traffic, see the **Hardening** section below.

## Why this app is local-only

A dbt `manifest.json` typically contains:

- All model, source, and seed names in your project
- Schema and database names (which can reveal your data warehouse provider and account IDs)
- Compiled SQL (which can reveal business logic, joins, and transformations)
- Column descriptions (which can contain business context, PII hints, etc.)
- Test definitions and macros

This is sensitive metadata. We chose local-first because:

- **No risk of accidental exposure** — no server, no public URL, no leaked credentials
- **No vendor lock-in** — you own the data, you own the runtime
- **No usage limits** — process manifests as large as you want, no tier restrictions
- **Auditability** — you can read every line of the code that touches your data

## Hardening (optional)

### 1. Block all outbound network traffic

If you want the app to make zero outbound calls:

- **Run on a machine with no internet** — the app will still work, but the UI will use fallback system fonts instead of Inter/JetBrains Mono.
- **Use a firewall rule** to block Python's outbound traffic (e.g. `pf` on macOS, `iptables` on Linux, Windows Defender Firewall on Windows).

### 2. Run in an isolated environment

For extra paranoia, run inside a container or VM with no network access:

```bash
docker run -it --network none -v $PWD:/data python:3.11-slim bash
# Inside container:
cd /data/cascade-data/cascade-rebuild
pip install -r requirements.txt
streamlit run app.py
```

### 3. Audit the code

The full source is in this repo. Before uploading your real `manifest.json`, you can:

- `grep -r "requests\\|httpx\\|urllib\\|http" lineage/ ui/ app.py` — should only find `streamlit.components.v1.html` references, no actual HTTP client calls.
- `grep -r "open\\|write" lineage/` — only `parser.py` reads `manifest.json` files. Nothing writes.

### 4. Verify what the app actually does

Run with strace (Linux) or dtrace (macOS) to see every system call:

```bash
# Linux
strace -f -e trace=open,openat,connect,sendto -o /tmp/cascade.trace streamlit run app.py
# Then upload a manifest, then Ctrl+C
grep -v "streamlit\\|font" /tmp/cascade.trace | head -50
```

You should see `open()` calls for the manifest file you uploaded, and no `connect()` calls except to `localhost:8502` (the app's own server).

## About the example `profiles.yml`

The `examples/jaffle_shop_minimal/profiles.yml` file uses dbt's standard `{{ env_var('XXX', 'default') }}` template syntax. The fallback value for the password is `'postgres'`. This is a **template default**, not a credential — it is only used if the `DBT_POSTGRES_PASSWORD` environment variable is unset, which would only happen on a local development machine. It is not a real password and grants no access to anything.

**Do not connect the example project to a database that uses default credentials in any non-localhost environment.** The example is for local learning only.

## Automated security tooling

This repository uses GitHub's free security tooling:

- **Dependabot** — `.github/dependabot.yml` is configured to check Python dependencies (`requirements.txt`) and GitHub Actions versions weekly. PRs are opened automatically when upgrades are available.
- **Secret scanning** — enabled in repository settings. If a credential pattern is committed, the push is blocked and an alert is opened.
- **Push protection** — same as above, blocks the push itself rather than alerting after the fact.

If you fork or copy this repo, please re-enable these features in your fork's **Settings → Code security and analysis**.

## If you find a security issue

Please open a private issue at https://github.com/noobigang/cascade-data/security or email the maintainers (see the GitHub profile). Do not open a public issue for security vulnerabilities.
