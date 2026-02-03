#!/usr/bin/env python3
"""
Video Processor - Module de traitement vidéo basé sur FFmpeg
Convertit les vidéos au format vertical (1080x1920) avec encodage H.264/AAC
"""

import os
import subprocess
import uuid
from pathlib import Path
from typing import Optional


def process_video(input_path: str) -> str:
    """
    Traite un fichier vidéo et le convertit au format MP4 vertical.
    
    Args:
        input_path: Chemin vers le fichier vidéo d'entrée
        
    Returns:
        str: Chemin vers le fichier vidéo généré
        
    Raises:
        FileNotFoundError: Si le fichier d'entrée n'existe pas
        RuntimeError: Si le traitement FFmpeg échoue
    """
    
    # =========================================================================
    # VALIDATION DU FICHIER D'ENTRÉE
    # =========================================================================
    input_file = Path(input_path)
    
    if not input_file.exists():
        raise FileNotFoundError(f"Fichier vidéo introuvable: {input_path}")
    
    if not input_file.is_file():
        raise ValueError(f"Le chemin spécifié n'est pas un fichier: {input_path}")
    
    # =========================================================================
    # CRÉATION DU DOSSIER DE SORTIE
    # =========================================================================
    output_dir = Path("outputs")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # =========================================================================
    # GÉNÉRATION DU NOM DE FICHIER DE SORTIE
    # =========================================================================
    # Utilisation d'un UUID pour éviter les conflits de noms
    input_filename = input_file.stem
    unique_id = uuid.uuid4().hex[:8]
    output_filename = f"{input_filename}_{unique_id}.mp4"
    output_path = output_dir / output_filename
    
    # =========================================================================
    # PARAMÈTRES DE CONVERSION
    # =========================================================================
    # Résolution cible (format vertical pour mobile/stories)
    target_width = 1080
    target_height = 1920
    
    # Pourcentage de crop léger (5% de chaque côté = 10% total)
    crop_percent = 0.05
    
    # =========================================================================
    # CONSTRUCTION DU FILTRE VIDÉO
    # =========================================================================
    # Le filtre effectue les opérations suivantes :
    # 1. Applique un léger crop centré sur la vidéo source (retire 5% de chaque bord)
    # 2. Scale la vidéo pour couvrir les dimensions cibles (conserve le ratio)
    # 3. Crop final centré pour obtenir exactement 1080x1920
    # 4. Normalise le SAR (Sample Aspect Ratio) à 1:1
    video_filter = (
        # Étape 1: Crop léger centré sur la source (5% de chaque côté)
        f"crop=iw*{1 - 2*crop_percent}:ih*{1 - 2*crop_percent}:iw*{crop_percent}:ih*{crop_percent},"
        # Étape 2: Scale pour couvrir la résolution cible
        f"scale=w={target_width}:h={target_height}:force_original_aspect_ratio=increase,"
        # Étape 3: Crop centré final pour dimensions exactes
        f"crop={target_width}:{target_height}:(iw-{target_width})/2:(ih-{target_height})/2,"
        # Étape 4: Normalisation du ratio d'aspect des pixels
        f"setsar=1"
    )
    
    # =========================================================================
    # CONSTRUCTION DE LA COMMANDE FFMPEG
    # =========================================================================
    ffmpeg_cmd = [
        "ffmpeg",
        # --- Options d'entrée ---
        "-i", str(input_file),          # Fichier d'entrée
        "-y",                            # Écrase le fichier de sortie sans demander
        
        # --- Filtres vidéo ---
        "-vf", video_filter,             # Applique le filtre de crop et scale
        
        # --- Codec vidéo H.264 ---
        "-c:v", "libx264",               # Codec H.264 (libx264)
        "-profile:v", "high",            # Profil High pour meilleure qualité
        "-level:v", "4.1",               # Niveau de compatibilité
        "-preset", "medium",             # Équilibre vitesse/qualité d'encodage
        "-crf", "23",                    # Qualité constante (18-28, plus bas = meilleur)
        "-pix_fmt", "yuv420p",           # Format pixel compatible universellement
        
        # --- Codec audio AAC ---
        "-c:a", "aac",                   # Codec audio AAC
        "-b:a", "128k",                  # Bitrate audio 128 kbps
        "-ar", "44100",                  # Fréquence d'échantillonnage 44.1 kHz
        "-ac", "2",                      # Audio stéréo (2 canaux)
        
        # --- Options de conteneur MP4 ---
        "-movflags", "+faststart",       # Optimise pour lecture web (moov atom au début)
        "-brand", "mp42",                # Marque de compatibilité MP4
        
        # --- Fichier de sortie ---
        str(output_path)
    ]
    
    # =========================================================================
    # EXÉCUTION DE FFMPEG
    # =========================================================================
    try:
        # Exécute la commande FFmpeg
        result = subprocess.run(
            ffmpeg_cmd,
            capture_output=True,         # Capture stdout et stderr
            text=True,                   # Décode en texte (pas bytes)
            check=True,                  # Lève une exception si code retour != 0
            timeout=3600                 # Timeout d'1 heure max
        )
        
    except subprocess.CalledProcessError as e:
        # FFmpeg a retourné une erreur
        error_message = (
            f"Échec du traitement FFmpeg.\n"
            f"Code de retour: {e.returncode}\n"
            f"Stderr: {e.stderr}"
        )
        raise RuntimeError(error_message) from e
        
    except subprocess.TimeoutExpired:
        raise RuntimeError("Le traitement a dépassé le délai maximum d'1 heure.")
        
    except FileNotFoundError:
        raise RuntimeError(
            "FFmpeg n'est pas installé ou n'est pas dans le PATH système.\n"
            "Installez FFmpeg: https://ffmpeg.org/download.html"
        )
    
    # =========================================================================
    # VÉRIFICATION DU FICHIER DE SORTIE
    # =========================================================================
    if not output_path.exists():
        raise RuntimeError(f"Le fichier de sortie n'a pas été créé: {output_path}")
    
    # Vérifie que le fichier n'est pas vide
    if output_path.stat().st_size == 0:
        output_path.unlink()  # Supprime le fichier vide
        raise RuntimeError("Le fichier de sortie généré est vide.")
    
    return f"/outputs/{output_path.name}"


def get_video_info(input_path: str) -> Optional[dict]:
    """
    Récupère les informations d'une vidéo via FFprobe.
    
    Args:
        input_path: Chemin vers le fichier vidéo
        
    Returns:
        dict: Informations sur la vidéo (durée, résolution, etc.) ou None si erreur
    """
    try:
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            input_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        import json
        return json.loads(result.stdout)
        
    except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError):
        return None


def check_ffmpeg_available() -> bool:
    """
    Vérifie si FFmpeg est disponible sur le système.
    
    Returns:
        bool: True si FFmpeg est disponible, False sinon
    """
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            check=True,
            timeout=10
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


# =============================================================================
# POINT D'ENTRÉE POUR UTILISATION EN LIGNE DE COMMANDE
# =============================================================================
if __name__ == "__main__":
    import sys
    
    # Affiche l'aide si aucun argument
    if len(sys.argv) < 2:
        print("=" * 60)
        print("VIDEO PROCESSOR - Convertisseur vidéo vertical")
        print("=" * 60)
        print("\nUsage: python video_processor.py <chemin_video>")
        print("\nCe script convertit une vidéo au format vertical (1080x1920)")
        print("avec codec vidéo H.264 et codec audio AAC.")
        print("\nCaractéristiques:")
        print("  • Résolution: 1080x1920 (format vertical)")
        print("  • Codec vidéo: H.264 (libx264)")
        print("  • Codec audio: AAC 128kbps")
        print("  • Crop centré léger appliqué")
        print("  • Sortie dans le dossier outputs/")
        sys.exit(0)
    
    # Vérifie la disponibilité de FFmpeg
    print("Vérification de FFmpeg...")
    if not check_ffmpeg_available():
        print("❌ Erreur: FFmpeg n'est pas installé ou n'est pas dans le PATH")
        print("   Installez FFmpeg depuis: https://ffmpeg.org/download.html")
        sys.exit(1)
    print("✓ FFmpeg détecté")
    
    input_video = sys.argv[1]
    
    try:
        print(f"\n📹 Traitement de: {input_video}")
        print("   Conversion en cours...")
        
        output_video = process_video(input_video)
        
        print(f"\n✅ Succès!")
        print(f"   Fichier créé: {output_video}")
        
    except FileNotFoundError as e:
        print(f"\n❌ Erreur: {e}")
        sys.exit(1)
        
    except RuntimeError as e:
        print(f"\n❌ Erreur de traitement:\n{e}")
        sys.exit(1)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Traitement interrompu par l'utilisateur")
        sys.exit(130)
