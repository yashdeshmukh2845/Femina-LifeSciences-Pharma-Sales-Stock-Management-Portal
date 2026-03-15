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
    
    # Data for charts
    # 1. Monthly Sales Trend
    monthly_sales = db.session.query(
        func.date_trunc('month', Sale.sale_date).label('month'),
        func.sum(Sale.value).label('total_sales')
    ).filter_by(user_id=current_user.id)\
     .group_by('month')\
     .order_by('month').all()
    
    sales_labels = [s.month.strftime('%b %Y') for s in monthly_sales]
    sales_values = [float(s.total_sales) for s in monthly_sales]

    # 2. Product Distribution
    product_dist = db.session.query(
        Product.product_name,
        func.sum(Sale.value).label('total')
    ).join(Sale, Sale.product_id == Product.id)\
     .filter(Sale.user_id == current_user.id)\
     .group_by(Product.product_name)\
     .order_by(func.sum(Sale.value).desc()).limit(10).all()

    pie_labels = [p.product_name for p in product_dist]
    pie_values = [float(p.total) for p in product_dist]

    return render_template('dashboard.html', 
                           total_sales_value=total_sales_value,
                           total_sales_count=total_sales_count,
                           total_products=total_products,
                           total_customers=total_customers,
                           sales_labels=sales_labels,
                           sales_values=sales_values,
                           pie_labels=pie_labels,
                           pie_values=pie_values)
