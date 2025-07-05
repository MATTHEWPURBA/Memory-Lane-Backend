import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from flask_socketio import SocketIO
from flask_migrate import Migrate
import redis
from config import config

# Initialize extensions
db = SQLAlchemy()
jwt = JWTManager()
limiter = Limiter(key_func=get_remote_address)
migrate = Migrate()
socketio = SocketIO()

# Redis connection
redis_client = None

def create_app(config_name=None):
    """Application factory pattern."""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Create upload directory if it doesn't exist
    upload_dir = app.config['UPLOAD_FOLDER']
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
    
    # Initialize extensions with app
    db.init_app(app)
    jwt.init_app(app)
    limiter.init_app(app)
    migrate.init_app(app, db)
    
    # Initialize CORS
    CORS(app, origins=app.config['CORS_ORIGINS'])
    
    # Initialize SocketIO
    socketio.init_app(
        app, 
        cors_allowed_origins=app.config['SOCKETIO_CORS_ALLOWED_ORIGINS'],
        async_mode=app.config['SOCKETIO_ASYNC_MODE']
    )
    
    # Initialize Redis
    global redis_client
    redis_client = redis.from_url(app.config['REDIS_URL'])
    
    # JWT token blacklist check
    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        jti = jwt_payload['jti']
        token_in_redis = redis_client.get(jti)
        return token_in_redis is not None
    
    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.users import users_bp
    from app.routes.memories import memories_bp
    from app.routes.interactions import interactions_bp
    from app.routes.geospatial import geospatial_bp
    from app.routes.uploads import uploads_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(users_bp, url_prefix='/api/users')
    app.register_blueprint(memories_bp, url_prefix='/api/memories')
    app.register_blueprint(interactions_bp, url_prefix='/api/interactions')
    app.register_blueprint(geospatial_bp, url_prefix='/api/geospatial')
    app.register_blueprint(uploads_bp, url_prefix='/api/uploads')
    
    # Register error handlers
    from app.utils.error_handlers import register_error_handlers
    register_error_handlers(app)
    
    # Register SocketIO events
    from app.events import socketio_events
    
    @app.route('/health')
    def health_check():
        """Health check endpoint."""
        return {'status': 'healthy', 'message': 'Memory Lane Backend is running!'}, 200
    
    @app.route('/')
    def index():
        """Root endpoint."""
        return {
            'message': 'Welcome to Memory Lane Backend API',
            'version': '1.0.0',
            'docs': '/api/docs'
        }, 200
    
    return app 