from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Product, Stock
import pandas as pd
import io
from flask import send_file

product_bp = Blueprint('product', __name__)

@product_bp.route('/products')
@login_required
def list_products():
    products = Product.query.filter_by(user_id=current_user.id).all()
    
    # Calculate stock and value for each product
    product_data = []
    total_inventory_value = 0
    
    for p in products:
        # Get latest stock record
        latest_stock = Stock.query.filter_by(product_id=p.id, user_id=current_user.id).order_by(Stock.year.desc(), Stock.month.desc()).first()
        stock_qty = latest_stock.closing_stock if latest_stock else 0
        stock_value = stock_qty * float(p.pts_price or 0)
        
        product_data.append({
            'product': p,
            'stock': stock_qty,
            'value': stock_value
        })
        total_inventory_value += stock_value
        
    return render_template('product_list.html', products=product_data, total_value=total_inventory_value)

@product_bp.route('/product/add', methods=['GET', 'POST'])
@login_required
def add_product():
    if request.method == 'POST':
        code = request.form.get('product_code')
        name = request.form.get('product_name')
        pack = request.form.get('pack_size')
        
        new_product = Product(
            product_code=code,
            product_name=name,
            pack=pack,
            list_price=float(request.form.get('list_price') or 0),
            pts_price=float(request.form.get('pts_price') or 0),
            user_id=current_user.id
        )
        db.session.add(new_product)
        db.session.commit()
        flash('Product added to Master List!')
        return redirect(url_for('product.list_products'))
    
    return render_template('add_product.html')

@product_bp.route('/product/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_product(id):
    product = Product.query.get_or_404(id)
    if product.user_id != current_user.id:
        flash('Access denied!')
        return redirect(url_for('product.list_products'))
        
    if request.method == 'POST':
        product.product_code = request.form.get('product_code')
        product.product_name = request.form.get('product_name')
        product.pack = request.form.get('pack_size')
        product.list_price = float(request.form.get('list_price') or 0)
        product.pts_price = float(request.form.get('pts_price') or 0)
        db.session.commit()
        flash('Product updated!')
        return redirect(url_for('product.list_products'))
        
    return render_template('edit_product.html', product=product)

@product_bp.route('/product/delete/<int:id>')
@login_required
def delete_product(id):
    product = Product.query.get_or_404(id)
    if product.user_id != current_user.id:
        flash('Access denied!')
        return redirect(url_for('product.list_products'))
    
    db.session.delete(product)
    db.session.commit()
    flash('Product removed from Master List!')
@product_bp.route('/export-products')
@login_required
def export_products():
    products = Product.query.filter_by(user_id=current_user.id).all()
    
    data = []
    for p in products:
        latest_stock = Stock.query.filter_by(product_id=p.id, user_id=current_user.id).order_by(Stock.year.desc(), Stock.month.desc()).first()
        data.append({
            'Product Code': p.product_code,
            'Product Name': p.product_name,
            'Pack': p.pack,
            'List Price': p.list_price,
            'PTS': p.pts_price,
            'Current Stock': latest_stock.closing_stock if latest_stock else 0
        })
    
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Product Master')
    
    output.seek(0)
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'Product_Master_{datetime.now().strftime("%Y%m%d")}.xlsx'
    )
