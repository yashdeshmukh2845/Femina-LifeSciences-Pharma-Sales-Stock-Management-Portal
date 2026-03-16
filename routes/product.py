from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Product

product_bp = Blueprint('product', __name__)

@product_bp.route('/products')
@login_required
def list_products():
    products = Product.query.filter_by(user_id=current_user.id).all()
    total_inventory_value = 0
    
    for product in products:
        # Calculate total stock across all active batches (remaining_quantity > 0)
        from models import StockReceipt
        receipts = StockReceipt.query.filter_by(product_id=product.id).all()
        product.total_stock = sum(r.remaining_quantity for r in receipts)
        product.stock_value = product.total_stock * (product.pts_price or 0)
        total_inventory_value += product.stock_value
        
    return render_template('product_list.html', products=products, total_inventory_value=total_inventory_value)

@product_bp.route('/product/add', methods=['GET', 'POST'])
@login_required
def add_product():
    if request.method == 'POST':
        code = request.form.get('product_code')
        name = request.form.get('product_name')
        pack = request.form.get('pack_size')
        list_price = request.form.get('list_price')
        pts_price = request.form.get('pts_price')
        
        # Pre-check for duplicate
        existing_product = Product.query.filter_by(product_code=code).first()
        if existing_product:
            flash("Product code already exists. Please use a different code.", "danger")
            return redirect(url_for('product.add_product'))
            
        new_product = Product(
            product_code=code,
            product_name=name,
            pack=pack,
            list_price=list_price if list_price else None,
            pts_price=pts_price if pts_price else None,
            user_id=current_user.id
        )
        
        from sqlalchemy.exc import IntegrityError
        try:
            db.session.add(new_product)
            db.session.commit()
            flash('Product added to Master List!', 'success')
            return redirect(url_for('product.list_products'))
        except IntegrityError:
            db.session.rollback()
            flash('Product code already exists. Database constraint violated.', 'danger')
            return redirect(url_for('product.add_product'))
        except Exception as e:
            db.session.rollback()
            flash('An unexpected error occurred. Please try again.', 'danger')
            return redirect(url_for('product.add_product'))
    
    return render_template('add_product.html')

@product_bp.route('/product/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_product(id):
    product = Product.query.get_or_404(id)
    if product.user_id != current_user.id:
        flash('Access denied!')
        return redirect(url_for('product.list_products'))
        
    if request.method == 'POST':
        code = request.form.get('product_code')
        name = request.form.get('product_name')
        pack = request.form.get('pack_size')
        
        # Pre-check for duplicate if code changed
        if code != product.product_code:
            existing = Product.query.filter_by(product_code=code).first()
            if existing:
                flash('Another product already uses this code.', 'danger')
                return render_template('edit_product.html', product=product)

        product.product_code = code
        product.product_name = name
        product.pack = pack
        product.list_price = request.form.get('list_price') if request.form.get('list_price') else None
        product.pts_price = request.form.get('pts_price') if request.form.get('pts_price') else None
        
        try:
            db.session.commit()
            flash('Product updated!', 'success')
            return redirect(url_for('product.list_products'))
        except Exception as e:
            db.session.rollback()
            flash('Error while updating product. Please try again.', 'danger')
            return render_template('edit_product.html', product=product)
        
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
    return redirect(url_for('product.list_products'))
