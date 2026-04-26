#!/usr/bin/env python3
"""
Script de test pour la génération d'images uniquement
Permet de tester les prompts et la génération sans créer les PDF
"""

import os
import sys
import argparse
import json

# IMPORTANT : définir avant TOUS les imports de diffusers/torch
os.environ["DIFFUSERS_DISABLE_CUDA_CUSTOM_OPS"] = "1"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from card_generator.providers import ImageProviderManager


def main():
    """Test de génération d'images"""
    parser = argparse.ArgumentParser(
        description="Test de génération d'image unique",
        epilog="""
exemples:
  ./test_images.py --prompt "A detailed longsword with engravings" --provider local
  ./test_images.py --prompt "A magical shield" --provider local --model stabilityai/sdxl-turbo
  ./test_images.py --prompt "A leather backpack" --provider pollinations
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--prompt", metavar="TEXTE", required=True, help="Prompt pour générer l'image")
    parser.add_argument(
        "--provider",
        default="local",
        choices=["pollinations", "local", "localapi", "openai"],
        help="Fournisseur d'images (défaut : local)",
    )
    parser.add_argument(
        "--model",
        default="stabilityai/sd-turbo",
        metavar="HF_MODEL_ID",
        help="Modèle HuggingFace pour --provider local",
    )
    parser.add_argument(
        "--api_url",
        default="http://localhost:7860",
        metavar="URL",
        help="URL de l'API locale (pour --provider localapi)",
    )
    parser.add_argument(
        "--api_key",
        metavar="CLE",
        help="Clé API (pour --provider openai)",
    )
    parser.add_argument(
        "--image_cache",
        default=".image_cache",
        metavar="DOSSIER",
        help="Cache des images (défaut : .image_cache)",
    )
    parser.add_argument(
        "--output",
        metavar="CHEMIN",
        help="Chemin du fichier de sortie (sinon sauvegardé dans le cache)",
    )

    args = parser.parse_args()

    if args.provider == "openai" and not args.api_key:
        print("❌  --provider openai requiert --api_key")
        sys.exit(1)

    print(f"\n📊 Test de génération d'image")
    print(f"🎨 Provider : {args.provider}")
    if args.provider == "local":
        print(f"📦 Modèle : {args.model}")
    print()

    # Crée une "carte" simple avec juste le prompt
    card = {
        "nom": "test_image",
        "description_ia": args.prompt,
        "type": "equipement",
    }

    # Génère l'image
    provider = ImageProviderManager(cache_dir=args.image_cache)

    kwargs = {}
    if args.provider == "localapi":
        kwargs["api_url"] = args.api_url
    elif args.provider == "openai":
        kwargs["api_key"] = args.api_key

    provider.fetch_images(
        [card],
        provider=args.provider,
        model=args.model,
        **kwargs,
    )

    # Copie vers le chemin de sortie si spécifié
    if args.output and card.get("image"):
        import shutil
        shutil.copy(card["image"], args.output)
        print(f"💾 Image sauvegardée : {args.output}")
    elif card.get("image"):
        print(f"💾 Image générée : {card['image']}")
    else:
        print(f"❌ Échec de la génération d'image")
        sys.exit(1)

    print(f"\n✅ Terminé !")


if __name__ == "__main__":
    main()
