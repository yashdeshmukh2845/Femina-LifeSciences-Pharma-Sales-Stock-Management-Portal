import pandas as pd
import io
from datetime import datetime
from models import Sale, Product, Stock, db

def process_sales_excel(file_path, user_id):
    try:
        df = pd.read_excel(file_path)
        # Required headers for complex stock sheet format
        # Product Description, Opening Stock, Receive, Sale Quantity, Date, Invoice Number, Customer Name...
        
        for _, row in df.iterrows():
            prod_name = str(row['Product Description'])
            # Find or create product in master
            product = Product.query.filter_by(product_name=prod_name, user_id=user_id).first()
            if not product:
                product = Product(
                    product_code=str(row.get('Product Code', 'NA')),
                    product_name=prod_name,
                    pack=str(row.get('Pack', 'NA')),
                    user_id=user_id
                )
                db.session.add(product)
                db.session.commit()

            qty = int(row.get('Sale Quantity', 0))
            date_val = row.get('Date', datetime.utcnow())
            if isinstance(date_val, str):
                date_val = datetime.strptime(date_val, '%Y-%m-%d')
            
            new_sale = Sale(
                customer_name=str(row.get('Customer Name', 'Bulk Import')),
                product_id=product.id,
                invoice_no=str(row.get('Invoice Number', f"BULK{datetime.now().strftime('%H%M%S')}")),
                sale_date=date_val.date(),
                batch_no=str(row.get('Batch Number', 'NA')),
                quantity=qty,
                rate=float(row.get('Rate', 0)),
                value=float(row.get('Value', qty * float(row.get('Rate', 0)))),
                user_id=user_id
            )
            db.session.add(new_sale)
            
            # Update Stock for the month
            month, year = date_val.month, date_val.year
            stock_item = Stock.query.filter_by(product_id=product.id, month=month, year=year, user_id=user_id).first()
            if not stock_item:
                prev = Stock.query.filter_by(product_id=product.id, user_id=user_id).order_by(Stock.year.desc(), Stock.month.desc()).first()
                opening = int(row.get('Opening Stock', prev.closing_stock if prev else 0))
                stock_item = Stock(
                    product_id=product.id,
                    month=month, year=year, opening_stock=opening, user_id=user_id
                )
                db.session.add(stock_item)
            
            stock_item.received_stock += int(row.get('Receive', 0))
            stock_item.sales += qty
            stock_item.total_quantity = stock_item.opening_stock + stock_item.received_stock + stock_item.sale_return_qty + stock_item.replace_others_in
            stock_item.closing_stock = stock_item.total_quantity - stock_item.sales - stock_item.pr_quantity - stock_item.replace_others_out
            
        db.session.commit()
        return True, "Data imported successfully!"
    except Exception as e:
        db.session.rollback()
        return False, str(e)

def export_sales_to_excel(sales_query):
    data = []
    for sale in sales_query:
        data.append({
            'Product Name': sale.product_ref.product_name if sale.product_ref else 'NA',
            'Pack': sale.product_ref.pack if sale.product_ref else 'NA',
            'Product Code': sale.product_ref.product_code if sale.product_ref else 'NA',
            'Invoice No': sale.invoice_no,
            'Date': sale.sale_date.strftime('%Y-%m-%d'),
            'Batch No': sale.batch_no,
            'Quantity': sale.quantity,
            'Free Quantity': sale.free_quantity,
            'Rate': float(sale.rate),
            'Value': float(sale.value),
            'Customer Name': sale.customer_name
        })
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sales Report')
    output.seek(0)
    return output
