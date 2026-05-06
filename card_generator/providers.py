"""
Providers d'images IA pour la génération de cartes
Support de multiples services : Pollinations, Local, API locale, OpenAI
"""

import os
import sys
import re
import json
import time
import base64
import warnings
import urllib.request
import urllib.parse

from .exceptions import CardGeneratorError

# Style de dessin appliqué à tous les prompts IA (défini dans le code, pas dans le JSON)
# The prompt suffix is intentionally in English to match the card descriptions.
IMAGE_STYLE_SUFFIX = "hand-drawn sketch, minimal color, almost black and white"
# Supprime les warnings de dépréciation internes à huggingface_hub/diffusers
warnings.filterwarnings("ignore", message=".*local_dir_use_symlinks.*")

# Désactive les custom ops CUDA pour éviter les incompatibilités torch/diffusers
os.environ["DIFFUSERS_DISABLE_CUDA_CUSTOM_OPS"] = "1"


def _safe_filename(name: str) -> str:
    """Convertit un nom en nom de fichier sûr"""
    return re.sub(r"[^a-z0-9_-]", "_", name.lower().strip()) + ".png"


def _build_prompt(card: dict) -> str:
    """Récupère le prompt IA depuis le champ description_ia de la carte"""
    prompt = (card.get("description_ia", "") or "").strip()
    if not prompt:
        print(
            f"⚠️   Attention : la carte '{card.get('nom', 'inconnu')}' n'a pas de champ 'description_ia'",
            file=sys.stderr,
        )
        return ""
    # Ajoute le style de dessin depuis le code (ne pas le mettre dans le JSON)
    style = IMAGE_STYLE_SUFFIX
    if prompt.endswith((".", "!", "?")):
        final = f"{prompt} {style}"
    else:
        final = f"{prompt}. {style}"
    return final


class ImageProviderManager:
    """Gère la génération/récupération d'images via différents providers"""

    def __init__(self, cache_dir: str = ".image_cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def fetch_images(
        self,
        cards: list,
        provider: str = "pollinations",
        model: str = "stabilityai/sd-turbo",
        **kwargs
    ):
        """
        Génère/récupère les images pour les cartes

        Args:
            cards: Liste des cartes
            provider: Fournisseur (pollinations, local, localapi, openai)
            model: Modèle HuggingFace (pour provider=local)
            **kwargs: Arguments supplémentaires (api_url, api_key)
        """
        total = len(cards)

        for i, card in enumerate(cards, 1):
            # Image existante → on garde
            if card.get("image") and os.path.exists(card["image"]):
                print(f"  [{i}/{total}] ✅  Image existante : {card['image']}")
                continue

            nom = card.get("nom", "item")
            cache_path = os.path.join(self.cache_dir, _safe_filename(nom))

            # Image en cache → on utilise
            if os.path.exists(cache_path):
                print(f"  [{i}/{total}] 📦  Cache : {nom}")
                card["image"] = cache_path
                continue

            prompt = _build_prompt(card)
            print(f"  [{i}/{total}] 🎨  {nom}")
            print(f"          📝 Prompt: {prompt}")
            print(f"          ⏳ Génération...", end=" ", flush=True)

            # Génère selon le provider
            if provider == "local":
                ok = self._gen_local(prompt, cache_path, model)
            elif provider == "localapi":
                ok = self._gen_localapi(prompt, cache_path, kwargs.get("api_url", "http://localhost:7860"))
            elif provider == "openai":
                ok = self._gen_openai(prompt, cache_path, kwargs.get("api_key", ""))
            else:
                ok = self._gen_pollinations(prompt, cache_path)

            print("✅" if ok else "❌ (placeholder)")
            if ok:
                card["image"] = cache_path

            if i < total and provider not in ("local",):
                time.sleep(1)

    @staticmethod
    def _gen_pollinations(prompt: str, dest: str) -> bool:
        """Génère une image via Pollinations (en ligne, gratuit)"""
        url = (
            "https://image.pollinations.ai/prompt/"
            + urllib.parse.quote(prompt)
            + "?width=512&height=512&nologo=true&model=flux"
        )
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "jdr-card-gen/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
            with open(dest, "wb") as f:
                f.write(data)
            return True
        except Exception as e:
            print(f"⚠️  Pollinations : {e}", file=sys.stderr)
            return False

    @staticmethod
    def _detect_device():
        """
        Détecte le meilleur device pour les GPU

        Ordre de priorité :
          1. DirectML (AMD/Intel/NVIDIA sur WSL2)
          2. CUDA (NVIDIA)
          3. CPU (fallback)
        """
        import torch

        try:
            import torch_directml
            return torch_directml.device(), torch.float32, "DirectML (AMD/Intel via WSL)"
        except ImportError:
            pass

        if torch.cuda.is_available():
            device_name = torch.cuda.get_device_name(0)
            vram = torch.cuda.get_device_properties(0).total_memory / 1e9
            return "cuda", torch.float16, f"CUDA - {device_name} ({vram:.1f} GB)"

        return "cpu", torch.float32, "CPU ⚠️  (LENT - installe CUDA ou torch-directml pour accélérer)"

    @staticmethod
    def _hf_repo_has_model_index(repo_id: str) -> bool:
        """Vérifie rapidement si le repo Hugging Face contient un `model_index.json`.

        Essaie d'abord via `huggingface_hub.HfApi.list_repo_files`, puis fallback
        vers une requête HTTP HEAD sur le fichier `model_index.json`.
        Utilise `HF_TOKEN`/`HUGGINGFACE_TOKEN` si fourni pour accéder aux dépôts privés.
        """
        token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")
        try:
            from huggingface_hub import HfApi

            api = HfApi()
            files = api.list_repo_files(repo_id)
            return "model_index.json" in files
        except Exception:
            # Fallback HTTP check
            try:
                import urllib.request
                import urllib.error

                url = f"https://huggingface.co/{repo_id}/resolve/main/model_index.json"
                headers = {"User-Agent": "jdr-card-gen/1.0"}
                if token:
                    headers["Authorization"] = f"Bearer {token}"
                req = urllib.request.Request(url, headers=headers, method="HEAD")
                with urllib.request.urlopen(req, timeout=10) as resp:
                    code = getattr(resp, "status", None) or resp.getcode()
                    return code == 200
            except Exception:
                return False

    @staticmethod
    def _gen_local(prompt: str, dest: str, model_id: str) -> bool:
        """
        Génère une image via HuggingFace Diffusers localement

        Premier lancement : télécharge le modèle (~2 Go pour sd-turbo)
        """
        try:
            import torch
            from diffusers import AutoPipelineForText2Image
            import transformers  # noqa: F401
        except ImportError:
            raise CardGeneratorError(
                "Packages manquants pour --provider local:\n"
                "    pip install diffusers torch transformers torchvision accelerate pillow\n"
                "    (AMD/WSL) pip install torch-directml"
            )

        if (
            not hasattr(ImageProviderManager._gen_local, "_pipe")
            or ImageProviderManager._gen_local._model_id != model_id
        ):
            print(f"  📦  Chargement du modèle {model_id}...")
            device, dtype, label = ImageProviderManager._detect_device()
            print(f"  🖥️   Device : {label}")

            if "CPU" in label and "LENT" in label:
                print(f"  ⚠️   ATTENTION : Génération en CPU sera très lente !")
                print(f"      Pour accélérer : pip install torch-directml (Windows/WSL)")
                print(f"      Ou installer CUDA pour NVIDIA GPU\n")

            # Caching simple pour éviter de re-vérifier le repo à chaque carte
            if not hasattr(ImageProviderManager, "_hf_model_valid_cache"):
                ImageProviderManager._hf_model_valid_cache = {}

            if model_id not in ImageProviderManager._hf_model_valid_cache:
                print(f"  🔎  Vérification compatibilité du dépôt '{model_id}'...", end=" ", flush=True)
                ok = ImageProviderManager._hf_repo_has_model_index(model_id)
                ImageProviderManager._hf_model_valid_cache[model_id] = ok
                print("✅" if ok else "❌")
            else:
                ok = ImageProviderManager._hf_model_valid_cache[model_id]

            if not ok:
                print(f"\n  ⚠️   Le dépôt '{model_id}' ne semble pas être un repo 'diffusers' compatible (model_index.json manquant).", file=sys.stderr)
                print(
                    "    Vérifiez le nom du modèle, définissez HF_TOKEN pour les modèles privés, ou utilisez un modèle compatible 'diffusers' (ex: stabilityai/stable-diffusion-xl-base-1.0).",
                    file=sys.stderr,
                )
                return False

            print(f"  ⏳  Téléchargement du modèle (~2 Go pour sd-turbo)...")
            is_dml = not isinstance(device, str)

            hf_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")

            # Use float32 for compatibility with all models (fp16 variant may not exist)
            try:
                pipe = AutoPipelineForText2Image.from_pretrained(
                    model_id,
                    torch_dtype=torch.float32,
                    **({"use_auth_token": hf_token} if hf_token else {}),
                ).to(device)
            except Exception as e:
                # Common cause: the repo is not a `diffusers` pipeline (no model_index.json)
                errstr = str(e)
                if "model_index.json" in errstr or "Entry Not Found" in errstr or "404" in errstr:
                    print(f"\n  ⚠️   Le dépôt '{model_id}' ne semble pas être un repo 'diffusers' compatible (fichier model_index.json manquant).", file=sys.stderr)
                    print("      Tentative de fallback avec `DiffusionPipeline.from_pretrained`...", file=sys.stderr)
                    try:
                        from diffusers import DiffusionPipeline

                        pipe = DiffusionPipeline.from_pretrained(
                            model_id,
                            torch_dtype=torch.float32,
                            **({"use_auth_token": hf_token} if hf_token else {}),
                        ).to(device)
                    except Exception as e2:
                        print(f"  ❌  Échec du fallback pour '{model_id}': {e2}", file=sys.stderr)
                        print(
                            "    Vérifiez que le nom du modèle est correct, que le modèle est public, ou utilisez un modèle compatible 'diffusers' (ex: stabilityai/stable-diffusion-xl-base-1.0).",
                            file=sys.stderr,
                        )
                        return False
                else:
                    print(f"  ❌  Erreur lors du chargement du modèle '{model_id}': {e}", file=sys.stderr)
                    return False

            try:
                pipe.set_progress_bar_config(disable=True)
            except Exception:
                # Certaines variantes de pipeline n'ont pas set_progress_bar_config
                pass

            ImageProviderManager._gen_local._pipe = pipe
            ImageProviderManager._gen_local._model_id = model_id
            print("  ✅  Modèle chargé et prêt")

        try:
            is_turbo = "turbo" in model_id.lower() or "lightning" in model_id.lower()
            steps = 4 if is_turbo else 20
            guidance = 0.0 if is_turbo else 7.5

            result = ImageProviderManager._gen_local._pipe(
                prompt=prompt,
                num_inference_steps=steps,
                guidance_scale=guidance,
                width=512,
                height=512,
            )
            result.images[0].save(dest)
            return True
        except Exception as e:
            print(f"⚠️  Local diffusers : {e}", file=sys.stderr)
            return False

    @staticmethod
    def _gen_localapi(prompt: str, dest: str, api_url: str) -> bool:
        """
        Génère une image via une API locale compatible Automatic1111

        Endpoints supportés :
          - Automatic1111 : http://localhost:7860
          - ComfyUI : configuration spécifique
          - InvokeAI : http://localhost:9090
        """
        payload = json.dumps(
            {
                "prompt": prompt,
                "negative_prompt": "text, watermark, blurry, low quality",
                "steps": 20,
                "width": 512,
                "height": 512,
                "cfg_scale": 7,
                "sampler_name": "Euler a",
            }
        ).encode()

        endpoint = api_url.rstrip("/") + "/sdapi/v1/txt2img"
        try:
            req = urllib.request.Request(
                endpoint,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=120) as r:
                resp = json.loads(r.read())

            img_b64 = resp["images"][0]
            img_data = base64.b64decode(img_b64)
            with open(dest, "wb") as f:
                f.write(img_data)
            return True
        except urllib.error.URLError as e:
            print(
                f"⚠️  Impossible de joindre l'API locale ({endpoint}) : {e.reason}",
                file=sys.stderr,
            )
            print(
                "    Vérifiez que votre serveur tourne et que --api_url est correct.",
                file=sys.stderr,
            )
            return False
        except Exception as e:
            print(f"⚠️  LocalAPI : {e}", file=sys.stderr)
            return False

    @staticmethod
    def _gen_openai(prompt: str, dest: str, api_key: str) -> bool:
        """Génère une image via OpenAI DALL-E 3"""
        try:
            from openai import OpenAI
        except ImportError:
            raise CardGeneratorError("Package manquant pour --provider openai: pip install openai")

        try:
            client = OpenAI(api_key=api_key)
            response = client.images.generate(
                model="dall-e-3", prompt=prompt, size="1024x1024", quality="standard", n=1
            )
            img_url = response.data[0].url
            req = urllib.request.Request(img_url, headers={"User-Agent": "jdr-card-gen/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                with open(dest, "wb") as f:
                    f.write(r.read())
            return True
        except Exception as e:
            print(f"⚠️  OpenAI : {e}", file=sys.stderr)
            return False
