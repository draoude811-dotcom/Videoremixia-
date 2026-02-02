#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Video Processor - Traitement vidéo avec FFmpeg
===============================================

Ce module permet de :
- Couper les 30 premières secondes d'une vidéo
- Convertir en format vertical 9:16
- Ajouter un texte centré "Remix by AI"
- Exporter en MP4
- Nettoyer les fichiers temporaires

Auteur: AI Assistant
Compatible: Linux
Dépendances: FFmpeg doit être installé sur le système
"""

import subprocess
import os
import tempfile
import shutil
import logging
from pathlib import Path
from typing import Optional, Tuple

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VideoProcessorError(Exception):
    """Exception personnalisée pour les erreurs de traitement vidéo."""
    pass


class VideoProcessor:
    """
    Classe principale pour le traitement de vidéos avec FFmpeg.
    
    Attributes:
        input_path (Path): Chemin vers la vidéo d'entrée
        output_path (Path): Chemin vers la vidéo de sortie
        temp_dir (Path): Répertoire pour les fichiers temporaires
        duration (int): Durée de la coupe en secondes (défaut: 30)
        text_overlay (str): Texte à superposer sur la vidéo
    """
    
    # Dimensions pour le format vertical 9:16
    OUTPUT_WIDTH = 1080
    OUTPUT_HEIGHT = 1920
    
    def __init__(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        duration: int = 30,
        text_overlay: str = "Remix by AI"
    ):
        """
        Initialise le processeur vidéo.
        
        Args:
            input_path: Chemin vers la vidéo source
            output_path: Chemin de sortie (optionnel, généré automatiquement si non fourni)
            duration: Durée en secondes à extraire depuis le début (défaut: 30)
            text_overlay: Texte à afficher sur la vidéo (défaut: "Remix by AI")
        
        Raises:
            FileNotFoundError: Si le fichier d'entrée n'existe pas
            VideoProcessorError: Si FFmpeg n'est pas installé
        """
        self.input_path = Path(input_path)
        self.duration = duration
        self.text_overlay = text_overlay
        self.temp_dir: Optional[Path] = None
        
        # Vérification que le fichier d'entrée existe
        if not self.input_path.exists():
            raise FileNotFoundError(f"Fichier vidéo introuvable: {input_path}")
        
        # Vérification que FFmpeg est installé
        self._check_ffmpeg_installed()
        
        # Définition du chemin de sortie
        if output_path:
            self.output_path = Path(output_path)
        else:
            # Génère un nom de sortie basé sur l'entrée
            stem = self.input_path.stem
            self.output_path = self.input_path.parent / f"{stem}_remix_vertical.mp4"
        
        logger.info(f"VideoProcessor initialisé - Entrée: {self.input_path}, Sortie: {self.output_path}")
    
    def _check_ffmpeg_installed(self) -> None:
        """
        Vérifie que FFmpeg est installé et accessible.
        
        Raises:
            VideoProcessorError: Si FFmpeg n'est pas trouvé
        """
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True,
                check=True
            )
            logger.debug(f"FFmpeg trouvé: {result.stdout.split(chr(10))[0]}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise VideoProcessorError(
                "FFmpeg n'est pas installé ou n'est pas dans le PATH. "
                "Installez-le avec: sudo apt-get install ffmpeg"
            )
    
    def _create_temp_dir(self) -> Path:
        """
        Crée un répertoire temporaire pour les fichiers intermédiaires.
        
        Returns:
            Path: Chemin vers le répertoire temporaire créé
        """
        self.temp_dir = Path(tempfile.mkdtemp(prefix="video_processor_"))
        logger.info(f"Répertoire temporaire créé: {self.temp_dir}")
        return self.temp_dir
    
    def _cleanup_temp_files(self) -> None:
        """
        Supprime le répertoire temporaire et tous ses fichiers.
        """
        if self.temp_dir and self.temp_dir.exists():
            try:
                shutil.rmtree(self.temp_dir)
                logger.info(f"Fichiers temporaires supprimés: {self.temp_dir}")
            except OSError as e:
                logger.warning(f"Erreur lors de la suppression des fichiers temporaires: {e}")
    
    def _get_video_info(self) -> Tuple[int, int, float]:
        """
        Récupère les informations de la vidéo source (largeur, hauteur, durée).
        
        Returns:
            Tuple contenant (largeur, hauteur, durée en secondes)
        
        Raises:
            VideoProcessorError: Si impossible de lire les informations
        """
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,duration",
            "-of", "csv=p=0",
            str(self.input_path)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            parts = result.stdout.strip().split(",")
            
            width = int(parts[0])
            height = int(parts[1])
            # La durée peut être N/A pour certains formats
            duration = float(parts[2]) if len(parts) > 2 and parts[2] != "N/A" else 0
            
            logger.info(f"Info vidéo - Dimensions: {width}x{height}, Durée: {duration}s")
            return width, height, duration
            
        except (subprocess.CalledProcessError, ValueError, IndexError) as e:
            raise VideoProcessorError(f"Impossible de lire les informations vidéo: {e}")
    
    def _build_ffmpeg_command(self) -> list:
        """
        Construit la commande FFmpeg complète pour le traitement.
        
        La commande effectue en une seule passe:
        1. Coupe les N premières secondes
        2. Redimensionne et recadre en 9:16
        3. Ajoute le texte centré
        
        Returns:
            Liste des arguments pour subprocess
        """
        # Construction du filtre complexe
        # 1. scale: Redimensionne pour remplir 1080x1920 tout en gardant le ratio
        # 2. crop: Recadre au centre pour obtenir exactement 9:16
        # 3. drawtext: Ajoute le texte centré
        
        filter_complex = (
            # Étape 1: Redimensionner la vidéo pour qu'elle remplisse le format 9:16
            # On scale de façon à ce que la plus petite dimension corresponde au format cible
            f"scale=w='if(gt(iw/ih,{self.OUTPUT_WIDTH}/{self.OUTPUT_HEIGHT}),"
            f"-1,{self.OUTPUT_WIDTH})':h='if(gt(iw/ih,{self.OUTPUT_WIDTH}/{self.OUTPUT_HEIGHT}),"
            f"{self.OUTPUT_HEIGHT},-1)',"
            
            # Étape 2: S'assurer des dimensions minimales et recadrer au centre
            f"scale=w='max(iw,{self.OUTPUT_WIDTH})':h='max(ih,{self.OUTPUT_HEIGHT})',"
            f"crop={self.OUTPUT_WIDTH}:{self.OUTPUT_HEIGHT}:(iw-{self.OUTPUT_WIDTH})/2:(ih-{self.OUTPUT_HEIGHT})/2,"
            
            # Étape 3: Ajouter le texte centré "Remix by AI"
            # Utilise une police système Linux standard
            f"drawtext=text='{self.text_overlay}':"
            f"fontsize=72:"
            f"fontcolor=white:"
            f"borderw=3:"
            f"bordercolor=black:"
            f"x=(w-text_w)/2:"  # Centrage horizontal
            f"y=(h-text_h)/2"   # Centrage vertical
        )
        
        cmd = [
            "ffmpeg",
            "-y",                           # Écraser le fichier de sortie si existant
            "-i", str(self.input_path),     # Fichier d'entrée
            "-t", str(self.duration),       # Durée à extraire (30 secondes)
            "-vf", filter_complex,          # Filtres vidéo
            "-c:v", "libx264",              # Codec vidéo H.264
            "-preset", "medium",            # Compromis vitesse/qualité
            "-crf", "23",                   # Qualité (18-28, plus bas = meilleur)
            "-c:a", "aac",                  # Codec audio AAC
            "-b:a", "128k",                 # Bitrate audio
            "-movflags", "+faststart",      # Optimisation pour streaming web
            "-pix_fmt", "yuv420p",          # Format pixel compatible
            str(self.output_path)           # Fichier de sortie
        ]
        
        return cmd
    
    def process(self) -> Path:
        """
        Exécute le traitement complet de la vidéo.
        
        Cette méthode:
        1. Crée un répertoire temporaire
        2. Exécute FFmpeg avec tous les filtres
        3. Nettoie les fichiers temporaires
        4. Retourne le chemin du fichier de sortie
        
        Returns:
            Path: Chemin vers le fichier MP4 généré
        
        Raises:
            VideoProcessorError: En cas d'erreur durant le traitement
        """
        try:
            # Création du répertoire temporaire
            self._create_temp_dir()
            
            # Récupération des infos vidéo
            width, height, source_duration = self._get_video_info()
            
            # Avertissement si la vidéo est plus courte que la durée demandée
            if source_duration > 0 and source_duration < self.duration:
                logger.warning(
                    f"La vidéo source ({source_duration}s) est plus courte que "
                    f"la durée demandée ({self.duration}s). "
                    f"La vidéo complète sera utilisée."
                )
            
            # Construction et exécution de la commande FFmpeg
            cmd = self._build_ffmpeg_command()
            logger.info(f"Exécution de FFmpeg...")
            logger.debug(f"Commande: {' '.join(cmd)}")
            
            # Exécution de FFmpeg
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )
            
            # Vérification du résultat
            if result.returncode != 0:
                error_msg = result.stderr[-1000:] if result.stderr else "Erreur inconnue"
                raise VideoProcessorError(f"FFmpeg a échoué: {error_msg}")
            
            # Vérification que le fichier de sortie existe
            if not self.output_path.exists():
                raise VideoProcessorError("Le fichier de sortie n'a pas été créé")
            
            # Récupération de la taille du fichier
            file_size = self.output_path.stat().st_size / (1024 * 1024)  # En Mo
            logger.info(f"Traitement terminé! Fichier créé: {self.output_path} ({file_size:.2f} Mo)")
            
            return self.output_path
            
        except subprocess.CalledProcessError as e:
            raise VideoProcessorError(f"Erreur lors de l'exécution de FFmpeg: {e}")
        
        finally:
            # Nettoyage des fichiers temporaires (toujours exécuté)
            self._cleanup_temp_files()
    
    def process_with_custom_text_position(
        self,
        x: str = "(w-text_w)/2",
        y: str = "h-th-50"
    ) -> Path:
        """
        Traite la vidéo avec une position de texte personnalisée.
        
        Args:
            x: Expression FFmpeg pour la position X (défaut: centré)
            y: Expression FFmpeg pour la position Y (défaut: en bas)
        
        Returns:
            Path: Chemin vers le fichier de sortie
        """
        # Sauvegarde de la méthode originale
        original_build = self._build_ffmpeg_command
        
        def custom_build():
            cmd = original_build()
            # Remplace les positions dans le filtre
            for i, arg in enumerate(cmd):
                if "drawtext=" in arg:
                    cmd[i] = arg.replace(
                        "x=(w-text_w)/2", f"x={x}"
                    ).replace(
                        "y=(h-text_h)/2", f"y={y}"
                    )
            return cmd
        
        self._build_ffmpeg_command = custom_build
        try:
            return self.process()
        finally:
            self._build_ffmpeg_command = original_build


def process_video(
    input_path: str,
    output_path: Optional[str] = None,
    duration: int = 30,
    text: str = "Remix by AI"
) -> str:
    """
    Fonction utilitaire pour traiter une vidéo rapidement.
    
    Args:
        input_path: Chemin vers la vidéo source
        output_path: Chemin de sortie (optionnel)
        duration: Durée à extraire en secondes (défaut: 30)
        text: Texte à afficher (défaut: "Remix by AI")
    
    Returns:
        str: Chemin vers le fichier de sortie
    
    Example:
        >>> output = process_video("ma_video.mp4")
        >>> print(f"Vidéo traitée: {output}")
    """
    processor = VideoProcessor(
        input_path=input_path,
        output_path=output_path,
        duration=duration,
        text_overlay=text
    )
    return str(processor.process())


# Point d'entrée pour exécution en ligne de commande
if __name__ == "__main__":
    import argparse
    
    # Configuration des arguments CLI
    parser = argparse.ArgumentParser(
        description="Traitement vidéo: coupe, format vertical 9:16, ajout de texte",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples d'utilisation:
  python video_processor.py video.mp4
  python video_processor.py video.mp4 -o output.mp4
  python video_processor.py video.mp4 -d 60 -t "Mon Texte"
        """
    )
    
    parser.add_argument(
        "input",
        help="Chemin vers la vidéo d'entrée"
    )
    parser.add_argument(
        "-o", "--output",
        help="Chemin vers la vidéo de sortie (optionnel)"
    )
    parser.add_argument(
        "-d", "--duration",
        type=int,
        default=30,
        help="Durée à extraire en secondes (défaut: 30)"
    )
    parser.add_argument(
        "-t", "--text",
        default="Remix by AI",
        help="Texte à afficher sur la vidéo (défaut: 'Remix by AI')"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Affiche les informations de débogage"
    )
    
    args = parser.parse_args()
    
    # Configuration du niveau de log
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Traitement de la vidéo
        output = process_video(
            input_path=args.input,
            output_path=args.output,
            duration=args.duration,
            text=args.text
        )
        print(f"\n✅ Succès! Vidéo générée: {output}")
        
    except FileNotFoundError as e:
        print(f"\n❌ Erreur: {e}")
        exit(1)
        
    except VideoProcessorError as e:
        print(f"\n❌ Erreur de traitement: {e}")
        exit(1)
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Traitement interrompu par l'utilisateur")
        exit(130)
