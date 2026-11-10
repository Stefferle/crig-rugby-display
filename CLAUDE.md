# CLAUDE.md

Ce fichier guide Claude Code sur ce dépôt. Vue d'ensemble : [README.md](README.md). Déploiement : [DEPLOY.md](DEPLOY.md).

## Commandes

```bash
.venv/bin/python -m pytest -q                 # tests (à lancer avant chaque commit)
.venv/bin/python -m crig_rugby generate       # rendu depuis le cache, sans réseau : pour itérer sur templates/CSS
.venv/bin/python -m crig_rugby scrape         # requêtes réelles vers coeurdurugby.com
.venv/bin/python -m crig_rugby serve          # http://localhost:8090/
```

Préférer `generate` à `scrape` pendant le dev : le site source est un tiers, il faut le solliciter le moins possible.

## Conventions

- Tout est en **français** : code commenté, docstrings, messages de log, messages de commit (impératif, ex. « Corrige… », « Ajoute… »).
- Les commentaires expliquent le *pourquoi* (souvent une particularité du site source). Garder ce niveau de détail.
- Ajouter les fichiers nommément plutôt que `git add -A` (cf. DEPLOY.md). `data/`, `output/` et `logs/` sont ignorés par git.

## Pièges connus

- **Noms d'équipe** : le scraping, le repérage du CRIG et `overrides.yaml` utilisent les noms *bruts* du site. `club_aliases` / `club_logo_overrides` ne servent qu'à l'affichage, dans les templates. Ne jamais comparer avec un nom aliasé.
- **Ordre domicile/extérieur** : on conserve toujours celui du site, sans jamais mettre le CRIG en tête.
- **Deux sources par catégorie** : la page de poule (`resultats_url`, qui a l'heure du match) et la fiche équipe (`equipe_url`, qui n'a pas l'heure ; d'où `heure_habituelle`). La fiche équipe peut mettre plusieurs jours à synchroniser un score. Pour cette raison, `pipeline.scrape_competition` complète les résultats depuis la page de poule et `render._build_agenda` écarte les matchs non joués dont la date est passée.
- **Pré-saison** : un classement vide *ou* rempli de zéros veut dire « saison non commencée ». On affiche alors les clubs engagés et le premier match.
- **Deux caches distincts** : `data/cache/<slug>.json` pour les pages catégorie et `data/cache/agenda_<slug>.json` pour l'agenda. Ne pas les fusionner.
- **Dates** : le site ne fournit que des libellés français (« samedi 7 novembre 2026 »). Toujours trier via `dates.parse_date_label`, jamais sur la chaîne brute.
- **Overrides** : réappliqués à chaque `scrape` *et* à chaque `generate`, sur des données déjà corrigées en cache : ils doivent rester idempotents. Le fichier `overrides.yaml` est versionné. Une inversion (`inverser: true`) permute les champs du `Match` et met `inverted=True`. La correspondance se fait toujours sur `Match.site_teams` (l'ordre d'origine du site), sinon un aller A-B inversé serait confondu avec le retour B-A.
- **Structure HTML du site** : elle change parfois (ex. `eqL`/`eqR` + `score-home`/`score-away` en octobre 2026). En cas de casse, rafraîchir la fixture concernée dans `tests/fixtures/`, la dater dans la docstring de `tests/test_scraper.py`, puis adapter `scraper.py`.

## Cible de production

Raspberry Pi sous Anthias, sans écran local (accès SSH), service systemd `crig-rugby` (utilisateur `crig`, `/home/crig/crig-rugby-display`). Anthias affiche `http://localhost:8090/`. Le CSS est pensé pour du 1920x1080 et dimensionné en `vw` (voir `static/css/theme.css`) : le rendu doit rester lisible à distance.
