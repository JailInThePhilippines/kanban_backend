from flask import Flask, jsonify
from pymongo import MongoClient
from dotenv import load_dotenv
from flask_cors import CORS
import os

# Load environment variables from .env file
load_dotenv()

def create_app():
    app = Flask(__name__)

    # Set configuration values from .env
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['MONGO_URI'] = os.getenv('MONGO_URI')
    
    # Enable CORS for all routes and origins
    CORS(app)
    
    # Initialize MongoDB client and set as attribute of app
    client = MongoClient(app.config['MONGO_URI'])
    app.db = client.get_database()

    # Register blueprints for routes
    from .routes import bp
    app.register_blueprint(bp)

    # Error handling
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(500)
    def server_error(error):
        return jsonify({"error": "Server error"}), 500
    
    return app