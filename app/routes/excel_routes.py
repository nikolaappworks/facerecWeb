from flask import Blueprint, jsonify, request
from app.controllers.excel_controller import ExcelController
from app.services.excel_service import ExcelService
from flask import current_app

excel_bp = Blueprint('excel', __name__, url_prefix='/api/excel')

@excel_bp.route('/process', methods=['GET'])
def process_excel():
    controller = ExcelController()
    result = controller.process_excel_and_fetch_images()
    return jsonify(result)

@excel_bp.route('/check-excel', methods=['GET'])
def check_excel_file():
    """
    API endpoint za proveru Excel fajla i pokretanje obrade u pozadini
    
    Proverava da li Excel fajl postoji i da li sadrži podatke.
    Ako je sve u redu, pokreće obradu u pozadini.
    
    Query parametri:
        country (str, obavezno): Zemlja za koju se traže poznate ličnosti
    
    Returns:
        JSON: Status provere Excel fajla i pokretanja obrade
    """
    try:
        # Dobijanje parametra country iz URL-a
        country = request.args.get('country')
        
        # Provera da li je country parametar prosleđen
        if not country:
            return jsonify({
                "success": False,
                "message": "Parametar 'country' je obavezan"
            }), 400
        
        # Inicijalizacija Excel servisa
        excel_service = ExcelService()
        
        # Poziv metode za proveru Excel fajla
        check_result = excel_service.check_excel_file()
        
        # Ako je provera uspešna, pokreni thread za obradu
        if check_result["success"]:
            result = excel_service.start_processing_thread(check_result, country)
        else:
            result = check_result
        
        # Određivanje HTTP status koda na osnovu rezultata
        status_code = 200 if result["success"] else 400
        if "nije pronađen" in result.get("message", ""):
            status_code = 404
            
        return jsonify(result), status_code
        
    except Exception as e:
        current_app.logger.error(f"Greška prilikom provere Excel fajla: {str(e)}")
        return jsonify({
            "success": False, 
            "message": f"Greška: {str(e)}"
        }), 500 