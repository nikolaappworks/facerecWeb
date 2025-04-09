from flask import Blueprint, jsonify, request
from app.services.image_service import ImageService

image_bp = Blueprint('image', __name__)

@image_bp.route('/test', methods=['GET'])
def test_route():
    return jsonify({"message": "Test ruta radi!"})

@image_bp.route('/upload', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({"error": "Nema slike u zahtevu"}), 400
    
    return jsonify({"message": "Slika primljena"}), 200

@image_bp.route('/process', methods=['POST'])
def process_image():
    if 'image' not in request.files:
        return jsonify({"error": "Nema slike u zahtevu"}), 400
    
    return jsonify({"message": "Slika obrađena"}), 200

class ImageController:
    @staticmethod
    def handle_image_upload(image_file, person, created_date, domain):
        if not image_file or not ImageService.allowed_file(image_file.filename):
            return {
                "error": "Nevažeći format fajla",
                "domain": domain
            }
        
        # Pokrenemo asinhronu obradu
        ImageService.process_image_async(
            image_file=image_file,
            person=person,
            created_date=created_date,
            domain=domain
        )
        
        return {
            "message": "Slika je primljena i biće obrađena",
            "status": "processing",
            "person": person,
            "created_date": created_date.strftime('%Y-%m-%d'),
            "domain": domain
        } 