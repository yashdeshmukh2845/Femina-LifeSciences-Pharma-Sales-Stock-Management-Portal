from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required, current_user
from models import db, Sale, Product, Stock, StockReceipt
import pandas as pd
import io
from datetime import datetime, date

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/export-stock-report')
@login_required
def export_stock_report():
    month = int(request.args.get('month', datetime.now().month))
    year = int(request.args.get('year', datetime.now().year))
    
    stocks = Stock.query.filter_by(month=month, year=year, user_id=current_user.id).all()
    
    # If no records for this month, carry over or create empty
    if not stocks:
        products = Product.query.filter_by(user_id=current_user.id).all()
        stocks = []
        for p in products:
            prev = Stock.query.filter(Stock.product_id == p.id, Stock.user_id == current_user.id).order_by(Stock.year.desc(), Stock.month.desc()).first()
            opening = prev.closing_stock if prev else 0
            stocks.append(Stock(
                product_id=p.id, month=month, year=year, user_id=current_user.id,
                opening_stock=opening, received_stock=0, sale_return_qty=0, 
                replace_others_in=0, total_quantity=opening, sales=0, 
                pr_quantity=0, replace_others_out=0, closing_stock=opening,
                product_ref=p
            ))
            
    month_name = datetime(2000, month, 1).strftime('%B')
    excel_file = export_stock_statement_to_excel(stocks, month_name, year)
    
    return send_file(
        excel_file,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f"Stock_Statement_{month_name}_{year}.xlsx"
    )

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

@reports_bp.route('/export-customer-sales')
@login_required
def export_customer_sales():
    sales = Sale.query.filter_by(user_id=current_user.id).all()
    
    data = []
    for s in sales:
        data.append({
            'Customer': s.customer_name,
            'Invoice #': s.invoice_no,
            'Product': s.product_ref.product_name,
            'Pack': s.product_ref.pack,
            'Date': s.sale_date.strftime('%d-%m-%Y'),
            'Batch': s.batch_no,
            'Quantity': s.quantity,
            'Rate': s.rate,
            'Value': s.value
        })
    
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Customer Sales')
    
    output.seek(0)
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'Customer_Sales_{datetime.now().strftime("%Y%m%d")}.xlsx'
    )

@reports_bp.route('/monthly-analysis')
@login_required
def monthly_analysis():
    month = int(request.args.get('month', date.today().month))
    year = int(request.args.get('year', date.today().year))
    
    # 1. Product-wise sales for the month
    product_sales = db.session.query(
        Product.product_name,
        Product.pack,
        db.func.sum(Sale.quantity).label('total_qty'),
        db.func.sum(Sale.value).label('total_value')
    ).join(Sale).filter(
        Sale.user_id == current_user.id,
        db.func.extract('month', Sale.sale_date) == month,
        db.func.extract('year', Sale.sale_date) == year
    ).group_by(Product.product_name, Product.pack).all()
    
    total_month_value = sum(p.total_value for p in product_sales)
    
    # 2. Daily trend for the month
    daily_sales = db.session.query(
        db.func.extract('day', Sale.sale_date).label('day'),
        db.func.sum(Sale.value).label('value')
    ).filter(
        Sale.user_id == current_user.id,
        db.func.extract('month', Sale.sale_date) == month,
        db.func.extract('year', Sale.sale_date) == year
    ).group_by('day').order_by('day').all()
    
    chart_labels = [int(d.day) for d in daily_sales]
    chart_values = [float(d.value) for d in daily_sales]
    
    return render_template('monthly_analysis.html', 
                           product_sales=product_sales,
                           total_value=total_month_value,
                           chart_labels=chart_labels,
                           chart_values=chart_values,
                           month=month,
                           year=year)
