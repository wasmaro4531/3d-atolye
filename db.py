import sqlite3
import os
from datetime import datetime

_dir = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(_dir, "atolye.db") if os.path.isdir(_dir) else os.path.join(os.getcwd(), "atolye.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            electricity_price_kwh REAL NOT NULL DEFAULT 4.50,
            printer_price REAL NOT NULL DEFAULT 15000.0,
            target_amortization_hours REAL NOT NULL DEFAULT 2000.0,
            printer_name TEXT NOT NULL DEFAULT 'Bambu Lab A1',
            power_watts REAL NOT NULL DEFAULT 150.0
        );

        CREATE TABLE IF NOT EXISTS filaments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand TEXT NOT NULL,
            material_type TEXT NOT NULL,
            color TEXT NOT NULL,
            remaining_grams REAL NOT NULL DEFAULT 0,
            purchase_price REAL NOT NULL DEFAULT 0,
            purchase_date TEXT NOT NULL,
            opening_date TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            status TEXT NOT NULL DEFAULT 'Tamamlandı',
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS order_filaments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            filament_id INTEGER NOT NULL,
            grams_used REAL NOT NULL,
            filament_cost REAL NOT NULL DEFAULT 0,
            FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
            FOREIGN KEY (filament_id) REFERENCES filaments(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL DEFAULT 'Diğer',
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS gcode_analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            original_time_estimate TEXT,
            optimized_time_estimate TEXT,
            lines_optimized INTEGER NOT NULL DEFAULT 0,
            total_lines INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        );

        INSERT OR IGNORE INTO settings (id) VALUES (1);
    """)

    try:
        cursor.execute("ALTER TABLE orders ADD COLUMN quantity INTEGER NOT NULL DEFAULT 1")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE orders ADD COLUMN total_grams REAL NOT NULL DEFAULT 0")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE filaments ADD COLUMN purchase_date TEXT NOT NULL DEFAULT ''")
    except Exception:
        pass

    conn.commit()
    conn.close()


def get_settings() -> dict:
    conn = get_connection()
    row = conn.execute("SELECT * FROM settings WHERE id = 1").fetchone()
    conn.close()
    if row:
        return dict(row)
    return {
        "electricity_price_kwh": 4.50,
        "printer_price": 15000.0,
        "target_amortization_hours": 2000.0,
        "printer_name": "Bambu Lab A1",
        "power_watts": 150.0,
    }


def update_settings(electricity_price_kwh: float, printer_price: float, target_amortization_hours: float, printer_name: str, power_watts: float):
    conn = get_connection()
    conn.execute(
        """UPDATE settings SET
           electricity_price_kwh = ?,
           printer_price = ?,
           target_amortization_hours = ?,
           printer_name = ?,
           power_watts = ?
           WHERE id = 1""",
        (electricity_price_kwh, printer_price, target_amortization_hours, printer_name, power_watts),
    )
    conn.commit()
    conn.close()


def add_filament(brand: str, material_type: str, color: str, remaining_grams: float, purchase_price: float, purchase_date: str, opening_date: str):
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO filaments (brand, material_type, color, remaining_grams, purchase_price, purchase_date, opening_date) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (brand, material_type, color, remaining_grams, purchase_price, purchase_date, opening_date),
    )
    filament_id = cursor.lastrowid
    if purchase_price > 0:
        conn.execute(
            "INSERT INTO expenses (order_id, description, amount, category) VALUES (NULL, ?, ?, ?)",
            (f"{brand} {color} Filament Alışı ({remaining_grams:.0f}g)", purchase_price, "Filament Alış"),
        )
    conn.commit()
    conn.close()
    return filament_id


def get_all_filaments() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM filaments ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_filament_by_id(filament_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM filaments WHERE id = ?", (filament_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_filament(filament_id: int, **kwargs):
    conn = get_connection()
    allowed = {"brand", "material_type", "color", "remaining_grams", "purchase_price", "purchase_date", "opening_date"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        conn.close()
        return
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [filament_id]
    conn.execute(f"UPDATE filaments SET {set_clause} WHERE id = ?", values)
    conn.commit()
    conn.close()


def delete_filament(filament_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM filaments WHERE id = ?", (filament_id,))
    conn.commit()
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
):
    conn = get_connection()
    cursor = conn.execute(
        """INSERT INTO orders
           (product_name, print_duration_hours, cost_breakdown, total_filament_cost,
            total_expense_cost, electricity_cost, amortization_cost, total_cost,
            sale_price, profit_margin_pct, profit, quantity, total_grams)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (product_name, print_duration_hours, cost_breakdown, total_filament_cost,
         total_expense_cost, electricity_cost, amortization_cost, total_cost,
         sale_price, profit_margin_pct, profit, quantity, total_grams),
    )
    order_id = cursor.lastrowid

    for item in filament_items:
        conn.execute(
            "INSERT INTO order_filaments (order_id, filament_id, grams_used, filament_cost) VALUES (?, ?, ?, ?)",
            (order_id, item["filament_id"], item["grams_used"], item["filament_cost"]),
        )
        conn.execute(
            "UPDATE filaments SET remaining_grams = MAX(remaining_grams - ?, 0) WHERE id = ?",
            (item["grams_used"], item["filament_id"]),
        )

    for item in expense_items:
        conn.execute(
            "INSERT INTO expenses (order_id, description, amount, category) VALUES (?, ?, ?, ?)",
            (order_id, item["description"], item["amount"], item["category"]),
        )

    conn.commit()
    conn.close()
    return order_id


def get_order_filaments(order_id: int) -> list[dict]:
    conn = get_connection()
    rows = conn.execute("""
        SELECT of2.*, f.brand, f.material_type, f.color
        FROM order_filaments of2
        LEFT JOIN filaments f ON of2.filament_id = f.id
        WHERE of2.order_id = ?
    """, (order_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_orders() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM orders ORDER BY created_at DESC").fetchall()
    orders = []
    for row in rows:
        order = dict(row)
        order["filaments"] = get_order_filaments(order["id"])
        order["expenses"] = get_order_expenses(order["id"])
        orders.append(order)
    conn.close()
    return orders


def get_revenue_summary() -> dict:
    conn = get_connection()
    row = conn.execute("""
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
    """).fetchone()
    conn.close()
    return dict(row) if row else {
        "total_orders": 0, "total_revenue": 0, "total_cost": 0, "total_profit": 0,
        "total_filament_cost": 0, "total_expense_cost": 0,
        "total_electricity_cost": 0, "total_amortization_cost": 0,
    }


def get_monthly_revenue() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("""
        SELECT
            strftime('%Y-%m', created_at) as month,
            COUNT(*) as order_count,
            SUM(sale_price) as revenue,
            SUM(total_cost) as cost,
            SUM(profit) as profit
        FROM orders
        GROUP BY strftime('%Y-%m', created_at)
        ORDER BY month DESC
        LIMIT 12
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_gcode_analysis(filename: str, original_time: str, optimized_time: str, lines_optimized: int, total_lines: int):
    conn = get_connection()
    conn.execute(
        "INSERT INTO gcode_analyses (filename, original_time_estimate, optimized_time_estimate, lines_optimized, total_lines) VALUES (?, ?, ?, ?, ?)",
        (filename, original_time, optimized_time, lines_optimized, total_lines),
    )
    conn.commit()
    conn.close()


def get_gcode_analyses() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM gcode_analyses ORDER BY created_at DESC LIMIT 20").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_expense(description: str, amount: float, category: str, order_id: int | None = None):
    conn = get_connection()
    conn.execute(
        "INSERT INTO expenses (order_id, description, amount, category) VALUES (?, ?, ?, ?)",
        (order_id, description, amount, category),
    )
    conn.commit()
    conn.close()


def get_all_expenses() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("""
        SELECT e.*, o.product_name
        FROM expenses e
        LEFT JOIN orders o ON e.order_id = o.id
        ORDER BY e.created_at DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_order_expenses(order_id: int) -> list[dict]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM expenses WHERE order_id = ?", (order_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_expense(expense_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    conn.commit()
    conn.close()


def get_expense_summary() -> dict:
    conn = get_connection()
    row = conn.execute("""
        SELECT
            COALESCE(SUM(amount), 0) as total_expenses,
            COUNT(*) as expense_count
        FROM expenses
    """).fetchone()
    conn.close()
    return dict(row) if row else {"total_expenses": 0, "expense_count": 0}


def get_expenses_by_category() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("""
        SELECT category, SUM(amount) as total, COUNT(*) as count
        FROM expenses
        GROUP BY category
        ORDER BY total DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_order_by_id(order_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if row:
        order = dict(row)
        order["filaments"] = get_order_filaments(order["id"])
        order["expenses"] = get_order_expenses(order["id"])
        conn.close()
        return order
    conn.close()
    return None


def update_order_status(order_id: int, status: str):
    conn = get_connection()
    conn.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
    conn.commit()
    conn.close()


def delete_order(order_id: int):
    conn = get_connection()
    try:
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("DELETE FROM order_filaments WHERE order_id = ?", (order_id,))
        conn.execute("DELETE FROM expenses WHERE order_id = ?", (order_id,))
        conn.execute("DELETE FROM orders WHERE id = ?", (order_id,))
        conn.commit()
    finally:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.close()


def mark_defective_print(order_id: int, elapsed_hours: float) -> dict:
    conn = get_connection()
    order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if not order:
        conn.close()
        return {"error": "Sipariş bulunamadı"}

    order = dict(order)
    total_hours = order["print_duration_hours"]
    total_grams = order["total_grams"]

    if total_hours <= 0:
        conn.close()
        return {"error": "Baskı süresi geçersiz"}

    ratio = min(elapsed_hours / total_hours, 1.0)
    consumed_grams = round(total_grams * ratio, 2)

    filaments = conn.execute(
        "SELECT * FROM order_filaments WHERE order_id = ?", (order_id,)
    ).fetchall()

    for f in filaments:
        f_ratio = f["grams_used"] / total_grams if total_grams > 0 else 0
        fil_consumed = round(consumed_grams * f_ratio, 2)
        conn.execute(
            "UPDATE filaments SET remaining_grams = MAX(remaining_grams - ?, 0) WHERE id = ?",
            (fil_consumed, f["filament_id"]),
        )

    conn.execute(
        "UPDATE orders SET status = 'Hatalı Baskı' WHERE id = ?", (order_id,)
    )
    conn.commit()
    conn.close()

    return {"consumed_grams": consumed_grams, "ratio": ratio, "elapsed_hours": elapsed_hours}


def mark_as_sold(order_id: int):
    conn = get_connection()
    try:
        conn.execute("UPDATE orders SET status = 'Satıldı' WHERE id = ?", (order_id,))
        conn.commit()
    finally:
        conn.close()


init_db()
