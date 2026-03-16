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
    from models import StockReceipt, Product, Sale
    from datetime import datetime, date, timedelta
    
    today = date.today()
    start_of_month = date(today.year, today.month, 1)
    
    # 1. Total Products
    total_products = Product.query.filter_by(user_id=current_user.id).count()
    
    # 2. Total Inventory Value & Low Stock
    all_products = Product.query.filter_by(user_id=current_user.id).all()
    total_inv_value = 0
    low_stock_count = 0
    active_receipts = StockReceipt.query.filter(StockReceipt.user_id == current_user.id, StockReceipt.remaining_quantity > 0).all()
    
    # Pre-map stock to products for efficiency
    stock_map = {}
    for r in active_receipts:
        stock_map[r.product_id] = stock_map.get(r.product_id, 0) + r.remaining_quantity
        
    for p in all_products:
        p_stock = stock_map.get(p.id, 0)
        total_inv_value += p_stock * (p.pts_price or 0)
        if p_stock < 20:
            low_stock_count += 1
            
    # 3. Expiring Soon (< 90 days)
    ninety_days = today + timedelta(days=90)
    expiring_soon_count = StockReceipt.query.filter(
        StockReceipt.user_id == current_user.id,
        StockReceipt.remaining_quantity > 0,
        StockReceipt.expiry_date <= ninety_days
    ).count()
    
    # 4. Today's Sales
    today_sales_value = db.session.query(db.func.sum(Sale.value)).filter(
        Sale.user_id == current_user.id,
        Sale.sale_date == today
    ).scalar() or 0
    
    # 5. Monthly Sales
    monthly_sales_value = db.session.query(db.func.sum(Sale.value)).filter(
        Sale.user_id == current_user.id,
        Sale.sale_date >= start_of_month
    ).scalar() or 0
    
    # 6. Monthly Sales Trend (Real Data)
    sales_trend_data = db.session.query(
        db.func.date_trunc('month', Sale.sale_date).label('month'),
        db.func.sum(Sale.value).label('total_sales')
    ).filter_by(user_id=current_user.id).group_by('month').order_by('month').all()
    
    chart_labels = [d.month.strftime('%b %Y') for d in sales_trend_data]
    chart_values = [float(d.total_sales) for d in sales_trend_data]
    
    # 7. Product Distribution (Pie Chart)
    prod_dist_data = db.session.query(
        Product.product_name,
        db.func.sum(Sale.value).label('total')
    ).join(Sale).filter(Sale.user_id == current_user.id).group_by(Product.product_name).order_by(db.func.sum(Sale.value).desc()).limit(5).all()
    
    pie_labels = [d.product_name for d in prod_dist_data]
    pie_values = [float(d.total) for d in prod_dist_data]
    
    return render_template('dashboard.html', 
                            total_products=total_products,
                            total_inv_value=total_inv_value,
                            expiring_soon_count=expiring_soon_count,
                            today_sales_value=today_sales_value,
                            monthly_sales_value=monthly_sales_value,
                            low_stock_count=low_stock_count,
                            chart_labels=chart_labels,
                            chart_values=chart_values,
                            pie_labels=pie_labels,
                            pie_values=pie_values)

@main_bp.route('/expiry_dashboard')
@login_required
def expiry_dashboard():
    from models import StockReceipt, Product
    from datetime import date, timedelta
    
    today = date.today()
    # Explicit join to ensure product data is available and avoid attribute errors
    batches = StockReceipt.query.join(Product).filter(
        StockReceipt.user_id == current_user.id,
        StockReceipt.remaining_quantity > 0
    ).order_by(StockReceipt.expiry_date.asc()).all()
    
    # Enrich batches with days remaining and color
    for b in batches:
        # Safe access to product name
        b.p_name = b.product.product_name if b.product else "Unknown Product"
        if b.expiry_date:
            b.days_remaining = (b.expiry_date - today).days
            if b.days_remaining < 60:
                b.status_color = 'danger' # Red
            elif b.days_remaining < 120:
                b.status_color = 'warning' # Orange
            else:
                b.status_color = 'success' # Green
        else:
            b.days_remaining = 999
            b.status_color = 'secondary'
            
    return render_template('expiry_dashboard.html', batches=batches)
