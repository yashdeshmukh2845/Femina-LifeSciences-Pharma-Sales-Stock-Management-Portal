from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from models import Sale, Product, db
from sqlalchemy import func
from datetime import datetime

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@login_required
def index():
    return redirect(url_for('main.dashboard'))

@main_bp.route('/dashboard')
@login_required
def dashboard():
    # Calculate KPIs
    sales_query = Sale.query.filter_by(user_id=current_user.id)
    total_sales_value = db.session.query(db.func.sum(Sale.value)).filter_by(user_id=current_user.id).scalar() or 0
    total_sales_count = sales_query.count()
    total_products = Product.query.filter_by(user_id=current_user.id).count()
    total_customers = db.session.query(db.func.count(db.func.distinct(Sale.customer_name))).filter_by(user_id=current_user.id).scalar() or 0
    
    # Data for charts (placeholder for now, can be populated with real trends)
    return render_template('dashboard.html', 
                           total_sales_value=total_sales_value,
                           total_sales_count=total_sales_count,
                           total_products=total_products,
                           total_customers=total_customers)
