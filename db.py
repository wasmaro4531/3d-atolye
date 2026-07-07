import os
import streamlit as st
import psycopg2
import psycopg2.extras


def get_connection():
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        try:
            db_url = st.secrets["DATABASE_URL"]
        except Exception:
            db_url = ""
    if not db_url:
        raise Exception("DATABASE_URL bulunamadı! Streamlit Cloud > Secrets kısmına ekleyin.")

    try:
        conn = psycopg2.connect(db_url, sslmode="require", connect_timeout=10)
    except Exception:
        conn = psycopg2.connect(
            host="db.otkwkdcwcwsmaaqmdawn.supabase.co",
            port=5432,
            dbname="postgres",
            user="postgres.otkwkdcwcwsmaaqmdawn",
            password="km65535284594",
            sslmode="require",
            connect_timeout=10,
        )
    conn.autocommit = False
    return conn


def dict_row(cursor, row):
    if row is None:
        return None
    return {desc[0]: row[i] for i, desc in enumerate(cursor.description)}


def dict_rows(cursor, rows):
    return [dict_row(cursor, r) for r in rows]


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            electricity_price_kwh REAL NOT NULL DEFAULT 4.50,
            printer_price REAL NOT NULL DEFAULT 15000.0,
            target_amortization_hours REAL NOT NULL DEFAULT 2000.0,
            printer_name TEXT NOT NULL DEFAULT 'Bambu Lab A1',
            power_watts REAL NOT NULL DEFAULT 150.0
        );

        CREATE TABLE IF NOT EXISTS filaments (
            id SERIAL PRIMARY KEY,
            brand TEXT NOT NULL,
            material_type TEXT NOT NULL,
            color TEXT NOT NULL,
            remaining_grams REAL NOT NULL DEFAULT 0,
            purchase_price REAL NOT NULL DEFAULT 0,
            spool_grams REAL NOT NULL DEFAULT 1000,
            spool_price REAL NOT NULL DEFAULT 0,
            purchase_date TEXT NOT NULL,
            opening_date TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (NOW() AT TIME ZONE 'Europe/Istanbul')::text
        );

        CREATE TABLE IF NOT EXISTS orders (
            id SERIAL PRIMARY KEY,
            product_name TEXT NOT NULL,
            print_duration_hours REAL NOT NULL,
            cost_breakdown TEXT NOT NULL,
            total_filament_cost REAL NOT NULL DEFAULT 0,
            total_expense_cost REAL NOT NULL DEFAULT 0,
            electricity_cost REAL NOT NULL DEFAULT 0,
            amortization_cost REAL NOT NULL DEFAULT 0,
            total_cost REAL NOT NULL,
            sale_price REAL NOT NULL,
            profit_margin_pct REAL NOT NULL,
            profit REAL NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            total_grams REAL NOT NULL DEFAULT 0,
            actual_sale_price REAL DEFAULT NULL,
            photo_path TEXT DEFAULT NULL,
            status TEXT NOT NULL DEFAULT 'Tamamlandı',
            created_at TEXT NOT NULL DEFAULT (NOW() AT TIME ZONE 'Europe/Istanbul')::text
        );

        CREATE TABLE IF NOT EXISTS order_filaments (
            id SERIAL PRIMARY KEY,
            order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
            filament_id INTEGER NOT NULL REFERENCES filaments(id) ON DELETE CASCADE,
            grams_used REAL NOT NULL,
            filament_cost REAL NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS expenses (
            id SERIAL PRIMARY KEY,
            order_id INTEGER REFERENCES orders(id) ON DELETE SET NULL,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL DEFAULT 'Diğer',
            created_at TEXT NOT NULL DEFAULT (NOW() AT TIME ZONE 'Europe/Istanbul')::text
        );

        CREATE TABLE IF NOT EXISTS gcode_analyses (
            id SERIAL PRIMARY KEY,
            filename TEXT NOT NULL,
            original_time_estimate TEXT,
            optimized_time_estimate TEXT,
            lines_optimized INTEGER NOT NULL DEFAULT 0,
            total_lines INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (NOW() AT TIME ZONE 'Europe/Istanbul')::text
        );

        INSERT INTO settings (id) VALUES (1) ON CONFLICT (id) DO NOTHING;
    """)
    conn.commit()
    cur.close()
    conn.close()


def get_settings() -> dict:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM settings WHERE id = 1")
    row = dict_row(cur, cur.fetchone())
    cur.close()
    conn.close()
    if row:
        return row
    return {
        "electricity_price_kwh": 4.50,
        "printer_price": 15000.0,
        "target_amortization_hours": 2000.0,
        "printer_name": "Bambu Lab A1",
        "power_watts": 150.0,
    }


def update_settings(electricity_price_kwh: float, printer_price: float, target_amortization_hours: float, printer_name: str, power_watts: float):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """UPDATE settings SET
           electricity_price_kwh = %s,
           printer_price = %s,
           target_amortization_hours = %s,
           printer_name = %s,
           power_watts = %s
           WHERE id = 1""",
        (electricity_price_kwh, printer_price, target_amortization_hours, printer_name, power_watts),
    )
    conn.commit()
    cur.close()
    conn.close()


def add_filament(brand: str, material_type: str, color: str, remaining_grams: float, purchase_price: float, spool_grams: float, spool_price: float, purchase_date: str, opening_date: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO filaments (brand, material_type, color, remaining_grams, purchase_price, spool_grams, spool_price, purchase_date, opening_date) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
        (brand, material_type, color, remaining_grams, purchase_price, spool_grams, spool_price, purchase_date, opening_date),
    )
    filament_id = cur.fetchone()[0]
    if purchase_price > 0:
        cur.execute(
            "INSERT INTO expenses (order_id, description, amount, category) VALUES (NULL, %s, %s, %s)",
            (f"{brand} {color} Filament Alışı ({remaining_grams:.0f}g)", purchase_price, "Filament Alış"),
        )
    conn.commit()
    cur.close()
    conn.close()
    return filament_id


def get_all_filaments() -> list[dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM filaments ORDER BY created_at DESC")
    rows = dict_rows(cur, cur.fetchall())
    cur.close()
    conn.close()
    return rows


def get_filament_by_id(filament_id: int) -> dict | None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM filaments WHERE id = %s", (filament_id,))
    row = dict_row(cur, cur.fetchone())
    cur.close()
    conn.close()
    return row


def update_filament(filament_id: int, **kwargs):
    conn = get_connection()
    cur = conn.cursor()
    allowed = {"brand", "material_type", "color", "remaining_grams", "purchase_price", "spool_grams", "spool_price", "purchase_date", "opening_date"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        cur.close()
        conn.close()
        return
    set_clause = ", ".join(f"{k} = %s" for k in fields)
    values = list(fields.values()) + [filament_id]
    cur.execute(f"UPDATE filaments SET {set_clause} WHERE id = %s", values)
    conn.commit()
    cur.close()
    conn.close()


def delete_filament(filament_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM filaments WHERE id = %s", (filament_id,))
    conn.commit()
    cur.close()
    conn.close()


def add_order(
    product_name: str,
    print_duration_hours: float,
    cost_breakdown: str,
    total_filament_cost: float,
    total_expense_cost: float,
    electricity_cost: float,
    amortization_cost: float,
    total_cost: float,
    sale_price: float,
    profit_margin_pct: float,
    profit: float,
    filament_items: list[dict],
    expense_items: list[dict],
    quantity: int = 1,
    total_grams: float = 0,
    photo_path: str | None = None,
):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO orders
           (product_name, print_duration_hours, cost_breakdown, total_filament_cost,
            total_expense_cost, electricity_cost, amortization_cost, total_cost,
            sale_price, profit_margin_pct, profit, quantity, total_grams, photo_path)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
        (product_name, print_duration_hours, cost_breakdown, total_filament_cost,
         total_expense_cost, electricity_cost, amortization_cost, total_cost,
         sale_price, profit_margin_pct, profit, quantity, total_grams, photo_path),
    )
    order_id = cur.fetchone()[0]

    for item in filament_items:
        cur.execute(
            "INSERT INTO order_filaments (order_id, filament_id, grams_used, filament_cost) VALUES (%s, %s, %s, %s)",
            (order_id, item["filament_id"], item["grams_used"], item["filament_cost"]),
        )
        cur.execute(
            "UPDATE filaments SET remaining_grams = GREATEST(remaining_grams - %s, 0) WHERE id = %s",
            (item["grams_used"], item["filament_id"]),
        )

    for item in expense_items:
        cur.execute(
            "INSERT INTO expenses (order_id, description, amount, category) VALUES (%s, %s, %s, %s)",
            (order_id, item["description"], item["amount"], item["category"]),
        )

    conn.commit()
    cur.close()
    conn.close()
    return order_id


def get_order_filaments(order_id: int) -> list[dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT of2.*, f.brand, f.material_type, f.color
        FROM order_filaments of2
        LEFT JOIN filaments f ON of2.filament_id = f.id
        WHERE of2.order_id = %s
    """, (order_id,))
    rows = dict_rows(cur, cur.fetchall())
    cur.close()
    conn.close()
    return rows


def get_all_orders() -> list[dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM orders ORDER BY created_at DESC")
    rows = dict_rows(cur, cur.fetchall())
    orders = []
    for order in rows:
        order["filaments"] = get_order_filaments(order["id"])
        order["expenses"] = get_order_expenses(order["id"])
        orders.append(order)
    cur.close()
    conn.close()
    return orders


def get_revenue_summary() -> dict:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            COUNT(*) as total_orders,
            COALESCE(SUM(sale_price), 0) as total_revenue,
            COALESCE(SUM(total_cost), 0) as total_cost,
            COALESCE(SUM(profit), 0) as total_profit,
            COALESCE(SUM(total_filament_cost), 0) as total_filament_cost,
            COALESCE(SUM(total_expense_cost), 0) as total_expense_cost,
            COALESCE(SUM(electricity_cost), 0) as total_electricity_cost,
            COALESCE(SUM(amortization_cost), 0) as total_amortization_cost
        FROM orders
        WHERE status = 'Satıldı'
    """)
    row = dict_row(cur, cur.fetchone())
    cur.close()
    conn.close()
    return row if row else {
        "total_orders": 0, "total_revenue": 0, "total_cost": 0, "total_profit": 0,
        "total_filament_cost": 0, "total_expense_cost": 0,
        "total_electricity_cost": 0, "total_amortization_cost": 0,
    }


def get_actual_sales_summary() -> dict:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            COUNT(*) as sold_count,
            COALESCE(SUM(actual_sale_price), 0) as actual_revenue,
            COALESCE(SUM(total_cost), 0) as sold_cost,
            COALESCE(SUM(actual_sale_price - total_cost), 0) as actual_profit,
            COALESCE(SUM(actual_sale_price - sale_price), 0) as price_diff
        FROM orders
        WHERE status = 'Satıldı' AND actual_sale_price IS NOT NULL
    """)
    row = dict_row(cur, cur.fetchone())
    cur.close()
    conn.close()
    return row if row else {
        "sold_count": 0, "actual_revenue": 0, "sold_cost": 0,
        "actual_profit": 0, "price_diff": 0,
    }


def get_monthly_revenue() -> list[dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            TO_CHAR(created_at::timestamp, 'YYYY-MM') as month,
            COUNT(*) as order_count,
            SUM(sale_price) as revenue,
            SUM(total_cost) as cost,
            SUM(profit) as profit
        FROM orders
        WHERE status = 'Satıldı'
        GROUP BY TO_CHAR(created_at::timestamp, 'YYYY-MM')
        ORDER BY month DESC
        LIMIT 12
    """)
    rows = dict_rows(cur, cur.fetchall())
    cur.close()
    conn.close()
    return rows


def save_gcode_analysis(filename: str, original_time: str, optimized_time: str, lines_optimized: int, total_lines: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO gcode_analyses (filename, original_time_estimate, optimized_time_estimate, lines_optimized, total_lines) VALUES (%s, %s, %s, %s, %s)",
        (filename, original_time, optimized_time, lines_optimized, total_lines),
    )
    conn.commit()
    cur.close()
    conn.close()


def get_gcode_analyses() -> list[dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM gcode_analyses ORDER BY created_at DESC LIMIT 20")
    rows = dict_rows(cur, cur.fetchall())
    cur.close()
    conn.close()
    return rows


def add_expense(description: str, amount: float, category: str, order_id: int | None = None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO expenses (order_id, description, amount, category) VALUES (%s, %s, %s, %s)",
        (order_id, description, amount, category),
    )
    conn.commit()
    cur.close()
    conn.close()


def get_all_expenses() -> list[dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT e.*, o.product_name
        FROM expenses e
        LEFT JOIN orders o ON e.order_id = o.id
        ORDER BY e.created_at DESC
    """)
    rows = dict_rows(cur, cur.fetchall())
    cur.close()
    conn.close()
    return rows


def get_order_expenses(order_id: int) -> list[dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM expenses WHERE order_id = %s", (order_id,))
    rows = dict_rows(cur, cur.fetchall())
    cur.close()
    conn.close()
    return rows


def delete_expense(expense_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM expenses WHERE id = %s", (expense_id,))
    conn.commit()
    cur.close()
    conn.close()


def get_expense_summary() -> dict:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            COALESCE(SUM(amount), 0) as total_expenses,
            COUNT(*) as expense_count
        FROM expenses
    """)
    row = dict_row(cur, cur.fetchone())
    cur.close()
    conn.close()
    return row if row else {"total_expenses": 0, "expense_count": 0}


def get_expenses_by_category() -> list[dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT category, SUM(amount) as total, COUNT(*) as count
        FROM expenses
        GROUP BY category
        ORDER BY total DESC
    """)
    rows = dict_rows(cur, cur.fetchall())
    cur.close()
    conn.close()
    return rows


def get_order_by_id(order_id: int) -> dict | None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM orders WHERE id = %s", (order_id,))
    row = dict_row(cur, cur.fetchone())
    if row:
        row["filaments"] = get_order_filaments(row["id"])
        row["expenses"] = get_order_expenses(row["id"])
    cur.close()
    conn.close()
    return row


def update_order_status(order_id: int, status: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE orders SET status = %s WHERE id = %s", (status, order_id))
    conn.commit()
    cur.close()
    conn.close()


def delete_order(order_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM order_filaments WHERE order_id = %s", (order_id,))
    cur.execute("DELETE FROM expenses WHERE order_id = %s", (order_id,))
    cur.execute("DELETE FROM orders WHERE id = %s", (order_id,))
    conn.commit()
    cur.close()
    conn.close()


def mark_defective_print(order_id: int, elapsed_hours: float) -> dict:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM orders WHERE id = %s", (order_id,))
    order = dict_row(cur, cur.fetchone())
    if not order:
        cur.close()
        conn.close()
        return {"error": "Sipariş bulunamadı"}

    total_hours = order["print_duration_hours"]
    total_grams = order["total_grams"]

    if total_hours <= 0:
        cur.close()
        conn.close()
        return {"error": "Baskı süresi geçersiz"}

    ratio = min(elapsed_hours / total_hours, 1.0)
    consumed_grams = round(total_grams * ratio, 2)

    cur.execute("SELECT * FROM order_filaments WHERE order_id = %s", (order_id,))
    filaments = dict_rows(cur, cur.fetchall())

    for f in filaments:
        f_ratio = f["grams_used"] / total_grams if total_grams > 0 else 0
        fil_consumed = round(consumed_grams * f_ratio, 2)
        cur.execute(
            "UPDATE filaments SET remaining_grams = GREATEST(remaining_grams - %s, 0) WHERE id = %s",
            (fil_consumed, f["filament_id"]),
        )

    cur.execute("UPDATE orders SET status = 'Hatalı Baskı' WHERE id = %s", (order_id,))
    conn.commit()
    cur.close()
    conn.close()

    return {"consumed_grams": consumed_grams, "ratio": ratio, "elapsed_hours": elapsed_hours}


def mark_as_sold(order_id: int, actual_sale_price: float):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE orders SET status = 'Satıldı', actual_sale_price = %s WHERE id = %s",
        (actual_sale_price, order_id),
    )
    conn.commit()
    cur.close()
    conn.close()


def revert_order_status(order_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE orders SET status = 'Tamamlandı', actual_sale_price = NULL WHERE id = %s",
        (order_id,),
    )
    conn.commit()
    cur.close()
    conn.close()


def reset_database():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM order_filaments")
    cur.execute("DELETE FROM expenses")
    cur.execute("DELETE FROM orders")
    cur.execute("DELETE FROM filaments")
    cur.execute("DELETE FROM gcode_analyses")
    cur.execute("DELETE FROM settings")
    cur.execute("INSERT INTO settings (id) VALUES (1)")
    conn.commit()
    cur.close()
    conn.close()


init_db()
