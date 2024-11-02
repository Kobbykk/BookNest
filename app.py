import os
from flask import Flask, render_template
import logging
from extensions import db, login_manager, mail

# Configure logging
logging.basicConfig(level=logging.INFO)

def create_app():
    app = Flask(__name__)
    
    # Configure app
    app.config.update(
        SECRET_KEY=os.environ.get("FLASK_SECRET_KEY", "a secret key"),
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL"),
        SQLALCHEMY_ENGINE_OPTIONS={
            "pool_recycle": 300,
            "pool_pre_ping": True,
        },
        MAIL_SERVER='smtp.gmail.com',
        MAIL_PORT=587,
        MAIL_USE_TLS=True,
        MAIL_USERNAME=os.environ.get('MAIL_USERNAME'),
        MAIL_PASSWORD=os.environ.get('MAIL_PASSWORD'),
        MAIL_DEFAULT_SENDER=os.environ.get('MAIL_USERNAME'),
        STRIPE_PUBLISHABLE_KEY=os.environ.get('STRIPE_PUBLISHABLE_KEY'),
        STRIPE_SECRET_KEY=os.environ.get('STRIPE_SECRET_KEY')
    )
    
    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    
    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'
    
    @login_manager.user_loader
    def load_user(user_id):
        from models import User
        return db.session.get(User, int(user_id))
    
    # Register blueprints
    from views.auth import auth
    from views.main import main
    from views.admin import admin
    from views.cart import cart
    
    app.register_blueprint(auth)
    app.register_blueprint(main)
    app.register_blueprint(admin)
    app.register_blueprint(cart)
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500
    
    # Ensure database tables exist
    with app.app_context():
        db.create_all()
        # Validate Stripe configuration
        if not app.config.get('STRIPE_SECRET_KEY') or not app.config.get('STRIPE_PUBLISHABLE_KEY'):
            app.logger.warning('Stripe API keys are not configured properly')
    
    return app

app = create_app()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
