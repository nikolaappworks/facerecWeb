import logging
import os
import threading
from app.services.object_detection_service import ObjectDetectionService

logger = logging.getLogger(__name__)

class ObjectDetectionController:
    """
    Controller for handling object detection related operations
    """
    
    @staticmethod
    def handle_detection_image(image_file):
        """
        Handle the uploaded image for object detection
        
        Args:
            image_file: The uploaded image file
            
        Returns:
            dict: Result of the operation
        """
        try:
            # Create service instance
            detection_service = ObjectDetectionService()
            
            # Process and save the image
            result = detection_service.process_and_save_image(image_file)
            
            # Start background processing thread
            thread = threading.Thread(
                target=ObjectDetectionService._process_image_in_background,
                args=(result["path"],)
            )
            thread.daemon = True
            thread.start()
            
            return {
                "success": True,
                "message": "Image successfully uploaded for object detection. Processing started in background.",
                "data": result
            }
            
        except Exception as e:
            logger.error(f"Error processing image for object detection: {str(e)}")
            raise
    