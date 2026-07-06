import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
import json
import os

import db
from utils.calculations import (
    calculate_gram_price,
    calculate_multi_filament_cost,
    calculate_total_cost_with_expenses,
    calculate_sale_price,
    calculate_profit,
    calculate_roi,
    is_shelf_life_exceeded,
    shelf_life_remaining_days,
    optimize_gcode_line,
    SHELF_LIFE_MONTHS,
)

st.set_page_config(page_title="3D Atölye Yönetim Platformu", page_icon="🏭", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .stMetric { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 15px; border-radius: 10px; color: white; }
    .stMetric label { color: #ffffffcc !important; }
    .stMetric [data-testid="stMetricValue"] { color: #ffffff !important; }
    div[data-testid="stSidebar"] { background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%); }
    div[data-testid="stSidebar"] .stRadio label { color: #e0e0e0; }
    .warning-card { background: #fff3cd; border-left: 4px solid #ffc107; padding: 12px; border-radius: 4px; margin: 8px 0; }
    .success-card { background: #d4edda; border-left: 4px solid #28a745; padding: 12px; border-radius: 4px; margin: 8px 0; }
    .danger-card { background: #f8d7da; border-left: 4px solid #dc3545; padding: 12px; border-radius: 4px; margin: 8px 0; }
    .info-card { background: #d1ecf1; border-left: 4px solid #17a2b8; padding: 12px; border-radius: 4px; margin: 8px 0; }
</style>
""", unsafe_allow_html=True)

EXPENSE_CATEGORIES = ["Filament Alış", "Anahtarlık Zinciri", "Hediye Paketi", "Tutkal", "Boya / Vernik", "Kutu / Ambalaj", "Kargo", "Diğer"]


def sidebar():
    with st.sidebar:
        st.markdown("# 🏭 3D Atölye")
        st.markdown("---")
        page = st.radio("Modül Seçin", [
            "📊 Dashboard", "🧵 Filament Stok", "💰 Maliyet & ROI",
            "🏷️ Sipariş Oluştur", "🧾 Gider Yönetimi",
            "⚙️ G-code Optimizasyon", "✅ Kalite Kontrol", "⚙️ Ayarlar",
        ], label_visibility="collapsed")
        st.markdown("---")
        st.caption("v2.0 | Bambu Lab A1 Optimized")
        st.caption("Bu uygulama Kerem Malkoç & Gürkan Şimşek ortaklığıdır..")
    return page


def page_dashboard():
    st.title("📊 Dashboard")
    st.markdown("---")
    summary = db.get_revenue_summary()
    actual = db.get_actual_sales_summary()
    filaments = db.get_all_filaments()
    expense_summary = db.get_expense_summary()

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Toplam Sipariş", summary["total_orders"])
    c2.metric("Hesaplanan Ciro", f"₺{summary['total_revenue']:,.2f}")
    c3.metric("Toplam Maliyet", f"₺{summary['total_cost']:,.2f}")
    c4.metric("Hesaplanan Kâr", f"₺{summary['total_profit']:,.2f}")
    c5.metric("Toplam Gider", f"₺{expense_summary['total_expenses']:,.2f}")

    st.markdown("---")
    st.subheader("💰 Gerçek Satış Analizi (Satılanlar)")
    if actual["sold_count"] > 0:
        a1, a2, a3, a4, a5 = st.columns(5)
        a1.metric("Satılan Adet", f"{actual['sold_count']}")
        a2.metric("Gerçek Ciro", f"₺{actual['actual_revenue']:,.2f}")
        a3.metric("Satılanların Maliyeti", f"₺{actual['sold_cost']:,.2f}")
        real_p = actual['actual_profit']
        if real_p >= 0:
            a4.metric("GERÇEK KÂR", f"₺{real_p:,.2f}")
        else:
            a4.metric("GERÇEK ZARAR", f"-₺{abs(real_p):,.2f}")
        diff = actual['price_diff']
        if diff >= 0:
            a5.metric("Fiyat Farkı", f"+₺{diff:,.2f}")
        else:
            a5.metric("Fiyat Farkı", f"-₺{abs(diff):,.2f}")
    else:
        st.info("Henüz satılmış sipariş yok.")

    st.markdown("---")
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Filament Stok Durumu")
        if filaments:
            for f in [x for x in filaments if is_shelf_life_exceeded(x["opening_date"])]:
                st.markdown(f'<div class="warning-card">⚠️ <b>{f["brand"]} {f["color"]}</b> - Raf ömrü doldu!</div>', unsafe_allow_html=True)
            for f in [x for x in filaments if x["remaining_grams"] < 100]:
                st.markdown(f'<div class="danger-card">🔴 <b>{f["brand"]} {f["color"]}</b> - Stok kritik: {f["remaining_grams"]:.0f}g</div>', unsafe_allow_html=True)
            df = pd.DataFrame(filaments)
            fig = px.bar(df, x="color", y="remaining_grams", color="brand", title="Filament Stokları (g)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Henüz filament eklenmemiş.")

    with col_right:
        monthly = db.get_monthly_revenue()
        if monthly:
            df_m = pd.DataFrame(monthly)
            fig = go.Figure()
            fig.add_trace(go.Bar(x=df_m["month"], y=df_m["revenue"], name="Ciro", marker_color="#667eea"))
            fig.add_trace(go.Bar(x=df_m["month"], y=df_m["cost"], name="Maliyet", marker_color="#f093fb"))
            fig.add_trace(go.Scatter(x=df_m["month"], y=df_m["profit"], name="Kâr", mode="lines+markers", line=dict(color="#4ade80", width=3)))
            fig.update_layout(barmode="group", title="Aylık Finansal Özet")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Henüz sipariş verisi yok.")

        if summary["total_orders"] > 0:
            fig2 = go.Figure(data=[go.Pie(
                labels=["Filament", "Elektrik", "Amortisman", "Ek Giderler"],
                values=[summary["total_filament_cost"], summary["total_electricity_cost"], summary["total_amortization_cost"], summary["total_expense_cost"]],
                hole=0.4, marker_colors=["#667eea", "#f093fb", "#4ade80", "#fbbf24"],
            )])
            fig2.update_layout(height=280, margin=dict(t=20, b=20), title="Maliyet Dağılımı")
            st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")
    st.subheader("Son Siparişler")
    orders = db.get_all_orders()
    if orders:
        for o in orders[:5]:
            fil_str = ", ".join([f"{f['brand']} {f['color']} ({f['grams_used']}g)" for f in o.get("filaments", [])])
            status = o.get("status", "Tamamlandı")
            status_icon = {"Tamamlandı": "🟢", "Satıldı": "💰", "Hatalı Baskı": "🔴"}.get(status, "⚪")
            if status == "Satıldı" and o.get("actual_sale_price"):
                real_p = o["actual_sale_price"] - o["total_cost"]
                diff = o["actual_sale_price"] - o["sale_price"]
                st.markdown(f"{status_icon} **{o['product_name']}** | {fil_str} | Satış: ₺{o['actual_sale_price']:,.2f} (hesap: ₺{o['sale_price']:,.2f}) | Fark: {'+'if diff>=0 else ''}₺{diff:,.2f} | Kâr: ₺{real_p:,.2f} | {o['created_at']}")
            else:
                st.markdown(f"{status_icon} **{o['product_name']}** | {fil_str} | ₺{o['sale_price']:,.2f} | Kâr: ₺{o['profit']:,.2f} | {status} | {o['created_at']}")
    else:
        st.info("Henüz sipariş yok.")


def page_filament():
    st.title("🧵 Filament Stok Yönetimi")
    st.markdown("---")
    tab_add, tab_list = st.tabs(["➕ Filament Ekle", "📋 Stok Listesi"])

    with tab_add:
        with st.form("add_filament_form"):
            c1, c2 = st.columns(2)
            with c1:
                brand = st.text_input("Marka", placeholder="ör: Polymaker, eSUN")
                material_type = st.selectbox("Tür", ["PLA", "PLA+", "PETG", "TPU", "ABS", "ASA", "Nylon", "PC", "Diğer"])
                color = st.text_input("Renk", placeholder="ör: Kırmızı, Siyah")
            with c2:
                remaining_grams = st.number_input("Gramaj (g)", min_value=1.0, value=1000.0, step=10.0)
                purchase_price = st.number_input("Alış Fiyatı (₺)", min_value=0.0, value=350.0, step=10.0)
                purchase_date = st.date_input("Alış Tarihi", value=date.today())
                opening_date = st.date_input("Açılış Tarihi", value=date.today())
            if st.form_submit_button("🧵 Filament Ekle", use_container_width=True, type="primary"):
                if not brand or not color:
                    st.error("Marka ve Renk zorunludur.")
                else:
                    db.add_filament(brand, material_type, color, remaining_grams, purchase_price, purchase_date.strftime("%Y-%m-%d"), opening_date.strftime("%Y-%m-%d"))
                    st.success(f"✅ {brand} {color} eklendi!")
                    st.rerun()

    with tab_list:
        filaments = db.get_all_filaments()
        if not filaments:
            st.info("Henüz filament eklenmemiş.")
            return
        for f in filaments:
            expired = is_shelf_life_exceeded(f["opening_date"])
            remaining = shelf_life_remaining_days(f["opening_date"])
            gp = calculate_gram_price(f["purchase_price"])
            with st.expander(f"{'⚠️ ' if expired else ''}{f['brand']} {f['color']} ({f['material_type']}) - {f['remaining_grams']:.0f}g | ₺{gp:.2f}/g"):
                if expired:
                    st.markdown(f'<div class="warning-card">⚠️ <b>Raf ömrü doldu!</b> Nem kontrolü yapın.</div>', unsafe_allow_html=True)
                elif remaining < 30:
                    st.markdown(f'<div class="info-card">ℹ️ Raf ömrüne {remaining} gün kaldı.</div>', unsafe_allow_html=True)
                c1, c2, c3 = st.columns(3)
                c1.metric("Kalan Gram", f"{f['remaining_grams']:.0f}g")
                c2.metric("Birim Fiyat", f"₺{gp:.2f}/g")
                c3.metric("Toplam Değer", f"₺{f['remaining_grams'] * gp:,.2f}")
                st.caption(f"Alış: {f.get('purchase_date', 'N/A')} | Açılış: {f['opening_date']}")
                with st.form(key=f"edit_{f['id']}"):
                    ec1, ec2 = st.columns(2)
                    with ec1:
                        new_grams = st.number_input("Gram", value=float(f["remaining_grams"]), min_value=0.0, step=10.0, key=f"eg_{f['id']}")
                        new_price = st.number_input("Fiyat (₺)", value=float(f["purchase_price"]), min_value=0.0, step=10.0, key=f"ep_{f['id']}")
                    fc1, fc2 = st.columns(2)
                    if fc1.form_submit_button("💾 Güncelle", use_container_width=True):
                        db.update_filament(f["id"], remaining_grams=new_grams, purchase_price=new_price)
                        st.success("Güncellendi!"); st.rerun()
                    if fc2.form_submit_button("🗑️ Sil", use_container_width=True, type="secondary"):
                        db.delete_filament(f["id"]); st.warning("Silindi."); st.rerun()


def page_cost_calculator():
    st.title("💰 Maliyet Hesaplayıcı & ROI Takibi")
    st.markdown("---")
    settings = db.get_settings()
    summary = db.get_revenue_summary()
    tab_calc, tab_roi = st.tabs(["🧮 Maliyet Hesapla", "📈 ROI Analizi"])

    with tab_calc:
        filaments = db.get_all_filaments()
        if not filaments:
            st.warning("Önce filament ekleyin."); return
        f_opts = {f"{f['brand']} {f['color']} ({f['material_type']}) - {f['remaining_grams']:.0f}g": f for f in filaments}
        selected = st.multiselect("Filament seçin", list(f_opts.keys()))
        items = []
        if selected:
            for label in selected:
                f = f_opts[label]; gp = calculate_gram_price(f["purchase_price"])
                c1, c2, c3 = st.columns([2, 2, 1])
                with c1: st.markdown(f"**{f['brand']} {f['color']}** (₺{gp:.2f}/g)")
                with c2: g = st.number_input("Gram", min_value=1.0, value=50.0, step=1.0, key=f"cg_{f['id']}", label_visibility="collapsed")
                with c3: st.metric("Maliyet", f"₺{g*gp:,.2f}", label_visibility="collapsed")
                items.append({"filament_id": f["id"], "grams_used": g, "gram_price": gp, "filament_cost": round(g*gp, 2)})
        print_hours = st.number_input("Baskı Süresi (saat)", min_value=0.01, value=2.0, step=0.25)
        if items:
            fc = sum(i["filament_cost"] for i in items)
            cost = calculate_total_cost_with_expenses(fc, print_hours, settings["electricity_price_kwh"], settings["printer_price"], settings["target_amortization_hours"], 0.0, settings["power_watts"])
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Filament", f"₺{cost['filament_cost']:,.2f}")
            c2.metric("Elektrik", f"₺{cost['electricity_cost']:,.2f}")
            c3.metric("Amortisman", f"₺{cost['amortization_cost']:,.2f}")
            c4.metric("Net Maliyet", f"₺{cost['total_cost']:,.2f}")

    with tab_roi:
        c1, c2 = st.columns(2)
        with c1:
            st.metric("Yazıcı Fiyatı", f"₺{settings['printer_price']:,.0f}")
            st.metric("Toplam Kâr", f"₺{summary['total_profit']:,.2f}")
        with c2:
            mr = st.number_input("Aylık Ciro (₺)", min_value=0.0, value=5000.0, step=500.0)
            mc = st.number_input("Aylık Gider (₺)", min_value=0.0, value=1500.0, step=100.0)
        if st.button("📈 ROI Hesapla", use_container_width=True, type="primary"):
            roi = calculate_roi(settings["printer_price"], mr, mc)
            rc1, rc2, rc3 = st.columns(3)
            rc1.metric("Aylık Kâr", f"₺{roi['monthly_profit']:,.2f}")
            rc2.metric("Geri Dönüş", f"{roi['payback_months']} ay" if roi['payback_months'] != float('inf') else "Kârsız")
            rc3.metric("Yıllık ROI", f"%{roi['annual_roi_pct']}")
            if roi["payback_months"] != float("inf"):
                months = list(range(1, int(roi["payback_months"]) + 13))
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=months, y=[(mr - mc) * (i+1) for i in range(len(months))], mode="lines+markers", name="Kümülatif Kâr", line=dict(color="#4ade80", width=3)))
                fig.add_hline(y=settings["printer_price"], line_dash="dash", line_color="red", annotation_text=f"Yatırım: ₺{settings['printer_price']:,.0f}")
                fig.update_layout(title="Yatırım Geri Dönüşü", xaxis_title="Ay", yaxis_title="Kümülatif Kâr (₺)")
                st.plotly_chart(fig, use_container_width=True)


def page_pricing():
    st.title("🏷️ Sipariş Oluştur")
    st.markdown("---")
    settings = db.get_settings()
    filaments = db.get_all_filaments()
    if not filaments:
        st.warning("Önce filament ekleyin."); return

    f_opts = {f"{f['brand']} {f['color']} ({f['material_type']}) - {f['remaining_grams']:.0f}g": f for f in filaments}

    tab_create, tab_manage = st.tabs(["➕ Sipariş Oluştur", "📋 Sipariş Yönetimi"])

    with tab_create:
        st.subheader("1. Ürün Bilgileri")
        c_name, c_qty = st.columns([3, 1])
        with c_name:
            product_name = st.text_input("Ürün Adı", placeholder="ör: Telefon Kılıfı, Anahtarlık, Vazo")
        with c_qty:
            quantity = st.number_input("Adet", min_value=1, value=1, step=1)

        photo = st.file_uploader("Ürün Fotoğrafı", type=["jpg", "jpeg", "png", "webp"], key="order_photo")

        st.markdown("---")
        st.subheader("2. Filament Seçimi (Toplam Gram)")
        st.caption("Toplam harcanan filament gramını girin. Adet sayısına bölünerek birim maliyet hesaplanır.")
        sel_fil = st.multiselect("Kullanılacak filamentleri seçin", list(f_opts.keys()))
        fil_items = []
        if sel_fil:
            for label in sel_fil:
                f = f_opts[label]; gp = calculate_gram_price(f["purchase_price"])
                c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
                with c1:
                    st.markdown(f"**{f['brand']} {f['color']}** ({f['material_type']})")
                    st.caption(f"₺{gp:.2f}/g | Stok: {f['remaining_grams']:.0f}g")
                with c2:
                    total_g = st.number_input("Toplam Gram (g)", min_value=1.0, value=50.0, step=1.0, key=f"og_{f['id']}")
                with c3:
                    unit_g = total_g / quantity if quantity > 0 else 0
                    st.metric("Birim", f"{unit_g:.1f}g/adet")
                with c4:
                    st.metric("Toplam Maliyet", f"₺{total_g * gp:,.2f}")
                fil_items.append({"filament_id": f["id"], "brand": f["brand"], "color": f["color"], "material_type": f["material_type"],
                                  "grams_used": total_g, "gram_price": gp, "filament_cost": round(total_g * gp, 2), "remaining": f["remaining_grams"]})

        st.markdown("---")
        st.subheader("3. Baskı Süresi & Kâr Marjı")
        c1, c2 = st.columns(2)
        with c1: print_hours = st.number_input("Baskı Süresi (saat)", min_value=0.01, value=2.0, step=0.25)
        with c2: profit_margin = st.number_input("Kâr Marjı (%)", min_value=0.0, value=50.0, step=5.0)

        st.markdown("---")
        st.subheader("4. Ek Giderler")
        st.caption("Anahtarlık zinciri, hediye paketi, kargo vb.")
        if "order_expenses" not in st.session_state:
            st.session_state.order_expenses = []

        for i in range(len(st.session_state.order_expenses)):
            ecols = st.columns([3, 2, 2, 1])
            with ecols[0]:
                st.session_state.order_expenses[i]["description"] = st.text_input("Açıklama", value=st.session_state.order_expenses[i]["description"], key=f"od_{i}", label_visibility="collapsed", placeholder="ör: 2 adet zincir")
            with ecols[1]:
                idx = EXPENSE_CATEGORIES.index(st.session_state.order_expenses[i]["category"]) if st.session_state.order_expenses[i]["category"] in EXPENSE_CATEGORIES else 6
                st.session_state.order_expenses[i]["category"] = st.selectbox("Kategori", EXPENSE_CATEGORIES, index=idx, key=f"oc_{i}", label_visibility="collapsed")
            with ecols[2]:
                st.session_state.order_expenses[i]["amount"] = st.number_input("Tutar", value=st.session_state.order_expenses[i]["amount"], min_value=0.0, step=0.5, key=f"oa_{i}", label_visibility="collapsed")
            with ecols[3]:
                if st.button("🗑️", key=f"ox_{i}"):
                    st.session_state.order_expenses.pop(i); st.rerun()

        if st.button("➕ Gider Kalemi Ekle", key="add_oe"):
            st.session_state.order_expenses.append({"description": "", "category": "Diğer", "amount": 0.0}); st.rerun()

        if fil_items:
            st.markdown("---")
            st.subheader("5. Maliyet & Fiyat Analizi")
            total_grams_sum = sum(i["grams_used"] for i in fil_items)
            fc = sum(i["filament_cost"] for i in fil_items)
            exp_clean = [e for e in st.session_state.order_expenses if e.get("amount", 0) > 0]
            te = sum(e["amount"] for e in exp_clean)
            cost = calculate_total_cost_with_expenses(fc, print_hours, settings["electricity_price_kwh"], settings["printer_price"], settings["target_amortization_hours"], te, settings["power_watts"])
            sp = calculate_sale_price(cost["total_cost"], profit_margin)
            pa = calculate_profit(sp, cost["total_cost"])
            unit_cost = cost["total_cost"] / quantity if quantity > 0 else 0

            cc, ct = st.columns([1, 1])
            with cc:
                fig = go.Figure(data=[go.Pie(labels=["Filament", "Elektrik", "Amortisman", "Ek Giderler"],
                    values=[cost["filament_cost"], cost["electricity_cost"], cost["amortization_cost"], cost["expense_cost"]],
                    hole=0.4, marker_colors=["#667eea", "#f093fb", "#4ade80", "#fbbf24"])])
                fig.update_layout(height=280, margin=dict(t=20, b=20))
                st.plotly_chart(fig, use_container_width=True)
            with ct:
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Toplam Maliyet", f"₺{cost['total_cost']:,.2f}"); m2.metric("Birim Maliyet", f"₺{unit_cost:,.2f}")
                m3.metric("Toplam Satış", f"₺{sp:,.2f}"); m4.metric("Toplam Kâr", f"₺{pa:,.2f}")
                m5, m6 = st.columns(2)
                m5.metric("Birim Satış", f"₺{sp / quantity:,.2f}" if quantity > 0 else "₺0")
                m6.metric("Birim Kâr", f"₺{pa / quantity:,.2f}" if quantity > 0 else "₺0")
                st.markdown("---")
                lines = [f"**{product_name or 'Ürün'}** ({quantity} adet)"]
                if quantity > 0:
                    lines.append(f"  Toplam: {total_grams_sum:.0f}g | Birim: {total_grams_sum / quantity:.1f}g/adet")
                else:
                    lines.append(f"  Toplam: {total_grams_sum:.0f}g")
                for i in fil_items:
                    unit_i = i['grams_used'] / quantity if quantity > 0 else i['grams_used']
                    lines.append(f"  ├─ {i['brand']} {i['color']} ({i['grams_used']}g → {unit_i:.1f}g/adet) → ₺{i['filament_cost']:,.2f}")
                lines.append(f"  ├─ Elektrik ({print_hours}sa) → ₺{cost['electricity_cost']:,.2f}")
                lines.append(f"  ├─ Amortisman → ₺{cost['amortization_cost']:,.2f}")
                for e in exp_clean:
                    lines.append(f"  ├─ {e['description'] or e['category']} → ₺{e['amount']:,.2f}")
                lines += [f"  **Toplam Maliyet → ₺{cost['total_cost']:,.2f}**", f"  **Birim Maliyet → ₺{unit_cost:,.2f}**",
                          f"  Kâr (toplam) → +₺{pa:,.2f} | Birim → +₺{pa / quantity:,.2f}" if quantity > 0 else f"  Kâr → +₺{pa:,.2f}",
                          f"  **Satış (toplam) → ₺{sp:,.2f}** | Birim → ₺{sp / quantity:,.2f}" if quantity > 0 else f"  **Satış → ₺{sp:,.2f}**"]
                st.markdown("\n".join(lines))

            st.markdown("---")
            stock_ok = all(i["grams_used"] <= i["remaining"] for i in fil_items)
            if not stock_ok:
                st.error("⚠️ Yetersiz stok!")
                for i in fil_items:
                    if i["grams_used"] > i["remaining"]:
                        st.error(f"  • {i['brand']} {i['color']}: {i['grams_used']}g isteniyor, {i['remaining']:.0f}g kaldı")

            if st.button("🛒 Siparişi Onayla ve Üret", type="primary", use_container_width=True, disabled=not stock_ok or not product_name):
                if not product_name:
                    st.error("Ürün adı girin.")
                elif not fil_items:
                    st.error("En az bir filament seçin.")
                else:
                    photo_path = None
                    if photo:
                        import os
                        upload_dir = os.path.join(os.path.dirname(os.path.abspath(db.__file__)), "uploads")
                        os.makedirs(upload_dir, exist_ok=True)
                        photo_path = os.path.join(upload_dir, f"order_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{photo.name}")
                        with open(photo_path, "wb") as f:
                            f.write(photo.read())
                    oid = db.add_order(product_name, print_hours, json.dumps(cost), cost["filament_cost"], cost["expense_cost"],
                        cost["electricity_cost"], cost["amortization_cost"], cost["total_cost"], sp, profit_margin, pa, fil_items, exp_clean, quantity, total_grams_sum, photo_path)
                    st.session_state.order_expenses = []
                    st.success(f"✅ **{product_name}** siparişi oluşturuldu! (#{oid})\n\n{quantity} adet | Toplam: ₺{sp:,.2f} | Birim: ₺{sp/quantity:,.2f} | Kâr: ₺{pa:,.2f}")
                    st.balloons(); st.rerun()

    with tab_manage:
        st.subheader("📋 Tüm Siparişler")
        orders = db.get_all_orders()
        if not orders:
            st.info("Henüz sipariş yok."); return

        for o in orders:
            status = o.get("status", "Tamamlandı")
            status_colors = {"Tamamlandı": "🟢", "Satıldı": "💰", "Hatalı Baskı": "🔴"}
            status_icon = status_colors.get(status, "⚪")
            qty = o.get("quantity", 1)
            total_g = o.get("total_grams", 0)

            with st.expander(f"{status_icon} #{o['id']} {o['product_name']} | {qty} adet | ₺{o['sale_price']:,.2f} | {status} | {o['created_at']}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Ürün:** {o['product_name']}")
                    st.markdown(f"**Adet:** {qty}")
                    st.markdown(f"**Toplam Gram:** {total_g:.0f}g")
                    if qty > 0:
                        st.markdown(f"**Birim Gram:** {total_g / qty:.1f}g")
                    st.markdown(f"**Baskı Süresi:** {o['print_duration_hours']} saat")
                    st.markdown(f"**Toplam Maliyet:** ₺{o['total_cost']:,.2f}")
                    if qty > 0:
                        st.markdown(f"**Birim Maliyet:** ₺{o['total_cost'] / qty:,.2f}")
                with col2:
                    st.markdown(f"**Satış Fiyatı:** ₺{o['sale_price']:,.2f}")
                    if qty > 0:
                        st.markdown(f"**Birim Satış:** ₺{o['sale_price'] / qty:,.2f}")
                    st.markdown(f"**Kâr:** ₺{o['profit']:,.2f}")
                    if qty > 0:
                        st.markdown(f"**Birim Kâr:** ₺{o['profit'] / qty:,.2f}")
                    st.markdown(f"**Durum:** {status_icon} {status}")

                fil_str = ", ".join([f"{f['brand']} {f['color']} ({f['grams_used']}g)" for f in o.get("filaments", [])])
                if fil_str:
                    st.markdown(f"**Filament:** {fil_str}")

                if o.get("expenses"):
                    exp_str = ", ".join([f"{e['description']} (₺{e['amount']:,.2f})" for e in o["expenses"]])
                    st.markdown(f"**Ek Giderler:** {exp_str}")

                if o.get("photo_path") and os.path.exists(o["photo_path"]):
                    st.image(o["photo_path"], caption=o["product_name"], use_container_width=True)

                st.markdown("---")

                if status == "Satıldı":
                    actual = o.get('actual_sale_price') or o['sale_price']
                    real_profit = actual - o['total_cost']
                    diff = actual - o['sale_price']
                    if diff >= 0:
                        st.success(f"**Satış: ₺{actual:,.2f}** | Hesaplanan: ₺{o['sale_price']:,.2f} | Fark: +₺{diff:,.2f}")
                    else:
                        st.warning(f"**Satış: ₺{actual:,.2f}** | Hesaplanan: ₺{o['sale_price']:,.2f} | Fark: ₺{diff:,.2f}")
                    st.markdown(f"**Maliyet: ₺{o['total_cost']:,.2f}** | **Gerçek Kâr: ₺{real_profit:,.2f}**")
                    if st.button("Durumu Değiştir", key=f"rev_{o['id']}", use_container_width=True):
                        try:
                            db.revert_order_status(o['id'])
                            st.rerun()
                        except Exception as e:
                            st.error(f"Hata: {e}")
                elif status == "Hatalı Baskı":
                    st.error("Bu sipariş hatalı baskı olarak işaretlendi.")
                else:
                    btn_col1, btn_col2, btn_col3 = st.columns(3)
                    with btn_col1:
                        actual_price = st.number_input("Gerçek Satış Fiyatı (₺)", min_value=0.01, value=float(o['sale_price']), step=1.0, key=f"ap_{o['id']}")
                        if st.button("Satıldı", key=f"sold_{o['id']}", use_container_width=True, type="primary"):
                            try:
                                db.mark_as_sold(o['id'], actual_price)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Hata: {e}")
                    with btn_col2:
                        elapsed = st.number_input("Geçen Süre (saat)", min_value=0.01, max_value=float(o['print_duration_hours']), value=float(o['print_duration_hours']), step=0.25, key=f"elapsed_{o['id']}")
                        if st.button("Hatalı Baskı", key=f"def_{o['id']}", use_container_width=True):
                            try:
                                result = db.mark_defective_print(o['id'], elapsed)
                                if "error" in result:
                                    st.error(result["error"])
                                else:
                                    st.warning(f"Hatalı baskı! {result['consumed_grams']:.1f}g filament harcandı (geçen: {elapsed}sa / toplam: {o['print_duration_hours']}sa)")
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Hata: {e}")
                    with btn_col3:
                        if st.button("Sil", key=f"del_{o['id']}", use_container_width=True):
                            try:
                                db.delete_order(o['id'])
                                st.rerun()
                            except Exception as e:
                                st.error(f"Hata: {e}")


def page_expenses():
    st.title("🧾 Gider Yönetimi")
    st.markdown("---")
    tab_add, tab_list, tab_sum = st.tabs(["➕ Gider Ekle", "📋 Gider Listesi", "📊 Özet"])

    with tab_add:
        st.caption("Sipariş dışı bağımsız giderler (kargo, ambalaj vb.)")
        with st.form("add_expense_form"):
            c1, c2 = st.columns(2)
            with c1:
                exp_desc = st.text_input("Açıklama", placeholder="ör: 10 adet kargo kutusu")
                exp_cat = st.selectbox("Kategori", EXPENSE_CATEGORIES)
            with c2:
                exp_amt = st.number_input("Tutar (₺)", min_value=0.01, value=0.01, step=0.5)
            if st.form_submit_button("💾 Kaydet", use_container_width=True, type="primary"):
                if not exp_desc: st.error("Açıklama zorunludur.")
                elif exp_amt <= 0: st.error("Tutar > 0 olmalı.")
                else:
                    db.add_expense(exp_desc, exp_amt, exp_cat)
                    st.success(f"✅ {exp_desc} - ₺{exp_amt:,.2f} kaydedildi"); st.rerun()

    with tab_list:
        expenses = db.get_all_expenses()
        if not expenses:
            st.info("Henüz gider yok."); return
        for e in expenses:
            with st.expander(f"📋 {e['description']} | ₺{e['amount']:,.2f} | {e['category']} | {e['created_at']}"):
                st.markdown(f"**Açıklama:** {e['description']} | **Kategori:** {e['category']} | **Tutar:** ₺{e['amount']:,.2f}")
                if e.get("product_name"): st.markdown(f"**Sipariş:** {e['product_name']}")
                st.caption(f"Tarih: {e['created_at']}")
                if st.button("🗑️ Sil", key=f"de_{e['id']}"):
                    db.delete_expense(e["id"]); st.warning("Silindi."); st.rerun()

    with tab_sum:
        es = db.get_expense_summary()
        cats = db.get_expenses_by_category()
        c1, c2 = st.columns(2)
        c1.metric("Toplam Gider", es["expense_count"])
        c2.metric("Toplam Tutar", f"₺{es['total_expenses']:,.2f}")
        if cats:
            st.markdown("---")
            df = pd.DataFrame(cats)
            fig = px.bar(df, x="category", y="total", color="category", title="Kategorilere Göre Giderler", labels={"total": "₺", "category": "Kategori"})
            st.plotly_chart(fig, use_container_width=True)
            fig2 = go.Figure(data=[go.Pie(labels=df["category"], values=df["total"], hole=0.4, marker_colors=px.colors.qualitative.Set2)])
            fig2.update_layout(height=300, margin=dict(t=20, b=20), title="Gider Dağılımı")
            st.plotly_chart(fig2, use_container_width=True)


def page_gcode():
    st.title("⚙️ G-code Optimizasyon Analizörü")
    st.markdown("---")
    c1, c2 = st.columns([1, 1])
    with c1:
        st.subheader("Dosya Yükle")
        uf = st.file_uploader("G-code dosyası", type=["gcode", "gco", "g", "nc", "txt"])
        st.caption(";TYPE:Internal infill alanlarındaki F değerleri F18000'e çekilir")

    if uf:
        fc = uf.read().decode("utf-8", errors="ignore")
        lines = fc.split("\n"); total = len(lines)
        opt, changed, maxf, infill = [], 0, 0, 0
        for line in lines:
            s = line.strip()
            if s.startswith(";TYPE:") and "Internal infill" in s: infill += 1
            nl, ch = optimize_gcode_line(line); opt.append(nl)
            if ch: changed += 1
            if "F" in s and (s.startswith("G0") or s.startswith("G1")):
                try:
                    fi = s.rfind("F"); fv = ""
                    for ch2 in s[fi+1:]:
                        if ch2.isdigit(): fv += ch2
                        else: break
                    if fv:
                        vi = int(fv)
                        if vi > maxf: maxf = vi
                except ValueError: pass

        with c2:
            st.subheader("Sonuç")
            opt_text = "\n".join(opt)
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Satır", f"{total:,}"); m2.metric("Optimize", f"{changed:,}")
            m3.metric("Max F", f"F{maxf}"); m4.metric("İç Dolgu", f"{infill}")
            if maxf > 18000:
                pct = ((maxf - 18000) / maxf) * 100
                st.markdown(f'<div class="success-card">✅ {changed} satır F{maxf}→F18000 optimize. ~%{pct:.1f} süre kazancı</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="info-card">ℹ️ Tüm F değerleri limitler içinde.</div>', unsafe_allow_html=True)
            st.download_button("📥 Optimize İndir", opt_text, f"opt_{uf.name}", "text/plain", use_container_width=True)
            if st.button("💾 Kaydet"):
                db.save_gcode_analysis(uf.name, f"F{maxf}", "F18000", changed, total); st.success("Kaydedildi!")
            st.code(f"Önce: F{maxf} ({changed} satır) → Sonra: F18000")
        with st.expander("Önizleme (İlk 50 Satır)"):
            st.code("\n".join(opt[:50]), language="gcode")

    st.markdown("---")
    st.subheader("📌 Geçmiş")
    an = db.get_gcode_analyses()
    if an:
        st.dataframe(pd.DataFrame(an)[["filename", "original_time_estimate", "optimized_time_estimate", "lines_optimized", "total_lines", "created_at"]], use_container_width=True)
    else:
        st.info("Henüz analiz yok.")


def page_quality():
    st.title("✅ Kalite Kontrol")
    st.markdown("---")
    defects = {
        "stringing": {"name": "İpliklenme", "icon": "🕸️", "sol": ["Retraction 0.8→1.2mm", "Retraction hızı 30→40mm/s", "Filamenti kurutun", "Nozül -5-10°C", "Travel hızını artırın"]},
        "layer_shift": {"name": "Katman Kayması", "icon": "📐", "sol": ["Kayış gerginliğini kontrol", "Hızı %20-30 azaltın", "Yatak vidalarını sıkın", "Fan hızını kontrol"]},
        "surface_waves": {"name": "Yüzey Dalgalanması", "icon": "🌊", "sol": ["Hızı ve ivmelenmeyi azaltın", "Vidaları sıkın", "Input Shaping kalibrasyonu"]},
        "warping": {"name": "Kıvrılma", "icon": "🔄", "sol": ["Yatak sıc. artırın", "Brim ekleyin (5-8mm)", "Yatağı temizleyin", "Draft shield"]},
        "under_extrusion": {"name": "Eksik Ekstrüzyon", "icon": "📉", "sol": ["Filament çapını kontrol", "Nozül temizleyin", "Flow rate %2-5 artırın", "Sıcaklık +5-10°C"]},
        "over_extrusion": {"name": "Fazla Ekstrüzyon", "icon": "📈", "sol": ["Flow rate %2-5 azaltın", "Nozül sıc. -5-10°C", "Line width kontrol"]},
        "poor_adhesion": {"name": "Yapışma Sorunu", "icon": "❌", "sol": ["Yatağı temizleyin", "Sıcaklık +5-10°C", "Z-offset ayarlayın", "Brim/raft ekleyin"]},
        "holes_gaps": {"name": "Delikler/Boşluklar", "icon": "🕳️", "sol": ["Top/bottom solid kat ↑", "Infill yoğunluğu ↑", "Flow rate kontrol"]},
    }
    with st.form("qf"):
        st.markdown("### Tespit Edilen Kusurlar")
        sel = []; cols = st.columns(2)
        for idx, (k, d) in enumerate(defects.items()):
            with cols[idx % 2]:
                if st.checkbox(f"{d['icon']} {d['name']}", key=f"d_{k}"): sel.append(k)
        st.form_submit_button("🔍 Analiz Et", use_container_width=True, type="primary")

    if sel:
        st.markdown("---")
        pri = {"poor_adhesion": 1, "layer_shift": 1, "under_extrusion": 2, "over_extrusion": 2, "warping": 2, "stringing": 3, "surface_waves": 3, "holes_gaps": 3}
        for i, dk in enumerate(sorted(sel, key=lambda x: pri.get(x, 5)), 1):
            d = defects[dk]; p = pri.get(dk, 5)
            c = "🔴" if p == 1 else "🟡" if p == 2 else "🟢"
            with st.expander(f"{c} **{i}. {d['name']}** ({'Yüksek' if p==1 else 'Orta' if p==2 else 'Düşük'})", expanded=True):
                for j, s in enumerate(d["sol"], 1): st.markdown(f"  {j}. {s}")
                if dk == "stringing": st.code("Retraction: 1.0mm / 40mm/s / Z-Hop: 0.2mm")
                elif dk == "layer_shift": st.code("Kayış: ~1cm eğilmeli | Vidalar: 0.8Nm | Stepper: <60°C")
    elif 'sel' in dir():
        st.success("🎉 Kusur tespit edilmedi!")


def page_settings():
    st.title("⚙️ Ayarlar")
    st.markdown("---")
    s = db.get_settings()
    with st.form("sf"):
        st.subheader("Yazıcı")
        c1, c2 = st.columns(2)
        with c1:
            pn = st.text_input("Ad", value=s["printer_name"])
            pp = st.number_input("Fiyat (₺)", min_value=0.0, value=float(s["printer_price"]), step=500.0)
        with c2:
            tah = st.number_input("Amortisman (saat)", min_value=100.0, value=float(s["target_amortization_hours"]), step=100.0)
            pw = st.number_input("Güç (W)", min_value=10.0, value=float(s["power_watts"]), step=10.0)
        st.subheader("Enerji")
        ep = st.number_input("₺/kWh", min_value=0.0, value=float(s["electricity_price_kwh"]), step=0.1)
        st.markdown("---")
        he = (s["power_watts"]/1000)*ep; ha = pp/tah
        st.markdown(f"| Elektrik | {s['power_watts']}W/1000 × ₺{ep} | **₺{he:.4f}/sa** |\n| Amortisman | ₺{pp:,.0f} ÷ {tah:,.0f} | **₺{ha:.4f}/sa** |")
        if st.form_submit_button("💾 Kaydet", use_container_width=True, type="primary"):
            db.update_settings(ep, pp, tah, pn, pw); st.success("Kaydedildi!"); st.rerun()

    st.markdown("---")
    db_path = os.path.join(os.path.dirname(os.path.abspath(db.__file__)), "atolye.db")
    sz = os.path.getsize(db_path) / 1024 if os.path.exists(db_path) else 0
    st.info(f"DB: {sz:.1f} KB | Filament: {len(db.get_all_filaments())} | Sipariş: {len(db.get_all_orders())} | Gider: {len(db.get_all_expenses())}")

    st.markdown("---")
    st.subheader("Tehlikeli Bölge")
    if st.button("Veritabanını Sıfırla", type="secondary"):
        st.session_state["confirm_reset"] = True
    if st.session_state.get("confirm_reset"):
        st.error("Tüm veriler silinecek! Emin misiniz?")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Evet, Sıfırla", type="primary"):
                db.reset_database()
                st.session_state["confirm_reset"] = False
                st.success("Veritabanı sıfırlandı!"); st.rerun()
        with c2:
            if st.button("İptal"):
                st.session_state["confirm_reset"] = False; st.rerun()


def main():
    page = sidebar()
    pages = {
        "📊 Dashboard": page_dashboard, "🧵 Filament Stok": page_filament,
        "💰 Maliyet & ROI": page_cost_calculator, "🏷️ Sipariş Oluştur": page_pricing,
        "🧾 Gider Yönetimi": page_expenses, "⚙️ G-code Optimizasyon": page_gcode,
        "✅ Kalite Kontrol": page_quality, "⚙️ Ayarlar": page_settings,
    }
    pages.get(page, lambda: None)()


if __name__ == "__main__":
    main()
