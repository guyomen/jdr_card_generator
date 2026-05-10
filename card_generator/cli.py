"""
Interface en ligne de commande pour le générateur de cartes JDR
"""

import sys
import os
import argparse
from .generator import CardGenerator
from .exceptions import CardGeneratorError


def parse_args():
    """Parse les arguments de la ligne de commande"""
    parser = argparse.ArgumentParser(
        description="Générateur de cartes JDR (PDF imprimable)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
exemples:
  jdr-cards --input data_COFv2/
  jdr-cards --input data_COFv2/ --style data_COFv2/style.json
  jdr-cards --arme data/armes.csv --armure data/armures.csv --autre data/equipements.csv
        """,
    )

    parser.add_argument("--input", metavar="PATH", help="Fichier ou dossier contenant les cartes (JSON ou CSV)")
    parser.add_argument("--arme", metavar="FICHIER", help="Fichier des armes (JSON ou CSV)")
    parser.add_argument("--armure", metavar="FICHIER", help="Fichier des armures (JSON ou CSV)")
    parser.add_argument("--autre", metavar="FICHIER", help="Fichier des équipements (JSON ou CSV)")
    parser.add_argument(
        "--style",
        metavar="CHEMIN",
        help="Fichier de styles JSON (par défaut: cherche style.json dans le dossier input)",
    )
    parser.add_argument(
        "--out",
        metavar="DOSSIER",
        default=".",
        help="Dossier de sortie (défaut : .)",
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

    # Détermine le chemin de style
    style_path = args.style
    if not style_path and args.input and os.path.isdir(args.input):
        # Cherche style.json dans le dossier input
        potential_style = os.path.join(args.input, "style.json")
        if os.path.exists(potential_style):
            style_path = potential_style

    # Crée le générateur avec les styles
    generator = CardGenerator(style_path=style_path)

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

        # Génère le PDF
        output_file = f"{args.out}/cartes_jdr.pdf"
        generator.generate_cards(cards, output_path=output_file)

    except CardGeneratorError as e:
        print(f"❌  {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
