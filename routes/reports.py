from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required, current_user
from models import db, Sale, Product, Stock
from datetime import datetime
import pandas as pd
import io

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/reports/stock-statement')
@login_required
def stock_statement():
    month = int(request.args.get('month', datetime.now().month))
    year = int(request.args.get('year', datetime.now().year))
    
    # Get all product stocks for this month/year
    stocks = Stock.query.filter_by(month=month, year=year, user_id=current_user.id).all()
    
    # If no records for this month, show products with zeroed data (or carry over)
    if not stocks:
        products = Product.query.filter_by(user_id=current_user.id).all()
        stocks = []
        for p in products:
            # Try to find previous month's closing
            prev = Stock.query.filter(Stock.product_id == p.id, Stock.user_id == current_user.id).order_by(Stock.year.desc(), Stock.month.desc()).first()
            opening = prev.closing_stock if prev else 0
            stocks.append({
                'product_name': p.product_name,
                'pack': p.pack,
                'opening_stock': opening,
                'received_stock': 0,
                'sale_return_qty': 0,
                'replace_others_in': 0,
                'total_quantity': opening,
                'sales': 0,
                'pr_quantity': 0,
                'replace_others_out': 0,
                'closing_stock': opening
            })
            
    months = [
        (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
        (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
        (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')
    ]
    
    return render_template('stock_statement.html', 
                           stocks=stocks, 
                           selected_month=month, 
                           selected_year=year,
                           months=months,
                           years=range(2024, 2030))

@reports_bp.route('/reports')
@login_required
def report_center():
    return render_template('report_center.html')

@reports_bp.route('/reports/export-products')
@login_required
def export_products():
    products = Product.query.filter_by(user_id=current_user.id).all()
    data = []
    for p in products:
        # Calculate stock
        from models import StockReceipt
        receipts = StockReceipt.query.filter_by(product_id=p.id, user_id=current_user.id).all()
        total_stock = sum(r.remaining_quantity for r in receipts)
        data.append({
            'Product Code': p.product_code,
            'Product Name': p.product_name,
            'Pack': p.pack,
            'List Price': p.list_price,
            'PTS Price': p.pts_price,
            'Current Stock': total_stock,
            'Inventory Value': total_stock * (p.pts_price or 0)
        })
    
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Product Master')
    output.seek(0)
    
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True, download_name=f'Product_Master_{datetime.now().strftime("%Y%m%d")}.xlsx')

@reports_bp.route('/reports/export-inventory')
@login_required
def export_inventory():
    from flask import current_app
    from models import StockReceipt, Product
    try:
        # Explicit join and filtered query for better performance and safety
        records = db.session.query(StockReceipt).join(Product).filter(
            StockReceipt.user_id == current_user.id,
            StockReceipt.remaining_quantity > 0
        ).all()
        
        data = []
        for r in records:
            # Safe attribute access to prevent AttributeError
            p_name = r.product.product_name if r.product else "Unknown"
            p_pts = float(r.product.pts_price or 0) if r.product else 0
            
            data.append({
                'Product': p_name,
                'Batch No': r.batch_no,
                'Expiry': r.expiry_date.strftime('%Y-%m-%d') if r.expiry_date else 'N/A',
                'SOH (Units)': r.remaining_quantity,
                'PTS Rate': p_pts,
                'Inventory Value': float(r.remaining_quantity * p_pts)
            })
        
        if not data:
            flash("No inventory data found to export.", "warning")
            return redirect(url_for('reports.report_center'))

        df = pd.DataFrame(data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Live Inventory')
        output.seek(0)
        
        return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                         as_attachment=True, download_name=f'Live_Inventory_{datetime.now().strftime("%Y%m%d")}.xlsx')
    except Exception as e:
        current_app.logger.error(f"Inventory Export Error: {str(e)}")
        flash("Export failed. Please check server logs or contact support.", "danger")
        return redirect(url_for('reports.report_center'))

@reports_bp.route('/reports/customer-sales')
@login_required
def customer_sales():
    sales = Sale.query.filter_by(user_id=current_user.id).order_by(Sale.customer_name, Sale.sale_date.desc()).all()
    customer_data = {}
    for s in sales:
        if s.customer_name not in customer_data:
            customer_data[s.customer_name] = {'sales': [], 'total_value': 0}
        customer_data[s.customer_name]['sales'].append(s)
        customer_data[s.customer_name]['total_value'] += s.value
    return render_template('customer_sales.html', customer_data=customer_data)

@reports_bp.route('/reports/monthly-sales')
@login_required
def monthly_sales():
    month = int(request.args.get('month', datetime.now().month))
    year = int(request.args.get('year', datetime.now().year))
    
    sales = Sale.query.filter(
        db.extract('month', Sale.sale_date) == month,
        db.extract('year', Sale.sale_date) == year,
        Sale.user_id == current_user.id
    ).all()
    
    total_value = sum(s.value for s in sales)
    total_qty = sum(s.quantity for s in sales)
    
    months = [(i, datetime(2000, i, 1).strftime('%B')) for i in range(1, 13)]
    return render_template('monthly_sales.html', 
                           sales=sales, 
                           total_value=total_value, 
                           total_qty=total_qty,
                           selected_month=month,
                           selected_year=year,
                           months=months)
