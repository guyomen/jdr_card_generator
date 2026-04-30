"""
Interface en ligne de commande pour le générateur de cartes JDR
"""

import sys
import os
import argparse
from .generator import CardGenerator
from .exceptions import CardGeneratorError


def _ensure_hf_login():
    """Vérifie que l'utilisateur est authentifié sur HuggingFace Hub"""
    try:
        from huggingface_hub import get_token, login
    except ImportError:
        return  # huggingface_hub pas installé, on laisse diffusers gérer l'erreur plus tard

    if get_token():
        return

    print("🔑  Aucun token HuggingFace détecté.")
    print("    Un token permet des téléchargements plus rapides et l'accès aux modèles privés.")
    print()
    try:
        login()
    except Exception:
        print("⚠️   Login ignoré — les téléchargements seront anonymes (débit limité).")
        print()


def parse_args():
    """Parse les arguments de la ligne de commande"""
    parser = argparse.ArgumentParser(
        description="Générateur de cartes JDR (PDF imprimable)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
providers:
  pollinations   En ligne, gratuit, sans clé (défaut)
  local          HuggingFace diffusers en local
                   pip install diffusers torch accelerate pillow
                   Modèle par défaut : stabilityai/sd-turbo (~2 Go)
                   GPU (CUDA) utilisé automatiquement si disponible
  localapi       API locale compatible Automatic1111
                   Lancer A1111 avec --api, puis pointer avec --api_url
                   ComfyUI : utiliser un wrapper A1111-compatible
  openai         DALL-E 3, requiert --api_key

exemples:
  jdr-cards --input data/armes.json
  jdr-cards --input data --generate_image --provider local
  jdr-cards --arme data/armes.json --armure data/armures.json
  jdr-cards --arme data/armes.json --generate_image --provider local --model stabilityai/sdxl-turbo
  jdr-cards --arme data/armes.json --generate_image --provider localapi --api_url http://localhost:7860
  jdr-cards --arme data/armes.json --generate_image --provider openai --api_key sk-...
        """,
    )

    parser.add_argument("--input", metavar="PATH", help="Fichier JSON ou dossier contenant les JSONs (auto-détecte le type)")
    parser.add_argument("--arme", metavar="FICHIER", help="Fichier JSON des armes")
    parser.add_argument("--armure", metavar="FICHIER", help="Fichier JSON des armures")
    parser.add_argument("--autre", metavar="FICHIER", help="Fichier JSON des équipements")
    parser.add_argument(
        "--out",
        metavar="DOSSIER",
        default=".",
        help="Dossier de sortie (défaut : .)",
    )
    parser.add_argument(
        "--generate_image",
        action="store_true",
        help="Génère une image IA par carte",
    )
    parser.add_argument(
        "--provider",
        default="pollinations",
        choices=["pollinations", "local", "localapi", "openai"],
        help="Fournisseur d'images (défaut : pollinations)",
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
        help="Cache des images générées (défaut : .image_cache)",
    )

    return parser.parse_args()


def main():
    """Point d'entrée principal"""
    args = parse_args()

    # Validation : soit --input, soit --arme/--armure/--autre
    if args.input and any([args.arme, args.armure, args.autre]):
        print("❌  Utilise soit --input, soit --arme/--armure/--autre, pas les deux")
        sys.exit(1)

    if not args.input and not any([args.arme, args.armure, args.autre]):
        print("❌  Spécifie soit --input (fichier/dossier) soit --arme/--armure/--autre")
        sys.exit(1)

    if args.generate_image and args.provider == "openai" and not args.api_key:
        print("❌  --provider openai requiert --api_key")
        sys.exit(1)

    # Vérifie le login HuggingFace pour les providers qui téléchargent des modèles
    if args.generate_image and args.provider == "local":
        _ensure_hf_login()

    # Crée le générateur
    generator = CardGenerator(cache_dir=args.image_cache)

    try:
        # Charge les cartes
        if args.input:
            print(f"📁 Chargement depuis {args.input}...")
            cards = generator.load_cards_from_input(args.input)
        else:
            cards = generator.load_cards_from_files(
                armes=args.arme,
                armures=args.armure,
                autres=args.autre,
            )

        # Génère les images si demandé
        if args.generate_image:
            print(f"🎨  Génération images ({args.provider}) ...")
            generator.fetch_images_for_cards(
                cards,
                provider=args.provider,
                model=args.model,
                api_url=args.api_url,
                api_key=args.api_key,
            )

        # Génère le PDF
        output_file = f"{args.out}/cartes_jdr.pdf"
        generator.generate_cards(cards, output_path=output_file)

    except CardGeneratorError as e:
        print(f"❌  {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
