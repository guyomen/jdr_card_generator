"""
Générateur de cartes JDR - Logique principale
Utilise reportlab pour créer des cartes au format PDF imprimables.
"""

import os
import sys
import json
import glob
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from .providers import ImageProviderManager


# ─────────────────────────────────────────────
#  DIMENSIONS & MISE EN PAGE
# ─────────────────────────────────────────────
CARD_W = 63 * mm
CARD_H = 88 * mm
MARGIN = 10 * mm
MIN_COLS = 3
CUT_MARK_SZ = 3 * mm

# ─────────────────────────────────────────────
#  PALETTES
# ─────────────────────────────────────────────
PALETTES = {
    "arme": {
        "header_bg": colors.HexColor("#8B1A1A"),
        "header_fg": colors.white,
        "stats_bg": colors.HexColor("#F5E6D3"),
        "stats_fg": colors.HexColor("#3D0000"),
        "border": colors.HexColor("#5C0A0A"),
        "tag_bg": colors.HexColor("#C0392B"),
        "tag_fg": colors.white,
        "label": "ARME",
    },
    "armure": {
        "header_bg": colors.HexColor("#1A3A5C"),
        "header_fg": colors.white,
        "stats_bg": colors.HexColor("#D6E4F0"),
        "stats_fg": colors.HexColor("#0D2137"),
        "border": colors.HexColor("#0A2540"),
        "tag_bg": colors.HexColor("#2471A3"),
        "tag_fg": colors.white,
        "label": "ARMURE",
    },
    "equipement": {
        "header_bg": colors.HexColor("#2D6A2D"),
        "header_fg": colors.white,
        "stats_bg": colors.HexColor("#D5E8D4"),
        "stats_fg": colors.HexColor("#1A3D1A"),
        "border": colors.HexColor("#1B4D1B"),
        "tag_bg": colors.HexColor("#27AE60"),
        "tag_fg": colors.white,
        "label": "EQUIPEMENT",
    },
}


class CardGenerator:
    """Générateur de cartes JDR en PDF avec support images IA"""

    def __init__(self, cache_dir=".image_cache"):
        """
        Initialise le générateur

        Args:
            cache_dir: Répertoire de cache des images générées
        """
        self.cache_dir = cache_dir
        self.provider_manager = ImageProviderManager(cache_dir)
        os.makedirs(cache_dir, exist_ok=True)

    @staticmethod
    def load_json(path: str, card_type: str) -> list:
        """
        Charge un fichier JSON de cartes

        Args:
            path: Chemin du fichier JSON
            card_type: Type de carte (arme, armure, equipement)

        Returns:
            Liste des cartes avec le type assigné
        """
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            print(f"❌  Fichier introuvable : {path}", file=sys.stderr)
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"❌  JSON invalide dans {path} : {e}", file=sys.stderr)
            sys.exit(1)

        if not isinstance(data, list):
            print(f"❌  {path} doit contenir un tableau JSON", file=sys.stderr)
            sys.exit(1)

        for card in data:
            card.setdefault("type", card_type)

        return data

    def load_cards_from_files(
        self, armes=None, armures=None, autres=None
    ) -> list:
        """
        Charge les cartes depuis plusieurs fichiers JSON

        Args:
            armes: Chemin du fichier d'armes
            armures: Chemin du fichier d'armures
            autres: Chemin du fichier d'équipements

        Returns:
            Liste complète de toutes les cartes
        """
        cards = []
        if armes:
            cards += self.load_json(armes, "arme")
        if armures:
            cards += self.load_json(armures, "armure")
        if autres:
            cards += self.load_json(autres, "equipement")
        return cards

    @staticmethod
    def detect_type_from_filename(filename: str) -> str:
        """
        Détecte le type de carte basé sur le nom du fichier
        
        Args:
            filename: Nom du fichier (ex: armes.json, armures.json, autre.json)
        
        Returns:
            Type de carte (arme, armure, ou equipement)
        """
        filename_lower = filename.lower()
        if "arme" in filename_lower:
            return "arme"
        elif "armure" in filename_lower:
            return "armure"
        else:
            return "equipement"

    def load_cards_from_input(self, input_path: str) -> list:
        """
        Charge les cartes depuis un fichier ou un dossier
        Détecte automatiquement le type de carte
        
        Args:
            input_path: Chemin vers un fichier JSON ou un dossier contenant des JSONs
        
        Returns:
            Liste complète de toutes les cartes chargées
        """
        cards = []
        
        if os.path.isdir(input_path):
            # Charger tous les fichiers JSON du dossier
            json_files = sorted(glob.glob(os.path.join(input_path, "*.json")))
            if not json_files:
                print(f"❌  Aucun fichier JSON trouvé dans {input_path}", file=sys.stderr)
                sys.exit(1)
            
            for filepath in json_files:
                filename = os.path.basename(filepath)
                card_type = self.detect_type_from_filename(filename)
                loaded = self.load_json(filepath, card_type)
                print(f"  📁 {filename}: {len(loaded)} {card_type}(s)")
                cards.extend(loaded)
        else:
            # Charger un fichier spécifique
            filename = os.path.basename(input_path)
            card_type = self.detect_type_from_filename(filename)
            cards = self.load_json(input_path, card_type)
        
        return cards

    def fetch_images_for_cards(self, cards: list, provider: str = "pollinations",
                              model: str = "stabilityai/sd-turbo", **kwargs):
        """
        Génère/récupère les images pour les cartes

        Args:
            cards: Liste des cartes
            provider: Fournisseur d'images (pollinations, local, localapi, openai)
            model: Modèle à utiliser (pour provider=local)
            **kwargs: Arguments supplémentaires (api_url, api_key)
        """
        self.provider_manager.fetch_images(cards, provider, model, **kwargs)

    def generate_cards(self, cards: list, output_path: str = None):
        """
        Génère le PDF des cartes

        Args:
            cards: Liste des cartes à générer
            output_path: Chemin du fichier PDF de sortie (défaut: cartes_jdr.pdf)
        """
        if output_path is None:
            output_path = "cartes_jdr.pdf"

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        self._generate_pdf(cards, output_path)

    def _generate_pdf(self, cards: list, output_path: str):
        """Génère le fichier PDF"""
        page_w, page_h = A4
        cols = max(MIN_COLS, int((page_w - 2 * MARGIN) // CARD_W))
        rows = int((page_h - 2 * MARGIN) // CARD_H)
        per_page = cols * rows
        start_x = (page_w - cols * CARD_W) / 2

        c = canvas.Canvas(output_path, pagesize=A4)
        c.setTitle("Cartes JDR")

        for i, card in enumerate(cards):
            page_idx = i % per_page
            if i > 0 and page_idx == 0:
                c.showPage()
            col = page_idx % cols
            row = page_idx // cols
            cx = start_x + col * CARD_W
            cy = page_h - MARGIN - (row + 1) * CARD_H
            self._draw_cut_marks(c, cx, cy)
            self._draw_card(c, cx, cy, card)

        c.save()
        print(
            f"✅  {len(cards)} carte(s) → {output_path}  "
            f"[{cols} col × {rows} lignes/page]"
        )

    @staticmethod
    def _draw_cut_marks(c: canvas.Canvas, x: float, y: float):
        """Dessine les repères de coupe"""
        s = CUT_MARK_SZ
        c.setStrokeColor(colors.HexColor("#AAAAAA"))
        c.setLineWidth(0.25)
        for cx, cy in [(x, y), (x + CARD_W, y), (x, y + CARD_H), (x + CARD_W, y + CARD_H)]:
            c.line(cx - s, cy, cx + s, cy)
            c.line(cx, cy - s, cx, cy + s)

    def _draw_card(self, c: canvas.Canvas, x: float, y: float, card: dict):
        """Dessine une carte"""
        kind = card.get("type", "equipement").lower()
        pal = PALETTES.get(kind, PALETTES["equipement"])

        c.setFillColor(colors.white)
        c.setStrokeColor(pal["border"])
        c.setLineWidth(0.5)
        c.roundRect(x, y, CARD_W, CARD_H, radius=3 * mm, stroke=1, fill=1)

        # En-tête
        header_h = 14 * mm
        c.setFillColor(pal["header_bg"])
        c.roundRect(
            x, y + CARD_H - header_h, CARD_W, header_h, radius=3 * mm, stroke=0, fill=1
        )
        c.rect(x, y + CARD_H - header_h, CARD_W, 3 * mm, stroke=0, fill=1)
        c.setFillColor(pal["header_fg"])
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(
            x + CARD_W / 2, y + CARD_H - header_h + 4 * mm, card.get("nom", "???")
        )

        # Badge
        badge_h = 5 * mm
        badge_y = y + CARD_H - header_h - badge_h
        c.setFillColor(pal["tag_bg"])
        c.roundRect(x + 4 * mm, badge_y, CARD_W - 8 * mm, badge_h, radius=1.5 * mm, stroke=0, fill=1)
        c.setFillColor(pal["tag_fg"])
        c.setFont("Helvetica-Bold", 7)
        c.drawCentredString(x + CARD_W / 2, badge_y + 1.5 * mm, pal["label"])

        # Image
        img_margin = 4 * mm
        img_h = 28 * mm
        img_y = badge_y - img_h
        img_x = x + img_margin
        img_w = CARD_W - 2 * img_margin
        image_path = card.get("image")
        if image_path and os.path.exists(image_path):
            try:
                img = ImageReader(image_path)
                c.drawImage(
                    img,
                    img_x,
                    img_y,
                    width=img_w,
                    height=img_h,
                    preserveAspectRatio=True,
                    anchor="c",
                    mask="auto",
                )
                c.setStrokeColor(pal["border"])
                c.setLineWidth(0.5)
                c.roundRect(img_x, img_y, img_w, img_h, radius=2 * mm, stroke=1, fill=0)
            except Exception:
                self._draw_placeholder(c, img_x, img_y, img_w, img_h)
        else:
            self._draw_placeholder(c, img_x, img_y, img_w, img_h)

        # Stats
        sm = 3 * mm
        sx = x + sm
        sw = CARD_W - 2 * sm
        stats = self._get_stats(card, kind)
        slh = 5.5 * mm
        sh = len(stats) * slh + 2 * mm
        sy = img_y - sh - 1.5 * mm
        c.setFillColor(pal["stats_bg"])
        c.roundRect(sx, sy, sw, sh, radius=2 * mm, stroke=0, fill=1)

        for i, (lbl, val) in enumerate(stats):
            ly = sy + sh - (i + 1) * slh + 1 * mm
            c.setFillColor(pal["stats_fg"])
            c.setFont("Helvetica-Bold", 7)
            c.drawString(sx + 2 * mm, ly, lbl)
            c.setFont("Helvetica", 7)
            c.drawRightString(sx + sw - 2 * mm, ly, str(val))

            if i < len(stats) - 1:
                c.setStrokeColor(pal["border"])
                c.setLineWidth(0.3)
                c.line(sx + 2 * mm, ly - 0.5 * mm, sx + sw - 2 * mm, ly - 0.5 * mm)

        # Texte règles
        texte = card.get("regles") or card.get("info") or ""
        if texte:
            rp = 2.5 * mm
            self._draw_wrapped_text(
                c,
                texte,
                sx + rp,
                y + 3 * mm + rp,
                sw - 2 * rp,
                sy - 1.5 * mm - y - 3 * mm - 2 * rp,
                "Helvetica",
                6.5,
                colors.HexColor("#333333"),
                4.2 * mm,
            )

        # Bordure finale
        c.setStrokeColor(pal["border"])
        c.setLineWidth(0.5)
        c.roundRect(x, y, CARD_W, CARD_H, radius=3 * mm, stroke=1, fill=0)

    @staticmethod
    def _draw_placeholder(c, img_x, img_y, img_w, img_h):
        """Dessine un placeholder pour les images manquantes"""
        c.setFillColor(colors.HexColor("#F0F0F0"))
        c.setStrokeColor(colors.HexColor("#CCCCCC"))
        c.setLineWidth(0.5)
        c.roundRect(img_x, img_y, img_w, img_h, radius=2 * mm, stroke=1, fill=1)
        c.setStrokeColor(colors.HexColor("#BBBBBB"))
        c.setLineWidth(0.4)
        c.line(img_x, img_y, img_x + img_w, img_y + img_h)
        c.line(img_x + img_w, img_y, img_x, img_y + img_h)
        c.setFillColor(colors.HexColor("#AAAAAA"))
        c.setFont("Helvetica", 7)
        c.drawCentredString(img_x + img_w / 2, img_y + img_h / 2 - 2 * mm, "[ image ]")

    @staticmethod
    def _get_stats(card: dict, kind: str) -> list:
        """Extrait les stats à afficher selon le type de carte"""
        if kind == "arme":
            return [
                ("Type", card.get("sous_type", "—")),
                ("Dommages", card.get("dm", "—")),
                ("Portée", card.get("portee", "—")),
            ]
        elif kind == "armure":
            return [
                ("Type", card.get("sous_type", "—")),
                ("Défense", card.get("def", "—")),
                ("Max AGI", card.get("max_agi", "—")),
            ]
        else:
            rows = []
            if card.get("sous_type"):
                rows.append(("Type", card["sous_type"]))
            rows += [(k, v) for k, v in card.get("stats", {}).items()]
            return rows or [("—", "—")]

    @staticmethod
    def _draw_wrapped_text(c, text, x, y_bot, max_w, max_h, font, font_size, color, line_height):
        """Dessine du texte enrobé dans une zone limitée"""
        c.setFont(font, font_size)
        c.setFillColor(color)
        words, lines, current = text.split(), [], ""

        for word in words:
            test = (current + " " + word).strip()
            if c.stringWidth(test, font, font_size) <= max_w:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word

        if current:
            lines.append(current)

        lines = lines[: int(max_h // line_height)]
        start_y = y_bot + len(lines) * line_height - line_height

        for line in lines:
            c.drawString(x, start_y, line)
            start_y -= line_height
