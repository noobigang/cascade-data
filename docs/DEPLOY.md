# Deployment Guide

This guide covers all ways to deploy Cascade: **Hugging Face Spaces** (recommended), **Docker**, **self-hosted**, and **CI/CD pipelines**.

---

## Hugging Face Spaces (Recommended)

Hugging Face Spaces provides free, auto-deploying static hosting. Every push to `main` automatically deploys a new version.

### Prerequisites

- A GitHub account with this repo forked
- A Hugging Face account (free)

### Steps

#### 1. Create a new Space

Go to [hf.co/new-space](https://huggingface.co/new-space):

- **Owner**: your personal account or an organization
- **SDK**: select **Static** (this is correct — Streamlit apps on HF Spaces use a proxy layer)
- **Space name**: `cascade-data` (or a custom name)
- **Hardware**: **CPU basic** is sufficient (2 CPU cores, 16 GB RAM)

> **Note**: "Static" SDK on HF Spaces does not mean a static site. It means HF provides a proxy that routes HTTP requests to your Streamlit app running on their servers. You still run `streamlit run app.py`.

#### 2. Link your GitHub repo

In your new Space settings:

1. Go to **Settings** → **Repository** → **Sync Git Repository**
2. Click **Link a GitHub repository**
3. Authorize Hugging Face to access GitHub (one-time)
4. Select your **fork** of `cascade-data`
5. Choose the branch: `main`

#### 3. Verify the sync

After linking, HF will pull the repo. You should see the build log in the Space's **Settings** → **Repository** tab.

#### 4. Enable automatic deployment

The sync is one-way (GitHub → HF). Enable **Auto-deployment**:
- In Space settings → **Repository** → toggle **Automatic Diffusion**
- HF will rebuild on every push to `main`

#### 5. Customize your Space

Edit `README.md` frontmatter to customize the Space card:

```yaml
---
title: My Company's Cascade
emoji: 🧬
sdk: docker
color: 0d1117
---
```

> **SDK note**: Use `sdk: docker` if you need a `Dockerfile`. Use `sdk: static` for the default Streamlit proxy. The existing README uses `sdk: static`.

---

## Docker

### Build the image

```bash
docker build -t cascade-data:latest .
```

### Run

```bash
docker run -p 8501:8501 \
  --name cascade \
  -v $(pwd)/logs:/app/logs \
  cascade-data:latest
```

Open [http://localhost:8501](http://localhost:8501).

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "cascade/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### Docker Compose

```yaml
version: "3.8"

services:
  cascade:
    build: .
    ports:
      - "8501:8501"
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
```

```bash
docker compose up -d
```

---

## GitHub Actions (CI/CD)

### Deploy to Self-Hosted Server

```yaml
# .github/workflows/deploy.yml
name: Deploy Cascade

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ghcr.io/${{ github.repository }}:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Deploy to server
        run: |
          ssh ${{ secrets.SERVER_HOST }} \
            "docker pull ghcr.io/${{ github.repository }}:latest && \
             docker stop cascade || true && \
             docker rm cascade || true && \
             docker run -d --name cascade \
               -p 8501:8501 \
               --restart unless-stopped \
               ghcr.io/${{ github.repository }}:latest"
```

### Deploy to Hugging Face Spaces via GitHub Actions

If you want to trigger an HF Space redeploy after each push (in addition to or instead of HF's built-in sync):

```yaml
# .github/workflows/hf-deploy.yml
name: Trigger HF Space Rebuild

on:
  push:
    branches: [main]

jobs:
  trigger-hf:
    runs-on: ubuntu-latest
    steps:
      - name: Trigger HF Space rebuild
        run: |
          curl -X POST https://huggingface.co/api/spaces/${{ vars.HF_SPACE_ID }}/reload \
            -H "Authorization: Bearer ${{ secrets.HF_TOKEN }}"
```

Create `HF_TOKEN` as a GitHub Actions secret with a HF write token from [hf.co/settings/tokens](https://huggingface.co/settings/tokens).

---

## Self-Hosted (Bare Metal / VM)

```bash
# Install Python 3.9+
sudo apt update
sudo apt install -y python3.11 python3.11-venv git

# Clone
git clone https://github.com/noobigang/cascade-data.git
cd cascade-data

# Venv
python3.11 -m venv .venv
source .venv/bin/activate

# Install
pip install -r requirements.txt

# Run as service (systemd)
sudo tee /etc/systemd/system/cascade.service <<EOF
[Unit]
Description=Cascade Data Lineage
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/cascade-data
ExecStart=/opt/cascade-data/.venv/bin/streamlit run cascade/app.py --server.port=8501 --server.address=127.0.0.1
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable cascade
sudo systemctl start cascade
```

Then proxy through nginx:

```nginx
server {
    listen 443 ssl;
    server_name cascade.yourcompany.com;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `CASCADE_MAX_NODES` | `50000` | Max nodes to parse before warning |
| `CASCADE_LOG_LEVEL` | `INFO` | Logging verbosity |
| `CASCADE_ENABLE_TELEMETRY` | `false` | Anonymous usage stats (opt-in) |

---

## Troubleshooting

### HF Space build fails

- Check the build log in Space **Settings** → **Repository**
- Ensure `requirements.txt` lists exact versions, not ranges
- Test locally: `pip install -r requirements.txt` must succeed

### App loads but no DAG renders

- Check browser console for JavaScript errors
- PyVis requires the browser to load the vis.js CDN — ensure internet access in the deployment environment

### Large manifest (> 10k nodes) is slow

- Increase HF Space hardware tier to **CPU upgrade** or **T4 small**
- Set `CASCADE_MAX_NODES` to cap parsing

### "Static" vs "Docker" SDK on HF Spaces

Use **Static** for the default Streamlit proxy (simpler, no Dockerfile needed). Use **Docker** if you need custom system packages, GPU access, or a non-Streamlit app.