"""
Backend Flask pour application de génération vidéo.
Prêt pour déploiement sur Render.
"""

import os
import uuid
import tempfile
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

from video_processor import process_video

# =============================================================================
# CONFIGURATION
# =============================================================================

app = Flask(__name__)
CORS(app)

app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500 MB

ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm'}
UPLOAD_FOLDER = tempfile.gettempdir()
OUTPUT_FOLDER = "outputs"

# =============================================================================
# UTILITAIRES
# =============================================================================

def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# =============================================================================
# ROUTES
# =============================================================================

@app.route('/upload', methods=['POST'])
def upload_video():
    temp_filepath = None

    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'Aucun fichier fourni'}), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({'success': False, 'error': 'Nom de fichier vide'}), 400

        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'Format vidéo non autorisé'}), 400

        filename = secure_filename(file.filename)
        unique_name = f"{uuid.uuid4().hex}_{filename}"
        temp_filepath = os.path.join(UPLOAD_FOLDER, unique_name)

        file.save(temp_filepath)

        video_url = process_video(temp_filepath)

        return jsonify({
            'success': True,
            'video_url': video_url
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

    finally:
        if temp_filepath and os.path.exists(temp_filepath):
            os.remove(temp_filepath)

@app.route('/outputs/<filename>')
def serve_output(filename):
    return send_from_directory(OUTPUT_FOLDER, filename, as_attachment=False)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'}), 200

# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
