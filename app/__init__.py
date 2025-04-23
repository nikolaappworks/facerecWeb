from flask import Flask
from config import Config
from app.routes.image_routes import image_routes
from app.routes.admin_routes import admin_routes

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Povećanje maksimalne veličine zahteva na 30MB
    app.config['MAX_CONTENT_LENGTH'] = 30 * 1024 * 1024  # 30MB
    
    # Registrujemo rute
    app.register_blueprint(image_routes)
    app.register_blueprint(admin_routes, url_prefix='/admin')
    
    return app 