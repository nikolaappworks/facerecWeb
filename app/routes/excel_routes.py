from flask import Blueprint, jsonify
from app.controllers.excel_controller import ExcelController

excel_bp = Blueprint('excel', __name__, url_prefix='/api/excel')

@excel_bp.route('/process', methods=['GET'])
def process_excel():
    controller = ExcelController()
    result = controller.process_excel_and_fetch_images()
    return jsonify(result) 