# Export JSON des résultats du CRIG

Ce fichier JSON contient les données affichées sur l'écran du club : classements, derniers résultats, prochains matchs et agenda, pour chaque catégorie du CRIG (Illkirch Graffenstaden). Il est destiné à un site tiers, par exemple WordPress, qui veut afficher ces informations sans les recalculer.

## Où trouver le fichier

- **Pendant le POC** : un fichier d'exemple, `crig.json`, vous est transmis. Il contient des données réelles de la saison en cours. Vous pouvez le poser n'importe où (dossier du plugin, `wp-content/uploads/`).
- **Ensuite** : il sera publié à une URL fixe, de la forme `https://<serveur>/api/crig.json`. Le mode de publication reste à décider : fichier envoyé vers le WordPress, ou fichier lu sur un serveur public. Pour votre code, seule l'URL ou le chemin changera.

## Fréquence de mise à jour

Le fichier est régénéré après chaque récupération des données sur coeurdurugby.com :

- **le week-end** : toutes les 10 minutes, de 10 h à 20 h ;
- **en semaine** : une fois par jour, à 7 h.

Garder le JSON en cache côté WordPress une quinzaine de minutes (*transient*) suffit largement.

## Ce que le JSON contient déjà

Les règles d'affichage sont déjà appliquées. Il ne faut pas les refaire côté WordPress :

- les corrections manuelles de matchs (date, heure ou lieu changés) ;
- les noms d'affichage des clubs (`display_name`) et les logos de remplacement ;
- les matchs non joués dont la date est passée (par exemple un forfait) sont retirés de `next_match`, de `upcoming` et de l'agenda ;
- dans l'agenda, deux catégories qui jouent contre le même adversaire le même jour sont regroupées en une seule entrée, avec un horaire par catégorie ;
- l'ordre domicile/extérieur est celui de la Fédération. Le CRIG n'est **pas** systématiquement mis en premier.

## Structure

```jsonc
{
  "schema_version": 1,
  "generated_at": "2026-11-10T15:15:43+00:00",
  "source": "coeurdurugby.com",
  "team_name": "Illkirch Graffenstaden",
  "categories": [ /* une entrée par catégorie, voir ci-dessous */ ],
  "agenda": {
    "updated_at": "2026-11-10T07:00:00+00:00",
    "stale": false,
    "matches": [ /* les 5 prochains matchs, toutes catégories confondues */ ]
  }
}
```

### Champs généraux

| Champ | Type | Description |
|---|---|---|
| `schema_version` | entier | Version du format. Elle n'augmente que si un champ est renommé ou retiré. Les ajouts de champs ne la changent pas : ignorez simplement les champs que vous ne connaissez pas. |
| `generated_at` | horodatage ISO 8601, UTC | Date de génération du fichier. |
| `source` | texte | Source des données. À créditer (« Données : coeurdurugby.com »). |
| `team_name` | texte | Nom du club suivi, tel qu'il est écrit sur le site source. |

### Équipe (objet `team`)

On retrouve cet objet partout où une équipe apparaît.

| Champ | Type | Description |
|---|---|---|
| `name` | texte | Nom brut du site source. Il est stable : c'est lui qu'il faut utiliser pour comparer ou identifier une équipe. |
| `display_name` | texte | Nom à afficher (par exemple « CRIG » au lieu de « Illkirch Graffenstaden »). |
| `logo` | URL ou `null` | Logo du club. Il est le plus souvent hébergé sur coeurdurugby.com. Pendant le POC, un logo peut être un chemin relatif (`/static/...`) : il ne s'affichera pas chez vous, prévoyez un affichage sans image. |
| `is_crig` | booléen | Vrai pour le CRIG. Sert à mettre sa ligne en valeur. |

### Match (objet `match`)

| Champ | Type | Description |
|---|---|---|
| `date` | `AAAA-MM-JJ` ou `null` | Date du match. À utiliser pour trier et formater. |
| `date_label` | texte | Date telle qu'elle est écrite sur le site source (« samedi 14 novembre 2026 »). |
| `journee` | texte ou `null` | Journée du championnat (« J8 »). |
| `heure` | `HH:MM` ou `null` | Heure du coup d'envoi, si elle est connue. |
| `home`, `away` | objets `team` | Équipe qui reçoit et équipe qui se déplace. |
| `home_score`, `away_score` | texte ou `null` | Scores, présents seulement si le match est joué. Ce sont des chaînes de caractères, pas des nombres. |
| `played` | booléen | Vrai si le match a été joué. |
| `inverted` | booléen | Vrai si le match a été déplacé chez l'autre club par rapport au calendrier officiel. Champ purement informatif : `home` et `away` sont déjà corrigés. |

### Catégorie (élément de `categories`)

| Champ | Type | Description |
|---|---|---|
| `slug` | texte | Identifiant stable de la catégorie : `f2`, `fb`, `f1f`, `r3` ou `u18`. C'est lui qu'il faut utiliser dans un shortcode. |
| `label` | texte | Libellé complet (« Séniors M - Fédérale 2 - Poule 2 »). |
| `short_label` | texte | Libellé sans la poule (« Séniors M - Fédérale 2 »). |
| `updated_at` | horodatage ISO 8601, UTC, ou `null` | Dernière récupération réussie des données de cette catégorie. |
| `stale` | booléen | Vrai si la dernière récupération a échoué : les données affichées sont alors celles de la fois précédente. On peut le signaler (« Données non rafraîchies »). |
| `pre_season` | booléen | Vrai si la saison n'a pas commencé. `standings` est alors vide. Affichez plutôt `engaged_clubs` et `next_match`, qui est le premier match de la saison. |
| `standings` | liste | Classement, dans l'ordre. Chaque ligne contient `rank`, `team` (objet `team`), `points`, `played` (joués), `won`, `drawn`, `lost`, `scored_for` (points marqués), `scored_against` (points encaissés) et `diff`. Toutes les valeurs sont des chaînes de caractères. |
| `last_result` | `match` ou `null` | Dernier match joué. |
| `next_match` | `match` ou `null` | Prochain match. Il est égal à `upcoming[0]`, sauf en pré-saison. |
| `upcoming` | liste de `match` | Tous les matchs à venir, dans l'ordre chronologique. |
| `engaged_clubs` | liste de `team` | Clubs de la poule. Ce champ n'est rempli qu'en pré-saison. |

### Agenda (élément de `agenda.matches`)

L'agenda contient les 5 prochains matchs du CRIG, toutes catégories confondues, triés par date.

| Champ | Type | Description |
|---|---|---|
| `date`, `date_label` | | Comme dans l'objet `match`. |
| `home`, `away` | objets `team` | Les deux équipes. |
| `slots` | liste | Un élément par catégorie qui joue ce match : `slug`, `category_label` et `heure`. Il y a plusieurs éléments quand plusieurs catégories affrontent le même adversaire le même jour (par exemple la F2 à 15:15 et la FB à 13:30). |

Les horaires de l'agenda sont toujours remplis. Si le site source ne donne pas l'heure, on utilise l'heure habituelle de la catégorie.

## Pistes de shortcodes pour le POC

Ce ne sont que des suggestions, à discuter :

- `[crig_classement categorie="f2"]` : le classement, avec la ligne du CRIG mise en valeur (`is_crig`) ;
- `[crig_dernier_resultat categorie="f2"]` et `[crig_prochain_match categorie="f2"]` ;
- `[crig_agenda nb="5"]` : les prochains matchs toutes catégories confondues.

Le JSON est à lire côté serveur (`wp_remote_get()` ou lecture du fichier), et non dans le navigateur des visiteurs.
