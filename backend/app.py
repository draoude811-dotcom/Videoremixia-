"""
Backend Flask pour application de génération vidéo.
Prêt pour déploiement sur Render.
"""

import os
import uuid
import tempfile
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename

# Import de la fonction de traitement vidéo
from video_processor import process_video


# =============================================================================
# CONFIGURATION
# =============================================================================

app = Flask(__name__)

# Activation CORS pour toutes les origines
CORS(app)

# Limite de taille fichier : 500 MB
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500 MB en bytes

# Extensions vidéo autorisées
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm', 'flv', 'wmv'}

# Répertoire temporaire pour les uploads
UPLOAD_FOLDER = tempfile.gettempdir()


# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================

def allowed_file(filename: str) -> bool:
    """
    Vérifie si l'extension du fichier est autorisée.
    
    Args:
        filename: Nom du fichier à vérifier
        
    Returns:
        True si l'extension est valide, False sinon
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def generate_unique_filename(original_filename: str) -> str:
    """
    Génère un nom de fichier unique pour éviter les collisions.
    
    Args:
        original_filename: Nom original du fichier
        
    Returns:
        Nouveau nom de fichier unique
    """
    ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else 'mp4'
    unique_id = uuid.uuid4().hex
    return f"{unique_id}.{ext}"


def cleanup_temp_file(filepath: str) -> None:
    """
    Supprime un fichier temporaire s'il existe.
    
    Args:
        filepath: Chemin du fichier à supprimer
    """
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except OSError:
        pass  # Ignore les erreurs de suppression


# =============================================================================
# ENDPOINTS
# =============================================================================

@app.route('/upload', methods=['POST'])
def upload_video():
    """
    Endpoint POST /upload
    
    Reçoit un fichier vidéo, le sauvegarde temporairement,
    lance le traitement et retourne l'URL de la vidéo générée.
    
    Returns:
        JSON avec l'URL de la vidéo générée ou message d'erreur
    """
    temp_filepath = None
    
    try:
        # Vérification de la présence du fichier dans la requête
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'Aucun fichier fourni dans la requête'
            }), 400
        
        file = request.files['file']
        
        # Vérification que le fichier a un nom
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'Aucun fichier sélectionné'
            }), 400
        
        # Vérification de l'extension du fichier
        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': f'Type de fichier non autorisé. Extensions acceptées: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400
        
        # Sécurisation et génération du nom de fichier
        original_filename = secure_filename(file.filename)
        unique_filename = generate_unique_filename(original_filename)
        temp_filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
        
        # Sauvegarde temporaire du fichier
        file.save(temp_filepath)
        
        # Appel de la fonction de traitement vidéo
        result = process_video(temp_filepath)
        
        # Vérification du résultat du traitement
        if result is None:
            return jsonify({
                'success': False,
                'error': 'Échec du traitement vidéo'
            }), 500
        
        # Retour succès avec URL de la vidéo générée
        return jsonify({
            'success': True,
            'video_url': result,
            'message': 'Vidéo traitée avec succès'
        }), 200
        
    except Exception as e:
        # Gestion des erreurs inattendues
        return jsonify({
            'success': False,
            'error': f'Erreur serveur: {str(e)}'
        }), 500
        
    finally:
        # Nettoyage du fichier temporaire
        if temp_filepath:
            cleanup_temp_file(temp_filepath)


@app.route('/health', methods=['GET'])
def health_check():
    """
    Endpoint de vérification de santé pour Render.
    
    Returns:
        JSON confirmant que le service est opérationnel
    """
    return jsonify({
        'status': 'healthy',
        'service': 'video-generation-api'
    }), 200


# =============================================================================
# GESTIONNAIRES D'ERREURS
# =============================================================================

@app.errorhandler(413)
def request_entity_too_large(error):
    """
    Gestion de l'erreur de dépassement de taille de fichier.
    """
    return jsonify({
        'success': False,
        'error': 'Fichier trop volumineux. Limite: 500 MB'
    }), 413


@app.errorhandler(404)
def not_found(error):
    """
    Gestion des routes non trouvées.
    """
    return jsonify({
        'success': False,
        'error': 'Endpoint non trouvé'
    }), 404


@app.errorhandler(405)
def method_not_allowed(error):
    """
    Gestion des méthodes HTTP non autorisées.
    """
    return jsonify({
        'success': False,
        'error': 'Méthode HTTP non autorisée'
    }), 405


@app.errorhandler(500)
def internal_server_error(error):
    """
    Gestion des erreurs serveur internes.
    """
    return jsonify({
        'success': False,
        'error': 'Erreur serveur interne'
    }), 500


# =============================================================================
# POINT D'ENTRÉE
# =============================================================================

if __name__ == '__main__':
    # Configuration pour développement local
    # En production sur Render, Gunicorn sera utilisé
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )
