# Deployment Guide — Market-Sync AI

## Option 1: Oracle Cloud Always Free (Recommended)

Oracle Cloud has an **Always Free** tier with a powerful ARM VM — perfect for this app.

### Step 1: Create an Oracle Cloud Account

1. Go to [cloud.oracle.com](https://cloud.oracle.com) and sign up
2. You get **Always Free** resources including:
   - **VM.Standard.A1.Flex** — up to 4 ARM OCPUs + 24GB RAM (free forever)
   - **Oracle Autonomous Database** (you already have this set up)
   - 200GB block storage

### Step 2: Create a Free VM

1. Go to **Compute → Instances → Create Instance**
2. Choose:
   - Shape: **VM.Standard.A1.Flex** (Ampere ARM)
   - OCPUs: **2** (use 2 of your 4 free)
   - Memory: **12 GB**
   - OS: **Oracle Linux 8** or **Ubuntu 22.04**
3. Download your SSH key pair
4. Note the **public IP address** after creation

### Step 3: Set Up the VM

```bash
# SSH into your VM
ssh -i your-key.pem opc@<YOUR_VM_PUBLIC_IP>

# Install Docker
sudo dnf install -y dnf-utils
sudo dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker opc
# Log out and back in for group to take effect

# Install git
sudo dnf install -y git
```

### Step 4: Deploy the App

```bash
# Clone your repo (or scp files)
git clone <YOUR_REPO_URL> marketsync
cd marketsync

# Create the .env file for Oracle DB
cat > backend/.env << 'EOF'
ORACLE_DSN=your_tns_connection_string
ORACLE_USER=ADMIN
ORACLE_PASSWORD=your_password
ORACLE_WALLET_DIR=/app/wallet
EOF

# Copy your Oracle wallet to the VM
# scp -i your-key.pem -r Wallet_*.zip opc@<IP>:~/marketsync/wallet/

# Unzip wallet into wallet/ directory
mkdir -p wallet && unzip Wallet_*.zip -d wallet/

# Build and start
docker compose up -d --build

# Check logs
docker compose logs -f
```

### Step 5: Open Firewall

```bash
# On the VM
sudo firewall-cmd --permanent --add-port=80/tcp
sudo firewall-cmd --reload

# In OCI Console:
# Networking → Virtual Cloud Networks → your VCN → Security Lists
# Add Ingress Rule: Source 0.0.0.0/0, TCP, Port 80
```

Your app is now live at `http://<YOUR_VM_PUBLIC_IP>`

### Step 6: (Optional) Add a Domain + HTTPS

```bash
# Install certbot for free SSL
sudo dnf install -y certbot python3-certbot-nginx

# Point your domain's A record to the VM IP, then:
sudo certbot --nginx -d yourdomain.com
```

---

## Option 2: Quick Deploy with Railway/Render

If you want a simpler one-click deploy:

### Railway (railway.app)
1. Push code to GitHub
2. Go to [railway.app](https://railway.app), connect GitHub
3. Add a new project → Deploy from repo
4. Add environment variables from your `.env`
5. Railway auto-detects the Dockerfile

### Render (render.com)
1. Push code to GitHub
2. Create a **Web Service** for the backend (Dockerfile)
3. Create a **Static Site** for the frontend (`npm run build`)
4. Add environment variables

---

## Option 3: Run Locally for Demo

```bash
# Terminal 1 — Backend
cd backend && source venv/bin/activate
python -m uvicorn backend.api.main:app --port 8000

# Terminal 2 — Frontend
cd frontend && npm run dev
```

Open http://localhost:5173
