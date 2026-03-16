from flask import Flask, render_template, redirect, url_for, flash
from flask_login import LoginManager
from models import db, User
from config import Config
import os
import logging

# Professional Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
)

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Import and register blueprints
from routes.auth import auth_bp
from routes.product import product_bp
from routes.sales import sales_bp
from routes.stock import stock_bp
from routes.reports import reports_bp
from routes.main import main_bp

app.register_blueprint(auth_bp)
app.register_blueprint(product_bp)
app.register_blueprint(sales_bp)
app.register_blueprint(stock_bp)
app.register_blueprint(reports_bp)
app.register_blueprint(main_bp)

@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f'Server Error: {error}')
    return render_template('error.html', message="Something went wrong internally. We have logged this error."), 500

@app.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', message="Oops! The page you're looking for doesn't exist."), 404

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
