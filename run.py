from app import create_app
from flask_cors import CORS

app = create_app()

# CORS konfiguracija - prihvata sve zahteve
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "Access-Control-Allow-Credentials"],
        "supports_credentials": True
    }
})

if __name__ == '__main__':
    app.run(debug=True) 