"""
Générateur de cartes JDR - Logique principale
Utilise reportlab pour créer des cartes au format PDF imprimables.
"""

import os
import json
import csv
import glob
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from .exceptions import CardGeneratorError


# ─────────────────────────────────────────────
#  DIMENSIONS & MISE EN PAGE
# ─────────────────────────────────────────────
CARD_W = 63 * mm
CARD_H = 88 * mm
MARGIN = 10 * mm
MIN_COLS = 3
CUT_MARK_SZ = 3 * mm

# ─────────────────────────────────────────────
#  PALETTES PAR DÉFAUT (gris neutre)
# ─────────────────────────────────────────────
DEFAULT_PALETTES = {
    "arme": {
        "header_bg": "#808080",
        "header_fg": "#FFFFFF",
        "stats_bg": "#F0F0F0",
        "stats_fg": "#333333",
        "border": "#999999",
        "tag_bg": "#CCCCCC",
        "tag_fg": "#333333",
        "label": "ARME",
    },
    "armure": {
        "header_bg": "#808080",
        "header_fg": "#FFFFFF",
        "stats_bg": "#F0F0F0",
        "stats_fg": "#333333",
        "border": "#999999",
        "tag_bg": "#CCCCCC",
        "tag_fg": "#333333",
        "label": "ARMURE",
    },
    "equipement": {
        "header_bg": "#808080",
        "header_fg": "#FFFFFF",
        "stats_bg": "#F0F0F0",
        "stats_fg": "#333333",
        "border": "#999999",
        "tag_bg": "#CCCCCC",
        "tag_fg": "#333333",
        "label": "EQUIPEMENT",
    },
}


def _resolve_palette(card: dict, styles: dict = None) -> dict:
    """
    Résout la palette à utiliser pour une carte.
    Priorité : styles chargés > palette par défaut du type.
    Les couleurs hex sont converties en objets reportlab.
    """
    if styles is None:
        styles = {}
    
    kind = card.get("type", "equipement").lower()
    
    # Cherche le style pour ce type
    if kind in styles and "template" in styles[kind]:
        base = styles[kind]["template"].copy()
    else:
        base = DEFAULT_PALETTES.get(kind, DEFAULT_PALETTES["equipement"]).copy()

    # Override avec le template custom si présent
    template = card.get("_template", {})
    for key in ("header_bg", "header_fg", "stats_bg", "stats_fg", "border", "tag_bg", "tag_fg", "label"):
        if key in template:
            base[key] = template[key]

    # Convertit les couleurs hex en objets reportlab
    pal = {}
    for key, val in base.items():
        if isinstance(val, str) and val.startswith("#"):
            pal[key] = colors.HexColor(val)
        else:
            pal[key] = val
    return pal


class CardGenerator:
    """Générateur de cartes JDR en PDF avec support images IA"""

    def __init__(self, style_path: str = None):
        """
        Initialise le générateur

        Args:
            style_path: Chemin vers le fichier style.json (optionnel)
        """
        self.styles = {}
        if style_path:
            self._load_styles(style_path)

    def _load_styles(self, style_path: str):
        """
        Charge les styles depuis un fichier JSON

        Args:
            style_path: Chemin vers le fichier style.json
        """
        try:
            if os.path.exists(style_path):
                with open(style_path, encoding="utf-8") as f:
                    self.styles = json.load(f)
                print(f"✅ Styles chargés depuis {style_path}")
            else:
                print(f"⚠️  Fichier de styles non trouvé : {style_path}")
        except Exception as e:
            print(f"⚠️  Erreur lors du chargement des styles : {e}")

    def load_csv(self, path: str, card_type: str = "equipement") -> list:
        """
        Charge un fichier CSV de cartes

        Args:
            path: Chemin du fichier CSV
            card_type: Type de carte (arme, armure, equipement)

        Returns:
            Liste des cartes avec le type assigné

        Raises:
            CardGeneratorError: Si le fichier est introuvable ou invalide
        """
        try:
            with open(path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                cards = list(reader)
        except FileNotFoundError:
            raise CardGeneratorError(f"Fichier introuvable : {path}")
        except Exception as e:
            raise CardGeneratorError(f"Erreur lors de la lecture du CSV {path} : {e}")

        if not cards:
            raise CardGeneratorError(f"Fichier CSV vide : {path}")

        # Assigne le type à toutes les cartes et parse les champs stats
        for card in cards:
            card.setdefault("type", card_type)
            
            # Parse le champ stats s'il existe et n'est pas vide
            if "stats" in card and card["stats"]:
                try:
                    # Essaie d'abord du JSON
                    card["stats"] = json.loads(card["stats"])
                except (json.JSONDecodeError, ValueError):
                    # Sinon, parse le format "clé: valeur; clé2: valeur2"
                    stats_dict = {}
                    for pair in card["stats"].split(";"):
                        if ":" in pair:
                            key, val = pair.split(":", 1)
                            stats_dict[key.strip()] = val.strip()
                    card["stats"] = stats_dict if stats_dict else {}
            else:
                card["stats"] = {}

        return cards

    @staticmethod
    def _detect_card_type(filename: str) -> str:
        """
        Détecte le type de carte par le nom du fichier
        """
        name = filename.lower()
        if "weapon" in name or "arme" in name:
            return "arme"
        elif "armor" in name or "armure" in name:
            return "armure"
        else:
            return "equipement"

    @staticmethod
    def load_json(path: str) -> list:
        """
        Charge un fichier JSON de cartes

        Format attendu :
          {
            "_meta": { "type": "arme", "template": { ... } },
            "items": [ ... ]
          }

        Args:
            path: Chemin du fichier JSON

        Returns:
            Liste des cartes avec le type et la palette assignés

        Raises:
            CardGeneratorError: Si le fichier est introuvable, invalide ou mal structuré
        """
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            raise CardGeneratorError(f"Fichier introuvable : {path}")
        except json.JSONDecodeError as e:
            raise CardGeneratorError(f"JSON invalide dans {path} : {e}")

        if not isinstance(data, dict) or "_meta" not in data or "items" not in data:
            raise CardGeneratorError(
                f"{path} : format invalide. Attendu : {{\"_meta\": {{...}}, \"items\": [...]}}"
            )

        meta = data["_meta"]
        items = data["items"]

        if not isinstance(items, list):
            raise CardGeneratorError(f"{path} : 'items' doit être un tableau")

        card_type = meta.get("type", "equipement")
        template = meta.get("template")

        for card in items:
            card.setdefault("type", card_type)
            if template:
                card.setdefault("_template", template)

        return items

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
        for path in (armes, armures, autres):
            if path:
                cards += self.load_json(path)
        return cards

    def load_cards_from_input(self, input_path: str) -> list:
        """
        Charge les cartes depuis un fichier ou un dossier
        Auto-détecte JSON ou CSV par extension de fichier
        Détecte le type de carte via le nom de fichier

        Args:
            input_path: Chemin vers un fichier ou un dossier contenant des cartes

        Returns:
            Liste complète de toutes les cartes chargées

        Raises:
            CardGeneratorError: Si aucun fichier n'est trouvé
        """
        cards = []

        if os.path.isdir(input_path):
            # Cherche les CSV d'abord, puis les JSON
            csv_files = sorted(glob.glob(os.path.join(input_path, "*.csv")))
            json_files = sorted(glob.glob(os.path.join(input_path, "*.json")))
            
            # Exclut style.json et autres fichiers de configuration
            json_files = [f for f in json_files if os.path.basename(f) not in ("style.json",)]
            
            if not csv_files and not json_files:
                raise CardGeneratorError(f"Aucun fichier de cartes trouvé dans {input_path}")

            # Charge les CSV
            for filepath in csv_files:
                filename = os.path.basename(filepath)
                card_type = self._detect_card_type(filename)
                loaded = self.load_csv(filepath, card_type)
                print(f"  📁 {filename}: {len(loaded)} {card_type}(s)")
                cards.extend(loaded)
            
            # Charge les JSON (support rétrocompatible)
            for filepath in json_files:
                filename = os.path.basename(filepath)
                loaded = self.load_json(filepath)
                card_type = loaded[0]["type"] if loaded else "inconnu"
                print(f"  📁 {filename}: {len(loaded)} {card_type}(s)")
                cards.extend(loaded)
        else:
            # Fichier unique
            ext = os.path.splitext(input_path)[1].lower()
            if ext == ".csv":
                card_type = self._detect_card_type(os.path.basename(input_path))
                cards = self.load_csv(input_path, card_type)
            else:
                cards = self.load_json(input_path)

        return cards

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
        pal = _resolve_palette(card, self.styles)

        # ── Ombre portée ──────────────────────────────────────────────
        SHADOW = 1.5 * mm
        c.setFillColor(colors.HexColor("#BBBBBB"))
        c.roundRect(x + SHADOW, y - SHADOW, CARD_W, CARD_H, radius=3 * mm, stroke=0, fill=1)

        # ── Fond blanc + bordure externe ──────────────────────────────
        c.setFillColor(colors.white)
        c.setStrokeColor(pal["border"])
        c.setLineWidth(1.2)
        c.roundRect(x, y, CARD_W, CARD_H, radius=3 * mm, stroke=1, fill=1)

        # ── En-tête (compact) ─────────────────────────────────────────
        header_h = 10 * mm
        header_y = y + CARD_H - header_h
        c.setFillColor(pal["header_bg"])
        c.roundRect(x, header_y, CARD_W, header_h, radius=3 * mm, stroke=0, fill=1)
        c.rect(x, header_y, CARD_W, 3 * mm, stroke=0, fill=1)
        # Liseré lumineux
        hb = pal["header_bg"]
        lighter = colors.Color(
            min(hb.red + 0.25, 1.0),
            min(hb.green + 0.25, 1.0),
            min(hb.blue + 0.25, 1.0),
        )
        c.setFillColor(lighter)
        c.roundRect(x, header_y + header_h - 2.5 * mm, CARD_W, 2.5 * mm, radius=3 * mm, stroke=0, fill=1)
        # Nom de l'objet — font size augmenté mais contenu adapté si nécessaire
        name = card.get("nom", "???")
        desired_title_size = 11  # points (augmenté sans changer la cartouche)
        max_name_width = CARD_W - 8 * mm  # laisser un peu de marge à gauche/droite

        # Réduire la taille si le nom est trop long pour tenir dans la largeur
        title_size = desired_title_size
        while title_size > 5 and c.stringWidth(name, "Helvetica-Bold", title_size) > max_name_width:
            title_size -= 0.5

        c.setFont("Helvetica-Bold", title_size)
        c.setFillColor(pal["header_fg"])
        # Position verticale : centre approximatif en tenant compte de la taille de police
        name_y = header_y + (header_h - title_size) / 2 + title_size * 0.25
        c.drawCentredString(x + CARD_W / 2, name_y, name)

        # ── Image + Badge type vertical à gauche ──────────────────────
        image_path = card.get("image")
        has_image = image_path and os.path.exists(image_path)
        img_h = 44 * mm if has_image else 28 * mm
        badge_w = 5 * mm
        img_margin = 3 * mm
        img_x = x + img_margin + badge_w + 1 * mm
        img_y = header_y - img_h - 2 * mm
        img_w = CARD_W - img_margin - badge_w - 1 * mm - img_margin

        # Badge type vertical (rotation 90°)
        badge_x = x + img_margin
        badge_y_start = img_y
        badge_h = img_h
        c.setFillColor(pal["tag_bg"])
        c.roundRect(badge_x, badge_y_start, badge_w, badge_h, radius=1.5 * mm, stroke=0, fill=1)
        c.setStrokeColor(pal["border"])
        c.setLineWidth(0.4)
        c.roundRect(badge_x, badge_y_start, badge_w, badge_h, radius=1.5 * mm, stroke=1, fill=0)
        # Texte vertical
        c.saveState()
        c.setFillColor(pal["tag_fg"])
        c.setFont("Helvetica-Bold", 6)
        c.translate(badge_x + badge_w / 2 + 1 * mm, badge_y_start + badge_h / 2)
        c.rotate(90)
        c.drawCentredString(0, 0, pal["label"])
        c.restoreState()

        # Image ou placeholder
        if has_image:
            try:
                img = ImageReader(image_path)
                c.drawImage(
                    img, img_x, img_y, width=img_w, height=img_h,
                    preserveAspectRatio=True, anchor="c", mask="auto",
                )
                c.setStrokeColor(pal["border"])
                c.setLineWidth(0.8)
                c.roundRect(img_x, img_y, img_w, img_h, radius=2 * mm, stroke=1, fill=0)
            except Exception:
                self._draw_placeholder(c, img_x, img_y, img_w, img_h, pal)
        else:
            self._draw_placeholder(c, img_x, img_y, img_w, img_h, pal)

        # ── Séparateur décoratif ──────────────────────────────────────
        div_y = img_y - 2.5 * mm
        self._draw_divider(c, x + 4 * mm, x + CARD_W - 4 * mm, div_y, pal["border"])

        # ── Stats avec rangées alternées ──────────────────────────────
        sm = 3 * mm
        sx = x + sm
        sw = CARD_W - 2 * sm
        stats = self._get_stats(card, kind)
        slh = 5.5 * mm
        sh = len(stats) * slh + 2 * mm
        sy = div_y - sh - 1.5 * mm
        # Fond global
        c.setFillColor(pal["stats_bg"])
        c.roundRect(sx, sy, sw, sh, radius=2 * mm, stroke=0, fill=1)
        # Rangées alternées (légèrement plus foncées)
        sb = pal["stats_bg"]
        alt_color = colors.Color(
            max(sb.red - 0.07, 0),
            max(sb.green - 0.07, 0),
            max(sb.blue - 0.07, 0),
        )
        for i, _ in enumerate(stats):
            if i % 2 == 1:
                row_y = sy + sh - (i + 1) * slh
                c.setFillColor(alt_color)
                c.rect(sx, row_y, sw, slh, stroke=0, fill=1)

        for i, (lbl, val) in enumerate(stats):
            ly = sy + sh - (i + 1) * slh + 1.5 * mm
            # Trait d'accentuation gauche coloré
            c.setFillColor(pal["tag_bg"])
            c.rect(sx, sy + sh - (i + 1) * slh + 0.5 * mm, 1.2 * mm, slh - 1 * mm, stroke=0, fill=1)
            c.setFillColor(pal["stats_fg"])
            c.setFont("Helvetica-Bold", 7)
            c.drawString(sx + 3 * mm, ly, lbl)
            c.setFont("Helvetica", 7)
            c.drawRightString(sx + sw - 2 * mm, ly, str(val))
            if i < len(stats) - 1:
                c.setStrokeColor(pal["border"])
                c.setLineWidth(0.2)
                c.line(sx + 2 * mm, ly - 0.5 * mm, sx + sw - 2 * mm, ly - 0.5 * mm)

        c.setStrokeColor(pal["border"])
        c.setLineWidth(0.6)
        c.roundRect(sx, sy, sw, sh, radius=2 * mm, stroke=1, fill=0)

        # ── Zone règles avec fond teinté ──────────────────────────────
        texte = card.get("regles") or card.get("info") or ""
        rules_y_bot = y + 2.5 * mm
        rules_h = sy - 2 * mm - rules_y_bot
        if texte and rules_h > 4 * mm:
            rp = 2 * mm
            c.setFillColor(colors.HexColor("#F8F8F8"))
            c.roundRect(sx, rules_y_bot, sw, rules_h, radius=1.5 * mm, stroke=0, fill=1)
            # Trait d'accroche coloré en bas de la zone
            c.setFillColor(pal["tag_bg"])
            c.roundRect(sx, rules_y_bot, sw, 2 * mm, radius=1.5 * mm, stroke=0, fill=1)
            c.setStrokeColor(pal["border"])
            c.setLineWidth(0.4)
            c.roundRect(sx, rules_y_bot, sw, rules_h, radius=1.5 * mm, stroke=1, fill=0)
            # Label "Règles:" en haut
            label_y = rules_y_bot + rules_h - rp - 3 * mm
            c.setFillColor(pal["stats_fg"])
            c.setFont("Helvetica-Bold", 7)
            c.drawString(sx + rp, label_y, "Règles:")
            # Texte des règles juste sous le label, de haut en bas
            text_y_start = label_y - 3 * mm  # Juste sous le label
            text_max_h = rules_h - rp - 2 * mm - 3 * mm  # Espace du label jusqu'en bas
            self._draw_wrapped_text_topdown(
                c, texte,
                sx + rp, text_y_start,
                sw - 2 * rp, text_max_h,
                "Helvetica-Oblique", 6.5,
                colors.HexColor("#444444"), 4.2 * mm,
            )

        # ── Double bordure décorative ─────────────────────────────────
        inset = 1.5 * mm
        c.setStrokeColor(pal["border"])
        c.setLineWidth(0.3)
        c.roundRect(x + inset, y + inset, CARD_W - 2 * inset, CARD_H - 2 * inset, radius=2.5 * mm, stroke=1, fill=0)
        # Bordure externe finale
        c.setLineWidth(1.2)
        c.roundRect(x, y, CARD_W, CARD_H, radius=3 * mm, stroke=1, fill=0)

    @staticmethod
    def _draw_placeholder(c, img_x, img_y, img_w, img_h, pal=None):
        """Dessine un placeholder vide pour les images manquantes (case blanche avec bordure fine)"""
        border = colors.HexColor("#CCCCCC") if pal is None else pal["border"]
        c.setFillColor(colors.white)
        c.setStrokeColor(border)
        c.setLineWidth(0.6)
        c.roundRect(img_x, img_y, img_w, img_h, radius=2 * mm, stroke=1, fill=1)

    @staticmethod
    def _draw_divider(c, x1, x2, y, color):
        """Dessine un séparateur décoratif : ligne + losange central"""
        mid = (x1 + x2) / 2
        ds = 1.5 * mm  # demi-taille du losange
        c.setStrokeColor(color)
        c.setLineWidth(0.5)
        c.line(x1, y, mid - ds * 1.4, y)
        c.line(mid + ds * 1.4, y, x2, y)
        p = c.beginPath()
        p.moveTo(mid, y + ds)
        p.lineTo(mid + ds, y)
        p.lineTo(mid, y - ds)
        p.lineTo(mid - ds, y)
        p.close()
        c.setFillColor(color)
        c.drawPath(p, fill=1, stroke=0)

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

    @staticmethod
    def _draw_wrapped_text_topdown(c, text, x, y_top, max_w, max_h, font, font_size, color, line_height):
        """Dessine du texte enrobé en commençant par le haut, avec sauts de ligne à chaque point"""
        c.setFont(font, font_size)
        c.setFillColor(color)
        
        # Divise le texte par les points pour créer des phrases
        sentences = [s.strip() for s in text.split(".") if s.strip()]
        
        lines = []
        for i, sentence in enumerate(sentences):
            words = sentence.split()
            current = ""
            
            for word in words:
                test = (current + " " + word).strip()
                if c.stringWidth(test, font, font_size) <= max_w:
                    current = test
                else:
                    if current:
                        lines.append(current)
                    current = word
            
            if current:
                lines.append(current + ".")  # Ajoute le point à la fin de la phrase
            
            # Ajoute un petit espacement entre les phrases (pas la dernière)
            if i < len(sentences) - 1:
                lines.append("")
        
        # Limite au nombre de lignes qui rentre dans la zone (en tenant compte du facteur 0.5)
        lines = lines[: int(max_h // (line_height * 0.5))]
        current_y = y_top
        
        for line in lines:
            if current_y < y_top - max_h:
                break
            c.drawString(x, current_y, line)
            current_y -= line_height * 0.5  # Réduit l'espacement à 50% pour les lignes vides aussi
