from datetime import datetime, timedelta


SHELF_LIFE_MONTHS = 6
BAMBU_A1_MAX_F = 18000
DEFAULT_PRINTER_PRICE = 15000.0
DEFAULT_AMORTIZATION_HOURS = 2000.0


def calculate_gram_price(purchase_price: float, total_grams: float = 1000.0) -> float:
    if total_grams <= 0:
        return 0.0
    return purchase_price / total_grams


def calculate_electricity_cost(print_hours: float, price_per_kwh: float, power_watts: float = 150.0) -> float:
    return print_hours * (power_watts / 1000.0) * price_per_kwh


def calculate_amortization_cost(print_hours: float, printer_price: float, target_hours: float) -> float:
    if target_hours <= 0:
        return 0.0
    hourly_rate = printer_price / target_hours
    return print_hours * hourly_rate


def calculate_total_cost(
    grams_used: float,
    gram_price: float,
    print_hours: float,
    price_per_kwh: float,
    printer_price: float,
    target_amortization_hours: float,
    power_watts: float = 150.0,
) -> dict:
    filament_cost = grams_used * gram_price
    electricity_cost = calculate_electricity_cost(print_hours, price_per_kwh, power_watts)
    amortization_cost = calculate_amortization_cost(print_hours, printer_price, target_amortization_hours)
    total = filament_cost + electricity_cost + amortization_cost

    return {
        "filament_cost": round(filament_cost, 2),
        "electricity_cost": round(electricity_cost, 2),
        "amortization_cost": round(amortization_cost, 2),
        "total_cost": round(total, 2),
    }


def calculate_sale_price(total_cost: float, profit_margin_pct: float) -> float:
    if total_cost <= 0:
        return 0.0
    return round(total_cost * (1 + profit_margin_pct / 100.0), 2)


def calculate_profit(sale_price: float, total_cost: float) -> float:
    return round(sale_price - total_cost, 2)


def is_shelf_life_exceeded(opening_date_str: str, shelf_months: int = SHELF_LIFE_MONTHS) -> bool:
    try:
        opening_date = datetime.strptime(opening_date_str, "%Y-%m-%d").date()
        expiry_date = opening_date + timedelta(days=shelf_months * 30)
        return datetime.now().date() > expiry_date
    except (ValueError, TypeError):
        return False


def shelf_life_remaining_days(opening_date_str: str, shelf_months: int = SHELF_LIFE_MONTHS) -> int:
    try:
        opening_date = datetime.strptime(opening_date_str, "%Y-%m-%d").date()
        expiry_date = opening_date + timedelta(days=shelf_months * 30)
        remaining = (expiry_date - datetime.now().date()).days
        return max(remaining, 0)
    except (ValueError, TypeError):
        return 0


def calculate_roi(total_investment: float, monthly_revenue: float, monthly_cost: float) -> dict:
    monthly_profit = monthly_revenue - monthly_cost
    if monthly_profit <= 0:
        return {
            "monthly_profit": round(monthly_profit, 2),
            "payback_months": float("inf"),
            "annual_roi_pct": 0.0,
        }
    payback_months = total_investment / monthly_profit
    annual_profit = monthly_profit * 12
    annual_roi_pct = (annual_profit / total_investment) * 100 if total_investment > 0 else 0.0

    return {
        "monthly_profit": round(monthly_profit, 2),
        "payback_months": round(payback_months, 1),
        "annual_roi_pct": round(annual_roi_pct, 1),
    }


def optimize_gcode_line(line: str) -> tuple[str, bool]:
    stripped = line.strip()
    if stripped.startswith(";TYPE:Internal infill"):
        return line, False

    if stripped.startswith("G0") or stripped.startswith("G1"):
        if "F" in stripped:
            parts = stripped.split(";")
            gcode_part = parts[0]
            comment_part = ";" + parts[1] if len(parts) > 1 else ""

            f_idx = gcode_part.rfind("F")
            if f_idx > 0:
                f_start = f_idx + 1
                f_end = f_start
                while f_end < len(gcode_part) and gcode_part[f_end].isdigit():
                    f_end += 1
                try:
                    current_f = int(gcode_part[f_start:f_end])
                    if current_f > BAMBU_A1_MAX_F:
                        new_gcode = gcode_part[:f_idx] + f"F{BAMBU_A1_MAX_F}" + gcode_part[f_end:]
                        return new_gcode + comment_part, True
                except ValueError:
                    pass

    return line, False


def calculate_multi_filament_cost(filament_items: list[dict]) -> float:
    total = 0.0
    for item in filament_items:
        total += item["grams_used"] * item["gram_price"]
    return round(total, 2)


def calculate_total_cost_with_expenses(
    filament_cost: float,
    print_hours: float,
    price_per_kwh: float,
    printer_price: float,
    target_amortization_hours: float,
    expense_cost: float = 0.0,
    power_watts: float = 150.0,
) -> dict:
    electricity_cost = calculate_electricity_cost(print_hours, price_per_kwh, power_watts)
    amortization_cost = calculate_amortization_cost(print_hours, printer_price, target_amortization_hours)
    total = filament_cost + electricity_cost + amortization_cost + expense_cost

    return {
        "filament_cost": round(filament_cost, 2),
        "electricity_cost": round(electricity_cost, 2),
        "amortization_cost": round(amortization_cost, 2),
        "expense_cost": round(expense_cost, 2),
        "total_cost": round(total, 2),
    }


def estimate_print_time_minutes(layer_count: int, avg_layer_time_sec: float) -> float:
    return round((layer_count * avg_layer_time_sec) / 60.0, 1)
