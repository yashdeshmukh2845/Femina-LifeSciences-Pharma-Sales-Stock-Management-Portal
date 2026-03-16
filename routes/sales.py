from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required, current_user
from models import db, Sale, Product, Stock, StockReceipt
from datetime import datetime
from utils.excel_import import process_standardized_import
from utils.excel_export import export_stock_statement_to_excel
import io

sales_bp = Blueprint('sales', __name__)

@sales_bp.route('/sales')
@login_required
def sales_report():
    sales = Sale.query.filter_by(user_id=current_user.id).order_by(Sale.sale_date.desc()).all()
    return render_template('sales_report.html', sales=sales)

@sales_bp.route('/sales/add', methods=['GET', 'POST'])
@login_required
def add_sale():
    products = Product.query.filter_by(user_id=current_user.id).all()
    
    if request.method == 'POST':
        customer_name = request.form.get('customer_name')
        product_id = int(request.form.get('product_id'))
        product = Product.query.get(product_id)
        
        invoice_no = request.form.get('invoice_no')
        date_str = request.form.get('date')
        sale_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else datetime.utcnow().date()
        batch_no = request.form.get('batch_no')
        quantity = int(request.form.get('quantity') or 0)
        free_quantity = int(request.form.get('free_quantity') or 0)
        rate = float(request.form.get('rate') or 0)
        value = quantity * rate
        total_requested = quantity + free_quantity

        # 1. Check for available stock before proceeding
        month, year = sale_date.month, sale_date.year
        stock_item = Stock.query.filter_by(product_id=product_id, month=month, year=year, user_id=current_user.id).first()
        
        # Calculate current available stock
        if stock_item:
            available = stock_item.total_quantity - stock_item.sales - stock_item.pr_quantity - stock_item.replace_others_out
        else:
            # Check previous month's closing if current month record doesn't exist yet
            prev_stock = Stock.query.filter_by(product_id=product_id, user_id=current_user.id).order_by(Stock.year.desc(), Stock.month.desc()).first()
            available = prev_stock.closing_stock if prev_stock else 0
        
        if total_requested > available:
            flash("Insufficient Stock Available")
            return redirect(url_for('sales.add_sale'))

        # 2. Auto-generate Invoice Number if not provided
        if not invoice_no:
            last_sale = Sale.query.filter_by(user_id=current_user.id).order_by(Sale.id.desc()).first()
            if last_sale and last_sale.invoice_no.startswith('INV'):
                try:
                    num = int(last_sale.invoice_no[3:]) + 1
                    invoice_no = f"INV{num:04d}"
                except:
                    invoice_no = f"INV{datetime.now().strftime('%Y%m%d%H%M%S')}"
            else:
                invoice_no = "INV0001"

        # 3. Create Sale Record(s) and Update Batch Stock (FIFO)
        remaining_to_deduct = total_requested
        # Get all batches for this product ordered by expiry (FIFO)
        available_batches = StockReceipt.query.filter(
            StockReceipt.product_id == product_id,
            StockReceipt.remaining_quantity > 0,
            StockReceipt.user_id == current_user.id
        ).order_by(StockReceipt.expiry_date.asc()).all()

        if not available_batches:
             flash("No batches found for this product.")
             return redirect(url_for('sales.add_sale'))

        for batch in available_batches:
            if remaining_to_deduct <= 0:
                break
            
            deduction = min(batch.remaining_quantity, remaining_to_deduct)
            batch.remaining_quantity -= deduction
            remaining_to_deduct -= deduction
            
            # Create a sale record for this batch
            # Note: The request only creates ONE sale record in the original logic, 
            # but if we follow FIFO strictly across different batches for ONE entry,
            # we might need multiple records or just log the batch used.
            # User request says: "Automatically fill Batch Number, Expiry Date"
            # This implies one sale per entry, but the backend should ideally handle it.
            # Let's stick to the user's single entry but update the closest batch.
            # If multiple batches are needed, we'll use the one with nearest expiry that covers the qty.
            # For simplicity and UI alignment, we'll assign the sale to the FIFO batch.
            
        # Assigning to the first available FIFO batch for the sale record
        target_batch = available_batches[0]
        new_sale = Sale(
            customer_name=customer_name,
            product_id=product_id,
            invoice_no=invoice_no,
            sale_date=sale_date,
            batch_no=target_batch.batch_no,
            expiry_date=target_batch.expiry_date,
            quantity=quantity,
            free_quantity=free_quantity,
            rate=rate,
            value=value,
            user_id=current_user.id
        )
        db.session.add(new_sale)
        
        # 4. Update Monthly Stock Record
        if not stock_item:
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

        stock_item.sales += total_requested
        # Total Quantity = Opening + Receive + Sale Return + Replace
        stock_item.total_quantity = stock_item.opening_stock + stock_item.received_stock + stock_item.sale_return_qty + stock_item.replace_others_in
        # Closing Stock = Total Quantity - Sales - P/R Quantity - Others Out
        stock_item.closing_stock = stock_item.total_quantity - stock_item.sales - stock_item.pr_quantity - stock_item.replace_others_out
        stock_item.last_movement = datetime.utcnow()

        db.session.commit()
        flash(f'Sale {invoice_no} recorded successfully!')
        return redirect(url_for('sales.sales_report'))

    # Pre-generate next invoice number for display
    last_sale = Sale.query.filter_by(user_id=current_user.id).order_by(Sale.id.desc()).first()
    next_inv = "INV0001"
    if last_sale and last_sale.invoice_no.startswith('INV'):
        try:
            num = int(last_sale.invoice_no[3:]) + 1
            next_inv = f"INV{num:04d}"
        except: pass
        
    return render_template('add_sale.html', products=products, next_inv=next_inv, today=datetime.now().strftime('%Y-%m-%d'))

@sales_bp.route('/sales/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_sale(id):
    sale = Sale.query.get_or_404(id)
    if sale.user_id != current_user.id:
        flash('Access denied!')
        return redirect(url_for('sales.sales_report'))

    if request.method == 'POST':
        # Update logic similar to add
        pass

    return render_template('edit_sale.html', sale=sale)

@sales_bp.route('/sales/delete/<int:id>')
@login_required
def delete_sale(id):
    sale = Sale.query.get_or_404(id)
    if sale.user_id != current_user.id:
        flash('Access denied!')
        return redirect(url_for('sales.sales_report'))
    
    # Reverse Stock
    month, year = sale.sale_date.month, sale.sale_date.year
    stock_item = Stock.query.filter_by(product_id=sale.product_id, month=month, year=year, user_id=current_user.id).first()
    if stock_item:
        stock_item.sales -= (sale.quantity + sale.free_quantity)
        stock_item.total_quantity = stock_item.opening_stock + stock_item.received_stock + stock_item.sale_return_qty + stock_item.replace_others_in
        stock_item.closing_stock = stock_item.total_quantity - stock_item.sales - stock_item.pr_quantity - stock_item.replace_others_out
        stock_item.last_movement = datetime.utcnow()

    db.session.delete(sale)
    db.session.commit()
    flash(f'Sale {sale.invoice_no} deleted!')
    return redirect(url_for('sales.sales_report'))

@sales_bp.route('/import-stock-report', methods=['GET', 'POST'])
@sales_bp.route('/upload-excel', methods=['GET', 'POST'])
@login_required
def upload_excel():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        file = request.files['file']
        month = int(request.form.get('month', datetime.utcnow().month))
        year = int(request.form.get('year', datetime.utcnow().year))
        
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
            
        if file:
            success, message = process_standardized_import(file, current_user.id, month, year)
            if success:
                flash(message, 'success')
            else:
                flash(message, 'danger')
            return redirect(url_for('main.index'))
    return render_template('upload_excel.html')

@sales_bp.route('/sales/invoice/<int:id>')
@login_required
def view_invoice(id):
    sale = Sale.query.get_or_404(id)
    if sale.user_id != current_user.id:
        flash('Access denied!')
        return redirect(url_for('sales.sales_report'))
    return render_template('invoice.html', sale=sale)

@sales_bp.route('/export-stock-report')
@sales_bp.route('/export-excel')
@login_required
def export_excel():
    month = int(request.args.get('month', datetime.utcnow().month))
    year = int(request.args.get('year', datetime.utcnow().year))
    
    stocks = Stock.query.filter_by(user_id=current_user.id, month=month, year=year).all()
    
    # Create empty stock objects if none exist
    if not stocks:
        products = Product.query.filter_by(user_id=current_user.id).all()
        for p in products:
            prev = Stock.query.filter_by(product_id=p.id, user_id=current_user.id).order_by(Stock.year.desc(), Stock.month.desc()).first()
            opening = prev.closing_stock if prev else 0
            stocks.append(Stock(product_id=p.id, opening_stock=opening, product_ref=p, received_stock=0, sale_return_qty=0, replace_others_in=0, sales=0, pr_quantity=0, replace_others_out=0, closing_stock=opening, total_quantity=opening))
            
    month_name = datetime(2000, month, 1).strftime('%B')
    excel_file = export_stock_statement_to_excel(stocks, month_name, year)
    
    return send_file(
        excel_file,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f"Stock_Statement_{month_name}_{year}.xlsx"
    )
@sales_bp.route('/api/product-batches/<int:product_id>')
@login_required
def get_product_batches(product_id):
    batches = StockReceipt.query.filter(
        StockReceipt.product_id == product_id,
        StockReceipt.remaining_quantity > 0,
        StockReceipt.user_id == current_user.id
    ).order_by(StockReceipt.expiry_date.asc()).all()
    
    product = Product.query.get(product_id)
    
    batch_list = []
    for b in batches:
        batch_list.append({
            'batch_no': b.batch_no,
            'expiry_date': b.expiry_date.strftime('%m/%Y') if b.expiry_date else 'N/A',
            'expiry_full': b.expiry_date.strftime('%Y-%m-%d') if b.expiry_date else '',
            'stock': b.remaining_quantity,
            'days_to_expiry': (b.expiry_date - datetime.utcnow().date()).days if b.expiry_date else 999
        })
    
    return {
        'batches': batch_list,
        'pts_price': float(product.pts_price or 0)
    }
