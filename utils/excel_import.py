import pandas as pd
from datetime import datetime
from models import db, Product, Stock, Sale

def process_standardized_import(file_path, user_id, month, year):
    try:
        # Template has 2 title rows, headers start at row 3 (0-indexed 2)
        df = pd.read_excel(file_path, skiprows=2)
        
        # Clean column names (strip whitespace)
        df.columns = [str(c).strip() for c in df.columns]
        
        # Handle duplicate "REPLACE + OTHERS" (Pandas likely named them "REPLACE + OTHERS" and "REPLACE + OTHERS.1")
        # Map:
        # REPLACE + OTHERS -> replace_others_in
        # REPLACE + OTHERS.1 -> replace_others_out
        
        expected_cols = [
            "PRODUCT DESCRIPTION",
            "OPENING STOCK",
            "RECEIVE",
            "SALE RETURN QUANTITY",
            "REPLACE + OTHERS",
            "SALE QUANTITY",
            "P/R QUANTITY"
        ]
        
        # Validation
        for col in expected_cols:
            if col not in df.columns:
                return False, f"Missing required column: {col}"
        
        imported_count = 0
        for _, row in df.iterrows():
            prod_name = str(row['PRODUCT DESCRIPTION']).strip()
            
            # Skip totals rows or empty rows
            if not prod_name or 'TOTAL' in prod_name.upper() or pd.isna(row['PRODUCT DESCRIPTION']):
                continue
                
            # 1. Product Lookup/Creation
            product = Product.query.filter_by(product_name=prod_name, user_id=user_id).first()
            if not product:
                product = Product(
                    product_name=prod_name,
                    user_id=user_id,
                    product_code="AUTO",
                    pack="NA"
                )
                db.session.add(product)
                db.session.flush() # Get ID
                
            # 2. Stock Management
            stock = Stock.query.filter_by(product_id=product.id, month=month, year=year, user_id=user_id).first()
            if not stock:
                stock = Stock(
                    product_id=product.id,
                    month=month,
                    year=year,
                    user_id=user_id,
                    opening_stock=float(row.get('OPENING STOCK', 0))
                )
                db.session.add(stock)
            
            # Map values
            stock.received_stock = float(row.get('RECEIVE', 0))
            stock.sale_return_qty = float(row.get('SALE RETURN QUANTITY', 0))
            stock.replace_others_in = float(row.get('REPLACE + OTHERS', 0))
            stock.sales = float(row.get('SALE QUANTITY', 0))
            stock.pr_quantity = float(row.get('P/R QUANTITY', 0))
            
            # Handle the second REPLACE + OTHERS if it exists
            if 'REPLACE + OTHERS.1' in df.columns:
                stock.replace_others_out = float(row.get('REPLACE + OTHERS.1', 0))
                
            # Recalculate Totals
            stock.total_quantity = stock.opening_stock + stock.received_stock + stock.sale_return_qty + stock.replace_others_in
            stock.closing_stock = stock.total_quantity - stock.sales - stock.pr_quantity - stock.replace_others_out
            
            # 3. Create a Sale record for history (summary daily record for the import)
            if stock.sales > 0:
                sale_record = Sale(
                    product_id=product.id,
                    user_id=user_id,
                    customer_name="Bulk Template Import",
                    invoice_no=f"IMP-{month}{year}-{product.id}",
                    sale_date=datetime(year, month, 1).date(),
                    quantity=int(stock.sales),
                    rate=0, # Unknown from template
                    value=0  # Unknown from template
                )
                db.session.add(sale_record)
            
            imported_count += 1
            
        db.session.commit()
        return True, f"Successfully imported {imported_count} products."
        
    except Exception as e:
        db.session.rollback()
        return False, f"Import Error: {str(e)}"
