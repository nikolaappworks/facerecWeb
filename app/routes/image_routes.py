from flask import Blueprint, jsonify, request
from app.controllers.image_controller import ImageController
from app.services.domain_service import DomainService
from datetime import datetime
from app.controllers.recognition_controller import RecognitionController
import logging

image_routes = Blueprint('image', __name__)

logger = logging.getLogger(__name__)

@image_routes.route('/upload-with-domain', methods=['POST'])
def upload_with_domain():
    # Provera da li postoje svi potrebni parametri
    if 'image' not in request.files:
        return jsonify({"error": "Nema slike u zahtevu"}), 400
    
    if 'person' not in request.form:
        return jsonify({"error": "Nedostaje parametar 'person'"}), 400
        
    if 'created_date' not in request.form:
        return jsonify({"error": "Nedostaje parametar 'created_date'"}), 400
    
    try:
        # Validacija datuma
        created_date = datetime.strptime(request.form['created_date'], '%Y-%m-%d')
    except ValueError:
        return jsonify({"error": "Neispravan format datuma. Koristite YYYY-MM-DD"}), 400
    
    image_file = request.files['image']
    person = request.form['person']
    domain = DomainService.extract_domain(request)
    
    result = ImageController.handle_image_upload(
        image_file=image_file,
        person=person,
        created_date=created_date,
        domain=domain
    )
    return jsonify(result), 202  # 202 Accepted status kod 

@image_routes.route('/recognize', methods=['POST'])
def recognize_face():
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image provided'}), 400
            
        image_file = request.files['image']
        if not image_file.filename:
            return jsonify({'error': 'No selected file'}), 400
            
        # Izvuci domain iz request-a koristeći DomainService
        domain = DomainService.extract_domain(request)
        
        # Čitaj sliku kao bytes
        image_bytes = image_file.read()
        
        # Pozovi kontroler
        result = RecognitionController.recognize_face(image_bytes, domain)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in recognize_face endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500 