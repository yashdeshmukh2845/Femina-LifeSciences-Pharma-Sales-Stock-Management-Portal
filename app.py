from flask import Flask, render_template, redirect, url_for, flash
from flask_login import LoginManager
from models import db, User
from config import Config
import os

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

if __name__ == '__main__':
    app.run(debug=True)
