# JDR Card Generator

Générateur de cartes JDR au format PDF avec support des images générées par IA.

## Caractéristiques

- **Génération PDF** : Cartes imprimables au format A4 avec repères de coupe
- **Templates personnalisables** : Couleurs et labels définis directement dans les fichiers JSON
- **Gestion d'images IA** : Support de plusieurs fournisseurs
  - Pollinations (en ligne, gratuit, sans clé)
  - HuggingFace Diffusers (local, GPU/CPU)
  - Automatic1111 / ComfyUI (API locale)
  - OpenAI DALL-E 3
- **Cache d'images** : Évite de régénérer les images existantes

## Installation

```bash
pip install .
```

### Avec support des images locales (GPU recommandé)

```bash
# NVIDIA CUDA
pip install ".[images-local]"

# AMD/Intel avec DirectML (WSL2/Windows)
pip install ".[images-local,images-directml]"

# OpenAI DALL-E 3
pip install ".[images-openai]"
```

## Usage

### Commande rapide (dev)

```bash
python run.py --input data
```

### CLI (après installation)

```bash
# Générer des cartes depuis un dossier (détecte le type via _meta)
jdr-cards --input data/

# Générer depuis un fichier spécifique
jdr-cards --input data/arme.json

# Fichiers séparés
jdr-cards --arme data/arme.json --armure data/armure.json --autre data/autre.json

# Avec images IA (Pollinations, gratuit)
jdr-cards --input data --generate_image

# Avec images locales (HuggingFace Diffusers)
jdr-cards --input data --generate_image --provider local

# Avec API locale (Automatic1111)
jdr-cards --input data --generate_image --provider localapi --api_url http://localhost:7860

# Avec OpenAI DALL-E
jdr-cards --input data --generate_image --provider openai --api_key sk-...
```

### Module Python

```python
from card_generator import CardGenerator

gen = CardGenerator()
cards = gen.load_cards_from_input("data/")
gen.generate_cards(cards, output_path="cartes_jdr.pdf")
```

## Format JSON

Chaque fichier JSON suit ce format :

```json
{
  "_meta": {
    "type": "arme",
    "template": {
      "label": "ARME",
      "header_bg": "#C17B7B",
      "header_fg": "#FFFFFF",
      "stats_bg": "#FAF0EC",
      "stats_fg": "#5A2A2A",
      "border": "#B09090",
      "tag_bg": "#D4A0A0",
      "tag_fg": "#3D1515"
    }
  },
  "items": [
    {
      "nom": "Épée longue",
      "sous_type": "Corps à corps",
      "dm": "1d8+FOR",
      "portee": "Mêlée",
      "regles": "Peut être tenue à une ou deux mains.",
      "description_ia": "basic long sword, medieval fantasy weapon..."
    }
  ]
}
```

### Champs `_meta`

| Champ | Description |
|-------|-------------|
| `type` | Type de carte : `arme`, `armure`, `equipement` (ou tout type custom) |
| `template` | Palette de couleurs de la carte (optionnel, des valeurs par défaut existent) |

### Clés du template

| Clé | Description |
|-----|-------------|
| `label` | Texte du badge de type (ex: "ARME", "SORT", "PIÈGE") |
| `header_bg` | Couleur de fond de l'en-tête |
| `header_fg` | Couleur du texte de l'en-tête |
| `stats_bg` | Couleur de fond du bloc stats |
| `stats_fg` | Couleur du texte des stats |
| `border` | Couleur des bordures |
| `tag_bg` | Couleur de fond du badge type |
| `tag_fg` | Couleur du texte du badge type |

### Champs par type de carte

**Armes** : `nom`, `sous_type`, `dm`, `portee`, `regles`, `description_ia`

**Armures** : `nom`, `sous_type`, `def`, `max_agi`, `regles`, `description_ia`

**Équipements** : `nom`, `sous_type`, `stats` (dict libre), `info`, `description_ia`

## HuggingFace — Configuration du token

Pour le provider `local`, le modèle est téléchargé depuis HuggingFace Hub (~2 Go pour sd-turbo).

Un token HuggingFace (gratuit) permet :
- Des téléchargements plus rapides (pas de limite de débit)
- L'accès aux modèles privés/gated

### Créer un token

1. Aller sur https://huggingface.co/settings/tokens
2. Créer un token avec le scope **Read** (lecture seule suffit pour les modèles publics)

### Configurer le token

```bash
# Option 1 : Login interactif (stocke le token localement)
huggingface-cli login

# Option 2 : Variable d'environnement
export HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxx        # Linux/Mac
$env:HF_TOKEN = "hf_xxxxxxxxxxxxxxxxxxxxx"      # PowerShell
```

> **Note** : Si aucun token n'est configuré, l'application proposera automatiquement le login interactif au lancement avec `--provider local`.

## Providers d'images IA

### Pollinations (par défaut)

- **Avantage** : Gratuit, sans configuration, sans GPU
- **Inconvénient** : Limites de taux, dépend d'un serveur externe

### HuggingFace Diffusers (local)

- **Avantage** : Contrôle total, pas de dépendance réseau après téléchargement
- **Inconvénient** : GPU recommandé, modèles volumineux (~2 Go)
- **Installation** : `pip install ".[images-local]"`
- **GPU supportés** : NVIDIA CUDA, AMD/Intel via DirectML

### Automatic1111 (API locale)

- **Avantage** : Interface Web, choix du modèle, réglages fins
- **Setup** : Lancer A1111 avec `--api` puis pointer avec `--api_url`

### OpenAI DALL-E 3

- **Avantage** : Haute qualité
- **Inconvénient** : Payant
- **Installation** : `pip install ".[images-openai]"`
- **Requiert** : `--api_key sk-...`

## Structure du projet

```
jdr_card_generator/
├── pyproject.toml
├── README.md
├── run.py                  # Point d'entrée dev
├── card_generator/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py              # Interface ligne de commande
│   ├── exceptions.py       # Exceptions métier
│   ├── generator.py        # Logique PDF + chargement JSON
│   └── providers.py        # Providers d'images IA
├── data/                   # Données d'exemple
│   ├── arme.json
│   ├── armure.json
│   └── autre.json
└── tests/
```

## Développement

```bash
pip install -e ".[dev]"
pytest
```

## Licence

MIT
