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

@reports_bp.route('/reports/customer-sales')
@login_required
def customer_sales():
    # Group sales by customer
    sales = Sale.query.filter_by(user_id=current_user.id).order_by(Sale.customer_name, Sale.sale_date.desc()).all()
    
    customer_data = {}
    for s in sales:
        if s.customer_name not in customer_data:
            customer_data[s.customer_name] = {'sales': [], 'total_value': 0}
        customer_data[s.customer_name]['sales'].append(s)
        customer_data[s.customer_name]['total_value'] += s.value
        
    return render_template('customer_sales.html', customer_data=customer_data)
