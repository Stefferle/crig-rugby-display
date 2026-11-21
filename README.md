# CRIG Rugby Display

Affichage dynamique des résultats, classements et prochains matchs des équipes du **CRIG (Illkirch Graffenstaden)**, destiné à un écran piloté par un Raspberry Pi sous [Anthias](https://anthias.screenly.io/).

Les données sont récupérées sur [coeurdurugby.com](https://coeurdurugby.com) (scraping), mises en cache, puis rendues en pages HTML statiques servies par un petit serveur Flask.

## Pages générées

| URL | Contenu |
|---|---|
| `/` (`index.html`) | Rotateur : fait défiler les pages catégorie (durée réglée par `rotation_seconds`) |
| `/<slug>.html` | Une page par catégorie (`f2`, `fb`, `f1f`, `r3`, `u18`) : classement, dernier résultat, prochain match. En pré-saison : clubs engagés et premier match |
| `/agenda.html` | Les 5 prochains matchs toutes catégories confondues ; les « doublettes » (ex. F2 + FB contre le même adversaire le même jour) sont regroupées sur une ligne |
| `/api/crig.json` | Export JSON des mêmes données, pour un site tiers (ex. WordPress). Format : [docs/export-json.md](docs/export-json.md) |
| `/healthz` | Contrôle de vie (`{"status": "ok"}`) |

## Installation (poste de dev)

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest -q
```

## Utilisation

```bash
.venv/bin/python -m crig_rugby scrape     # scrape toutes les catégories et met à jour le cache (pas de rendu)
.venv/bin/python -m crig_rugby generate   # régénère les pages depuis le cache, sans réseau
.venv/bin/python -m crig_rugby serve      # serveur web seul
.venv/bin/python -m crig_rugby run        # scrape + rendu, puis planificateur + serveur (production)
```

Puis ouvrir http://localhost:8090/.

Option globale : `--config chemin/vers/config.yaml` (défaut : `./config.yaml`).

## Configuration

### `config.yaml`

- `team_name` : nom exact du club tel qu'écrit sur coeurdurugby.com (sert à repérer la ligne CRIG).
- `club_aliases` : noms affichés à la place des noms du site (affichage uniquement).
- `club_logo_overrides` : logo de remplacement pour un club (fichier dans `static/img/logos/` ou URL externe).
- `competitions` : une entrée par catégorie : `slug` (nom du fichier de sortie, ne pas le changer), `label`, `resultats_url` (page de la poule), `equipe_url` (fiche équipe CRIG), `heure_habituelle` (heure par défaut sur l'agenda).
- `server` : `port`, `rotation_seconds`.
- `schedule` : le week-end, un scrape toutes les `weekend_interval_minutes` entre `weekend_start` et `weekend_end` ; en semaine, un scrape par jour à `weekday_daily_hour` (fuseau Europe/Paris).
- `scraping` : `request_timeout`, `request_delay_seconds` (pause entre deux requêtes pour ménager le site).
- `export` : `public_base_url`, URL publique du serveur, pour rendre absolus dans l'export JSON les logos en chemin relatif.

### `overrides.yaml`

Corrections manuelles pour un match dont la reprogrammation n'apparaît pas encore sur coeurdurugby.com. Chaque entrée indique `slug`, `home_team` et `away_team` (noms **exacts du site**, avant alias, dans l'ordre domicile/extérieur d'origine), puis tout ou partie de :
- `date_label` (ex. `"samedi 7 novembre 2026"`) ;
- `heure` ;
- `inverser: true` pour un match inversé, joué chez le club qui devait se déplacer. Domicile/extérieur (noms, scores, logos) sont alors permutés à l'affichage. On décrit toujours le match dans l'ordre **avant** inversion. Pour inverser aussi le match retour, il faut lui ajouter sa propre entrée.
- `score` (ex. `"25-23"`) pour forcer le score, exprimé dans l'ordre **affiché** (donc après inversion). Utile quand le site garde l'ordre d'origine d'un match inversé mais saisit le score dans l'ordre réellement joué : l'inversion seule donnerait alors le mauvais vainqueur. Le classement, lui, reste celui du site.

La section `exclusions_classement` écarte du classement (et des clubs engagés en pré-saison) un club que le site rattache à tort à la poule : chaque entrée indique `slug` et `equipe` (nom **exact du site**). Les clubs classés derrière remontent d'autant de places.

La section `ajustements_points` corrige un classement faux : chaque entrée indique `slug`, `equipe` (nom **exact du site**) et `points` à ajouter ou retrancher (ex. `-2`). Le tableau est alors retrié par points ; à égalité, l'ordre du site est conservé. L'ajustement déjà appliqué est mémorisé dans le cache, il ne se cumule donc pas d'un `generate` à l'autre, et retirer l'entrée rend au club ses points d'origine. À retirer dès que le site a corrigé, sinon la correction s'ajouterait à la sienne.

Le fichier est relu à chaque cycle, donc pas besoin de redémarrer le service. Une fois le site à jour, on retire l'entrée.

## Résilience

Si le scraping d'une catégorie échoue, son dernier snapshot en cache (`data/cache/`) reste affiché avec un bandeau « Données non rafraîchies ». Les journaux sont écrits dans `logs/crig-rugby.log` (rotation à 1 Mo).

## Structure

```
crig_rugby/
  cli.py        commandes scrape / generate / serve / run
  config.py     chargement de config.yaml
  scraper.py    parsing HTML de coeurdurugby.com
  pipeline.py   orchestration scrape → overrides → cache, repli sur le cache en cas d'échec
  overrides.py  corrections manuelles (overrides.yaml)
  cache.py      persistance JSON dans data/cache/
  render.py     rendu Jinja2 vers output/
  export.py     export JSON vers output/api/crig.json
  scheduler.py  planification APScheduler
  server.py     serveur Flask
  dates.py      parsing des dates en français
templates/      gabarits Jinja2 (category, agenda, rotator, base)
static/         CSS, polices, logos
tests/          tests de parsing sur des pages réelles figées (fixtures/)
systemd/        unité systemd pour le Raspberry Pi
```

## Déploiement

Voir [DEPLOY.md](DEPLOY.md) (installation sur le Pi, service systemd, branchement sur Anthias, mises à jour).
