# Déploiement — CRIG Rugby Display

Dépôt : https://github.com/Stefferle/crig-rugby-display

## 1. Sur le PC dev — commit / push

```bash
cd /home/stephane/Documents/crig-rugby-display

# vérifier que les tests passent avant de commiter
.venv/bin/python -m pytest -q

git status
git add <fichiers modifiés>          # éviter "git add -A" les yeux fermés
git commit -m "Description du changement"
git push
```

`.venv/`, `data/`, `output/`, `logs/`, `__pycache__/` et `.pytest_cache/` sont exclus via `.gitignore` — rien à faire de spécial pour eux.

## 2. Sur le Raspberry Pi (Anthias) — première installation

```bash
# dépendances système
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git

# récupération du code
cd /home/pi
git clone https://github.com/Stefferle/crig-rugby-display.git
cd crig-rugby-display

# environnement virtuel (obligatoire sur Raspberry Pi OS Bookworm, PEP 668)
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

# test manuel avant d'automatiser
.venv/bin/python -m crig_rugby run
# → vérifier http://localhost:8090/ puis Ctrl+C
```

### Activer le service systemd

```bash
sudo cp systemd/crig-rugby.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now crig-rugby
sudo systemctl status crig-rugby
journalctl -u crig-rugby -f      # logs en direct
```

### Brancher sur Anthias

Dans l'interface Anthias, ajouter une asset **"Web Page"** pointant vers `http://localhost:8090/` — le rotateur intégré (`index.html`) gère déjà l'alternance entre les 4 catégories, une seule asset suffit.

## 3. Sur le Raspberry Pi — mise à jour lors d'une nouvelle version

```bash
cd /home/pi/crig-rugby-display
git pull

# si requirements.txt a changé
.venv/bin/pip install -r requirements.txt

sudo systemctl restart crig-rugby
journalctl -u crig-rugby -f      # vérifier que ça redémarre sans erreur
```
