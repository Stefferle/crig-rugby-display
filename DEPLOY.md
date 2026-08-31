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
cd /home/crig
git clone https://github.com/Stefferle/crig-rugby-display.git
cd crig-rugby-display

# environnement virtuel (obligatoire sur Raspberry Pi OS Bookworm, PEP 668)
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

# test manuel avant d'automatiser
.venv/bin/python -m crig_rugby run
```

Le Pi n'a pas d'interface graphique locale (accès en SSH) — deux façons de vérifier que ça tourne, dans un autre terminal :

```bash
# depuis le Pi lui-même : suffisant pour confirmer que le serveur répond
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8090/healthz
curl -s http://localhost:8090/f2.html | head -30

# depuis un vrai navigateur (PC/téléphone sur le même réseau) : pour juger du rendu visuel
hostname -I                      # récupère l'IP LAN du Pi
# puis ouvrir http://<IP-du-Pi>:8090/ dans le navigateur
```

Ctrl+C sur le Pi pour arrêter le test manuel une fois vérifié.

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

Alternative : ajouter chaque catégorie comme asset séparée (pour gérer la durée d'affichage ou l'ordre directement depuis le planning Anthias plutôt que via `rotation_seconds` dans `config.yaml`) :

| Catégorie | URL |
|---|---|
| Rotateur (les 4 catégories) | `http://localhost:8090/` |
| Séniors M - Fédérale 2 | `http://localhost:8090/f2.html` |
| Séniors M - Fédérale B | `http://localhost:8090/fb.html` |
| Séniors F - Fédérale 1 | `http://localhost:8090/f1f.html` |
| Séniors - Régionale 3 | `http://localhost:8090/r3.html` |

## 3. Sur le Raspberry Pi — mise à jour lors d'une nouvelle version

```bash
cd /home/crig/crig-rugby-display
git pull

# si requirements.txt a changé
.venv/bin/pip install -r requirements.txt

sudo systemctl restart crig-rugby
journalctl -u crig-rugby -f      # vérifier que ça redémarre sans erreur
```
