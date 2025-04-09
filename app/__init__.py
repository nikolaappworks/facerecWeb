from flask import Flask
from config import Config
from app.routes.image_routes import image_routes

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Registrujemo rute
    app.register_blueprint(image_routes)

    return app 