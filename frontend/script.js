frontend/script.js
// ============================================
// VideoGen - Script Principal
// ============================================
// Configuration
const API_BASE_URL = 'http://localhost:5000';
const ENDPOINTS = {
    upload: `${API_BASE_URL}/api/upload`,
    generate: `${API_BASE_URL}/api/generate`,
    status: `${API_BASE_URL}/api/status`,
    download: `${API_BASE_URL}/api/download`
};
// État de l'application
let selectedFile = null;
let generatedVideoUrl = null;
let statusCheckInterval = null;
// ============================================
// Initialisation
// ============================================
document.addEventListener('DOMContentLoaded', () => {
    initDragAndDrop();
    initFileInput();
});
// ============================================
// Drag and Drop
// ============================================
function initDragAndDrop() {
    const uploadZone = document.getElementById('uploadZone');
    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        e.stopPropagation();
        uploadZone.classList.add('border-purple-400', 'bg-purple-500/20');
    });
    uploadZone.addEventListener('dragleave', (e) => {
        e.preventDefault();
        e.stopPropagation();
        uploadZone.classList.remove('border-purple-400', 'bg-purple-500/20');
    });
    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        e.stopPropagation();
        uploadZone.classList.remove('border-purple-400', 'bg-purple-500/20');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            validateAndHandleFile(files[0]);
        }
    });
    uploadZone.addEventListener('click', () => {
        document.getElementById('videoInput').click();
    });
}
// ============================================
// Gestion des fichiers
// ============================================
function initFileInput() {
    const fileInput = document.getElementById('videoInput');
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            validateAndHandleFile(e.target.files[0]);
        }
    });
}
function validateAndHandleFile(file) {
    // Vérification du type
    if (!file.type.startsWith('video/')) {
        showError('Veuillez sélectionner un fichier vidéo valide.');
        return;
    }
    // Vérification de la taille (max 500MB)
    const maxSize = 500 * 1024 * 1024;
    if (file.size > maxSize) {
        showError('Le fichier est trop volumineux. Taille maximale : 500MB');
        return;
    }
    handleFile(file);
}
function handleFile(file) {
    selectedFile = file;
    
    // Mise à jour de l'interface
    document.getElementById('uploadContent').classList.add('hidden');
    document.getElementById('fileInfo').classList.remove('hidden');
    document.getElementById('fileName').textContent = file.name;
    document.getElementById('fileSize').textContent = formatFileSize(file.size);
    
    // Aperçu vidéo
    const preview = document.getElementById('videoPreview');
    const player = document.getElementById('previewPlayer');
    
    // Libérer l'ancienne URL si elle existe
    if (player.src) {
        URL.revokeObjectURL(player.src);
    }
    
    player.src = URL.createObjectURL(file);
    preview.classList.remove('hidden');
    
    // Activer le bouton de génération
    document.getElementById('generateBtn').disabled = false;
    
    // Masquer les erreurs précédentes
    hideError();
}
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}
// ============================================
// Génération de la vidéo
// ============================================
async function generateVideo() {
    if (!selectedFile) {
        showError('Veuillez sélectionner une vidéo.');
        return;
    }
    try {
        // Afficher le loader
        showLoader();
        hideError();
        // Créer le FormData
        const formData = new FormData();
        formData.append('video', selectedFile);
        // Upload du fichier
        updateProgress(10, 'Envoi de la vidéo...');
        
        const uploadResponse = await fetch(ENDPOINTS.upload, {
            method: 'POST',
            body: formData
        });
        if (!uploadResponse.ok) {
            const errorData = await uploadResponse.json().catch(() => ({}));
            throw new Error(errorData.message || `Erreur d'upload: ${uploadResponse.status}`);
        }
        const uploadResult = await uploadResponse.json();
        const taskId = uploadResult.task_id;
        updateProgress(30, 'Traitement en cours...');
        // Lancer la génération
        const generateResponse = await fetch(ENDPOINTS.generate, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ task_id: taskId })
        });
        if (!generateResponse.ok) {
            const errorData = await generateResponse.json().catch(() => ({}));
            throw new Error(errorData.message || 'Erreur lors de la génération');
        }
        // Vérifier le statut périodiquement
        await checkGenerationStatus(taskId);
    } catch (error) {
        console.error('Erreur:', error);
        showError(error.message || 'Une erreur est survenue lors de la génération.');
        hideLoader();
        showGenerateButton();
    }
}
async function checkGenerationStatus(taskId) {
    return new Promise((resolve, reject) => {
        let progress = 30;
        
        statusCheckInterval = setInterval(async () => {
            try {
                const response = await fetch(`${ENDPOINTS.status}/${taskId}`);
                
                if (!response.ok) {
                    throw new Error('Erreur lors de la vérification du statut');
                }
                const data = await response.json();
                // Mise à jour de la progression
                if (data.progress) {
                    progress = Math.max(progress, data.progress);
                } else {
                    progress = Math.min(progress + 5, 90);
                }
                
                updateProgress(progress, data.message || 'Traitement en cours...');
                // Vérification du statut
                if (data.status === 'completed') {
                    clearInterval(statusCheckInterval);
                    updateProgress(100, 'Terminé !');
                    generatedVideoUrl = data.video_url || `${ENDPOINTS.download}/${taskId}`;
                    onGenerationComplete();
                    resolve();
                } else if (data.status === 'error') {
                    clearInterval(statusCheckInterval);
                    reject(new Error(data.message || 'Erreur lors de la génération'));
                }
            } catch (error) {
                clearInterval(statusCheckInterval);
                reject(error);
            }
        }, 2000); // Vérification toutes les 2 secondes
        // Timeout après 5 minutes
        setTimeout(() => {
            if (statusCheckInterval) {
                clearInterval(statusCheckInterval);
                reject(new Error('Délai d\'attente dépassé'));
            }
        }, 5 * 60 * 1000);
    });
}
// ============================================
// Interface utilisateur - Loader
// ============================================
function showLoader() {
    document.getElementById('generateBtn').classList.add('hidden');
    document.getElementById('loadingZone').classList.remove('hidden');
    updateProgress(0, 'Initialisation...');
}
function hideLoader() {
    document.getElementById('loadingZone').classList.add('hidden');
}
function updateProgress(value, message = null) {
    const progressText = document.getElementById('progressText');
    const progressBar = document.getElementById('progressBar');
    const loadingMessage = document.getElementById('loadingMessage');
    
    if (progressText) progressText.textContent = value + '%';
    if (progressBar) progressBar.style.width = value + '%';
    if (loadingMessage && message) loadingMessage.textContent = message;
}
function showGenerateButton() {
    document.getElementById('generateBtn').classList.remove('hidden');
    document.getElementById('generateBtn').disabled = false;
}
// ============================================
// Génération terminée
// ============================================
function onGenerationComplete() {
    hideLoader();
    
    // Afficher la zone de succès
    document.getElementById('successZone').classList.remove('hidden');
    
    // Afficher les boutons
    const downloadBtn = document.getElementById('downloadBtn');
    const resetBtn = document.getElementById('resetBtn');
    
    downloadBtn.classList.remove('hidden');
    downloadBtn.classList.add('flex');
    
    resetBtn.classList.remove('hidden');
    resetBtn.classList.add('flex');
}
// ============================================
// Téléchargement
// ============================================
async function downloadVideo() {
    if (!generatedVideoUrl) {
        showError('Aucune vidéo à télécharger.');
        return;
    }
    try {
        const downloadBtn = document.getElementById('downloadBtn');
        downloadBtn.disabled = true;
        downloadBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Téléchargement...';
        // Télécharger le fichier
        const response = await fetch(generatedVideoUrl);
        
        if (!response.ok) {
            throw new Error('Erreur lors du téléchargement');
        }
        const blob = await response.blob();
        
        // Créer un lien de téléchargement
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `video_generee_${Date.now()}.mp4`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        // Libérer l'URL
        URL.revokeObjectURL(url);
        // Restaurer le bouton
        downloadBtn.disabled = false;
        downloadBtn.innerHTML = '<i class="fas fa-download"></i> Télécharger la vidéo';
    } catch (error) {
        console.error('Erreur de téléchargement:', error);
        showError('Erreur lors du téléchargement de la vidéo.');
        
        const downloadBtn = document.getElementById('downloadBtn');
        downloadBtn.disabled = false;
        downloadBtn.innerHTML = '<i class="fas fa-download"></i> Télécharger la vidéo';
    }
}
// ============================================
// Réinitialisation
// ============================================
function resetForm() {
    // Arrêter la vérification de statut si en cours
    if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
        statusCheckInterval = null;
    }
    // Réinitialiser les variables
    selectedFile = null;
    generatedVideoUrl = null;
    
    // Réinitialiser l'input fichier
    document.getElementById('videoInput').value = '';
    
    // Réinitialiser l'interface
    document.getElementById('uploadContent').classList.remove('hidden');
    document.getElementById('fileInfo').classList.add('hidden');
    document.getElementById('videoPreview').classList.add('hidden');
    document.getElementById('loadingZone').classList.add('hidden');
    document.getElementById('successZone').classList.add('hidden');
    
    // Réinitialiser les boutons
    const generateBtn = document.getElementById('generateBtn');
    generateBtn.classList.remove('hidden');
    generateBtn.disabled = true;
    
    const downloadBtn = document.getElementById('downloadBtn');
    downloadBtn.classList.add('hidden');
    downloadBtn.classList.remove('flex');
    
    const resetBtn = document.getElementById('resetBtn');
    resetBtn.classList.add('hidden');
    resetBtn.classList.remove('flex');
    
    // Réinitialiser la progression
    updateProgress(0);
    
    // Libérer et réinitialiser la source vidéo
    const player = document.getElementById('previewPlayer');
    if (player.src) {
        URL.revokeObjectURL(player.src);
    }
    player.src = '';
    
    // Masquer les erreurs
    hideError();
}
// ============================================
// Gestion des erreurs
// ============================================
function showError(message) {
    let errorZone = document.getElementById('errorZone');
    
    // Créer la zone d'erreur si elle n'existe pas
    if (!errorZone) {
        errorZone = document.createElement('div');
        errorZone.id = 'errorZone';
        errorZone.className = 'mb-6';
        
        const container = document.getElementById('loadingZone').parentElement;
        container.insertBefore(errorZone, document.getElementById('generateBtn').parentElement);
    }
    
    errorZone.innerHTML = `
        <div class="bg-red-500/10 rounded-2xl p-4 text-center border border-red-500/30">
            <div class="flex items-center justify-center gap-3">
                <i class="fas fa-exclamation-circle text-red-400 text-xl"></i>
                <p class="text-red-300">${escapeHtml(message)}</p>
            </div>
        </div>
    `;
    errorZone.classList.remove('hidden');
}
function hideError() {
    const errorZone = document.getElementById('errorZone');
    if (errorZone) {
        errorZone.classList.add('hidden');
    }
}
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
// ============================================
// Utilitaires
// ============================================
// Gestion des erreurs réseau globales
window.addEventListener('unhandledrejection', (event) => {
    console.error('Erreur non gérée:', event.reason);
});
// Confirmation avant de quitter si génération en cours
window.addEventListener('beforeunload', (event) => {
    if (statusCheckInterval) {
        event.preventDefault();
        event.returnValue = 'Une génération est en cours. Voulez-vous vraiment quitter ?';
        return event.returnValue;
    }
});
