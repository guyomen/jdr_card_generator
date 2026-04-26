# JDR Card Generator

Générateur de cartes JDR au format PDF avec support des images générées par IA.

## Caractéristiques

- **Génération PDF** : Cartes imprimables au format A4 avec mises en page configurables
- **Gestion d'images IA** : Support de plusieurs fournisseurs d'images
  - Pollinations (en ligne, gratuit)
  - HuggingFace Diffusers (local, GPU/CPU)
  - Automatic1111 / ComfyUI (API locale)
  - OpenAI DALL-E 3
- **Palettes de couleurs** : Thèmes différents pour armes, armures et équipements
- **Cache d'images** : Évite de régénérer les images existantes
- **Format JSON** : Données simples et transportables

## Installation

### Installation standard

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

### CLI (après installation)

```bash
# Générer des cartes sans images
jdr-cards --arme data/armes.json --armure data/armures.json --autre data/equipements.json

# Générer des cartes avec images (fournisseur par défaut)
jdr-cards --arme data/armes.json --generate_image

# Utiliser HuggingFace Diffusers local
jdr-cards --arme data/armes.json --generate_image --provider local

# Utiliser une API locale (Automatic1111)
jdr-cards --arme data/armes.json --generate_image --provider localapi --api_url http://localhost:7860

# Utiliser OpenAI DALL-E
jdr-cards --arme data/armes.json --generate_image --provider openai --api_key sk-...
```

### Module Python

```python
from card_generator import CardGenerator
from pathlib import Path

gen = CardGenerator()
cards = gen.load_cards_from_files(
    armes="data/armes.json",
    armures="data/armures.json",
    autres="data/equipements.json"
)

gen.generate_cards(cards, output_path="output/cartes.pdf")
```

## Format JSON

### Armes

```json
[
  {
    "nom": "Épée longue",
    "sous_type": "Épée",
    "dm": "1d8+2",
    "portee": "Mêlée",
    "regles": "Lame d'acier forgée par des maîtres armuriers.",
    "image": "path/to/image.png"
  }
]
```

### Armures

```json
[
  {
    "nom": "Armure de chevalier",
    "sous_type": "Plaques d'acier",
    "def": "+4",
    "max_agi": "-1",
    "info": "Armure complète de plaques d'acier."
  }
]
```

### Équipements

```json
[
  {
    "nom": "Torche magique",
    "sous_type": "Accessoire",
    "stats": {
      "Portée lumière": "20m",
      "Durée": "Infini"
    },
    "regles": "Éclaire sans flamme."
  }
]
```

## Structure du projet

```
card-generator/
├── pyproject.toml          # Configuration du projet
├── README.md               # Ce fichier
├── .gitignore              # Fichiers à ignorer
├── card_generator/         # Package principal
│   ├── __init__.py
│   ├── __main__.py         # Permet: python -m card_generator
│   ├── cli.py              # Interface en ligne de commande
│   ├── generator.py        # Logique principale
│   └── providers.py        # Providers d'images (optionnel)
├── data/                   # Données d'exemple
│   ├── armes.json
│   ├── armures.json
│   └── equipements.json
├── tests/                  # Tests unitaires
└── output/                 # Résultats (généré)
    └── cartes_jdr.pdf
```

## Providers d'images IA

### Pollinations (par défaut)

- **Avantage** : Gratuit, sans configuration
- **Inconvénient** : Limites de taux, serveur externe
- **Installation** : Rien à faire

### HuggingFace Diffusers (Local)

- **Avantage** : Contrôle total, GPU accéléré, gratuit
- **Inconvénient** : Installation complexe, modèles volumineux
- **Installation** :
  ```bash
  pip install ".[images-local]"
  # AMD/Intel WSL2
  pip install torch-directml
  ```
- **Premiers pas** : Le modèle (~2 Go) se télécharge au premier lancement

### Automatic1111 (API locale)

- **Avantage** : Interface Web, modèles multiples
- **Inconvénient** : Configuration supplémentaire
- **Setup** :
  ```bash
  # Installer Automatic1111
  git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui
  cd stable-diffusion-webui
  ./webui.sh --api
  ```

### OpenAI DALL-E 3

- **Avantage** : Qualité élevée, modèle avancé
- **Inconvénient** : Payant (coûts API)
- **Installation** : `pip install ".[images-openai]"`

## Dépannage

### Erreur : "ModuleNotFoundError: No module named 'card_generator'"

Installez le package en mode développement :
```bash
pip install -e .
```

### Erreur GPU : "No GPU detected"

Pour NVIDIA CUDA :
```bash
pip install --upgrade torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

Pour AMD/Intel (WSL2) :
```bash
pip install torch-directml
```

### Erreur API locale : "Impossible de joindre l'API locale"

Vérifiez que votre serveur (Automatic1111, ComfyUI) tourne sur le port correct :
```bash
jdr-cards --arme data/armes.json --generate_image --provider localapi --api_url http://localhost:7860
```

## Développement

```bash
# Installer en mode édition avec dépendances de développement
pip install -e ".[dev]"

# Formater le code
black card_generator/ tests/

# Vérifier la qualité
flake8 card_generator/ tests/

# Lancer les tests
pytest
```

## Licence

MIT

## Auteur

À compléter dans pyproject.toml
