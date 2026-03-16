import pandas as pd
from datetime import datetime
from models import db, Product, Stock, Sale


def safe_float(value):
    """Safely convert Excel values to float"""
    try:
        if pd.isna(value):
            return 0
        return float(value)
    except:
        return 0


def process_standardized_import(file_path, user_id, month, year):

    try:

        # Excel template has title rows
        df = pd.read_excel(file_path, header=2)

        # Clean column names
        df.columns = df.columns.astype(str).str.strip().str.upper()

        # Remove completely empty rows
        df = df.dropna(how='all')

        # Expected columns
        expected_cols = [
            "PRODUCT DESCRIPTION",
            "OPENING STOCK",
            "RECEIVE",
            "SALE RETURN QUANTITY",
            "REPLACE + OTHERS",
            "SALE QUANTITY",
            "P/R QUANTITY"
        ]

        # Validate template structure
        for col in expected_cols:
            if col not in df.columns:
                return False, f"Missing required column: {col}"

        imported_count = 0

        for _, row in df.iterrows():

            prod_name = str(row.get("PRODUCT DESCRIPTION", "")).strip()

            # Skip totals or invalid rows
            if (
                not prod_name
                or prod_name.lower() == "nan"
                or "TOTAL" in prod_name.upper()
            ):
                continue

            # ---------------------------
            # Product Lookup / Creation
            # ---------------------------

            product = Product.query.filter_by(
                product_name=prod_name,
                user_id=user_id
            ).first()

            if not product:
                product = Product(
                    product_name=prod_name,
                    user_id=user_id,
                    product_code="AUTO",
                    pack="NA"
                )

                db.session.add(product)
                db.session.flush()

            # ---------------------------
            # Stock Record
            # ---------------------------

            stock = Stock.query.filter_by(
                product_id=product.id,
                month=month,
                year=year,
                user_id=user_id
            ).first()

            if not stock:
                stock = Stock(
                    product_id=product.id,
                    month=month,
                    year=year,
                    user_id=user_id,
                    opening_stock=safe_float(row.get("OPENING STOCK"))
                )

                db.session.add(stock)

            # ---------------------------
            # Map Excel values
            # ---------------------------

            stock.received_stock = safe_float(row.get("RECEIVE"))
            stock.sale_return_qty = safe_float(row.get("SALE RETURN QUANTITY"))
            stock.replace_others_in = safe_float(row.get("REPLACE + OTHERS"))
            stock.sales = safe_float(row.get("SALE QUANTITY"))
            stock.pr_quantity = safe_float(row.get("P/R QUANTITY"))

            # Handle duplicate column
            if "REPLACE + OTHERS.1" in df.columns:
                stock.replace_others_out = safe_float(row.get("REPLACE + OTHERS.1"))

            # ---------------------------
            # Calculate totals
            # ---------------------------

            stock.total_quantity = (
                stock.opening_stock
                + stock.received_stock
                + stock.sale_return_qty
                + stock.replace_others_in
            )

            stock.closing_stock = (
                stock.total_quantity
                - stock.sales
                - stock.pr_quantity
                - stock.replace_others_out
            )

            stock.last_movement = datetime.utcnow()

            # ---------------------------
            # Create Sale record
            # ---------------------------

            if stock.sales > 0:

                sale_record = Sale(
                    product_id=product.id,
                    user_id=user_id,
                    customer_name="Bulk Template Import",
                    invoice_no=f"IMP-{month}{year}-{product.id}",
                    sale_date=datetime(year, month, 1).date(),
                    quantity=int(stock.sales),
                    rate=0,
                    value=0
                )

                db.session.add(sale_record)

            imported_count += 1

        db.session.commit()

        return True, f"Successfully imported {imported_count} products."

    except Exception as e:

        db.session.rollback()

        return False, f"Import Error: {str(e)}"