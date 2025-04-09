from app.services.recognition_service import RecognitionService
import logging

logger = logging.getLogger(__name__)

class RecognitionController:
    @staticmethod
    def recognize_face(image_bytes, domain):
        try:
            return RecognitionService.recognize_face(image_bytes, domain)
        except Exception as e:
            logger.error(f"Error in RecognitionController.recognize_face: {str(e)}")
            raise 