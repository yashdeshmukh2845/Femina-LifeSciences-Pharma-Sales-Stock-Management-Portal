from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Product

product_bp = Blueprint('product', __name__)

@product_bp.route('/products')
@login_required
def list_products():
    products = Product.query.filter_by(user_id=current_user.id).all()
    return render_template('product_list.html', products=products)

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
    return redirect(url_for('product.list_products'))
