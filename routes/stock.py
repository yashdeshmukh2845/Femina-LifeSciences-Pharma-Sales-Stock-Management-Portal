from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import Stock, Product, StockReceipt, db
from datetime import datetime

stock_bp = Blueprint('stock', __name__)

@stock_bp.route('/stock')
@login_required
def stock_report():
    stocks = Stock.query.filter_by(user_id=current_user.id).all()
    return render_template('stock_report.html', stocks=stocks)

@stock_bp.route('/stock/entry', methods=['GET', 'POST'])
@login_required
def receive_stock():
    products = Product.query.filter_by(user_id=current_user.id).all()
    
    if request.method == 'POST':
        product_id = int(request.form.get('product_id'))
        product = Product.query.get(product_id)
        batch_no = request.form.get('batch_no')
        quantity = int(request.form.get('quantity') or 0)
        date_str = request.form.get('date')
        received_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else datetime.utcnow().date()
        
        expiry_str = request.form.get('expiry_date')
        expiry_date = datetime.strptime(expiry_str, '%Y-%m-%d').date() if expiry_str else None
        purchase_price = float(request.form.get('purchase_price') or 0)
        
        # 1. Record the receipt
        receipt = StockReceipt(
            product_id=product_id,
            batch_no=batch_no,
            quantity=quantity,
            remaining_quantity=quantity,  # Track available stock per batch
            expiry_date=expiry_date,
            purchase_price=purchase_price,
            received_date=received_date,
            user_id=current_user.id
        )
        db.session.add(receipt)
        
        # 2. Update monthly stock tracking
        month, year = received_date.month, received_date.year
        stock_item = Stock.query.filter_by(product_id=product_id, month=month, year=year, user_id=current_user.id).first()
        
        if not stock_item:
            # Carry over from previous month
            prev_stock = Stock.query.filter_by(product_id=product_id, user_id=current_user.id).order_by(Stock.year.desc(), Stock.month.desc()).first()
            opening = prev_stock.closing_stock if prev_stock else 0
            
            stock_item = Stock(
                product_id=product_id,
                month=month,
                year=year,
                opening_stock=opening,
                user_id=current_user.id,
                received_stock=0,
                sale_return_qty=0,
                replace_others_in=0,
                sales=0,
                pr_quantity=0,
                replace_others_out=0
            )
            db.session.add(stock_item)
            db.session.flush()

        stock_item.received_stock += quantity
        # Total Quantity = Opening + Receive + Sale Return + Replace
        stock_item.total_quantity = stock_item.opening_stock + stock_item.received_stock + stock_item.sale_return_qty + stock_item.replace_others_in
        # Closing Stock = Total Quantity - Sales - P/R Quantity - Others Out
        stock_item.closing_stock = stock_item.total_quantity - stock_item.sales - stock_item.pr_quantity - stock_item.replace_others_out
        stock_item.last_movement = datetime.utcnow()
        
        db.session.commit()
        flash(f'Successfully received {quantity} units of {product.product_name}!')
        return redirect(url_for('stock.stock_report'))
        
    return render_template('receive_stock.html', products=products, today=datetime.now().strftime('%Y-%m-%d'))
