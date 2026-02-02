"""
Flask Backend pour Générateur Vidéo V1
Compatible avec Render - Gestion d'upload et traitement vidéo
"""

import os
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from video_processor import process_video

# ============================================
# Configuration de l'application Flask
# ============================================
app = Flask(__name__)

# Configuration des chemins (relatifs au fichier app.py)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
OUTPUT_FOLDER = os.path.join(BASE_DIR, 'outputs')

# Configuration des uploads (100 Mo maximum)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 Mo

# Extensions vidéo autorisées
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm', 'wmv', 'flv'}


def create_directories():
    """Crée automatiquement les dossiers uploads/ et outputs/ s'ils n'existent pas"""
    for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER]:
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f"[INFO] Dossier créé: {folder}")


def allowed_file(filename):
    """Vérifie si l'extension du fichier est autorisée"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_base_url():
    """Récupère l'URL de base (compatible Render ou localhost)"""
    render_url = os.environ.get('RENDER_EXTERNAL_URL')
    if render_url:
        return render_url
    return request.host_url.rstrip('/')


# ============================================
# Endpoints de l'API
# ============================================

@app.route('/', methods=['GET'])
def index():
    """Endpoint de santé - vérifie que l'API fonctionne"""
    return jsonify({
        'status': 'ok',
        'message': 'Générateur Vidéo V1 - API opérationnelle',
        'max_upload_size': '100 Mo',
        'allowed_formats': list(ALLOWED_EXTENSIONS)
    })


@app.route('/upload', methods=['POST'])
def upload_video():
    """
    Endpoint principal pour l'upload et le traitement de vidéos
    
    Requête: multipart/form-data avec champ 'video'
    Réponse: JSON avec URL de la vidéo générée
    """
    try:
        # Vérification de la présence du fichier
        if 'video' not in request.files:
            return jsonify({
                'success': False,
                'error': 'Aucun fichier vidéo fourni (champ "video" requis)'
            }), 400
        
        file = request.files['video']
        
        # Vérification du nom de fichier
        if file.filename == '':
            return jsonify({'success': False, 'error': 'Nom de fichier vide'}), 400
        
        # Vérification de l'extension
        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': f'Extension non autorisée. Formats acceptés: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400
        
        # Sécurisation et sauvegarde du fichier uploadé
        filename = secure_filename(file.filename)
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(input_path)
        print(f"[INFO] Fichier uploadé: {input_path}")
        
        # Appel au processeur vidéo pour le traitement
        output_filename = process_video(input_path, app.config['OUTPUT_FOLDER'])
        
        # Construction de l'URL de la vidéo générée
        base_url = get_base_url()
        video_url = f"{base_url}/outputs/{output_filename}"
        
        # Retour JSON avec succès
        return jsonify({
            'success': True,
            'message': 'Vidéo traitée avec succès',
            'original_filename': filename,
            'output_filename': output_filename,
            'video_url': video_url
        }), 200
        
    except Exception as e:
        # Gestion globale des erreurs
        print(f"[ERROR] Erreur lors du traitement: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Erreur serveur: {str(e)}'
        }), 500


@app.route('/outputs/<filename>', methods=['GET'])
def serve_output(filename):
    """Sert les fichiers vidéo générés depuis le dossier outputs/"""
    try:
        return send_from_directory(app.config['OUTPUT_FOLDER'], filename)
    except FileNotFoundError:
        return jsonify({'success': False, 'error': 'Fichier non trouvé'}), 404


@app.errorhandler(413)
def file_too_large(error):
    """Gestion de l'erreur fichier trop volumineux (> 100 Mo)"""
    return jsonify({
        'success': False,
        'error': 'Fichier trop volumineux. Taille maximale: 100 Mo'
    }), 413


# ============================================
# Initialisation et démarrage
# ============================================

# Création automatique des dossiers au démarrage
create_directories()

if __name__ == '__main__':
    # Port dynamique pour Render, 5000 par défaut en local
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    print(f"[INFO] Serveur démarré sur le port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)
