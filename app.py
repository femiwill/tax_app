# app.py
import os
import base64
import json
from io import BytesIO
from flask import Flask, render_template, request, send_file
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import OperationalError
from reportlab.platypus import Table, TableStyle, SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4

# -------------------------
# Flask setup
# -------------------------
app = Flask(__name__)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "tax_records.db")
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# -------------------------
# DB model
# -------------------------
class TaxRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    annual_income = db.Column(db.Float)
    total_deductions = db.Column(db.Float)
    taxable_old = db.Column(db.Float)
    tax_old = db.Column(db.Float)
    taxable_new = db.Column(db.Float)
    tax_new = db.Column(db.Float)
    net_annual_old = db.Column(db.Float)
    net_annual_new = db.Column(db.Float)
    net_monthly_old = db.Column(db.Float)
    net_monthly_new = db.Column(db.Float)

with app.app_context():
    try:
        db.create_all()
    except OperationalError:
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        db.create_all()

# -------------------------
# Helpers
# -------------------------
def parse_amount(text):
    if text is None or text.strip() == "":
        return 0.0
    try:
        return float(text.replace(",", "").replace(" ", ""))
    except ValueError:
        return 0.0

def format_amount(num):
    try:
        return f"₦{float(num):,.2f}" if num is not None else "₦0.00"
    except Exception:
        return "₦0.00"

app.jinja_env.globals.update(format_amount=format_amount)

# -------------------------
# CRA (Old law)
# -------------------------
def compute_cra(gross_income, pension_annual):
    part1 = max(200_000.0, 0.01 * gross_income)
    part2 = 0.20 * max(0.0, gross_income - pension_annual)
    return part1 + part2

# -------------------------
# Tax brackets
# -------------------------
OLD_BRACKETS = [
    (300_000, 0.07),
    (300_000, 0.11),
    (500_000, 0.15),
    (500_000, 0.19),
    (1_600_000, 0.21),
    (float("inf"), 0.24)
]

NEW_BRACKETS = [
    (800_000, 0.00),
    (2_200_000, 0.15),
    (9_000_000, 0.18),
    (13_000_000, 0.21),
    (25_000_000, 0.23),
    (float("inf"), 0.25)
]

def apply_brackets(taxable_income, brackets):
    remaining = taxable_income
    total_tax = 0.0
    breakdown = []
    for limit, rate in brackets:
        if remaining <= 0:
            break
        amount = min(remaining, limit)
        tax = amount * rate
        breakdown.append((amount, rate, tax))
        total_tax += tax
        remaining -= amount
    return total_tax, breakdown

def rent_relief_calc(annual_rent):
    return min(500_000.0, 0.20 * annual_rent)

# -------------------------
# Routes
# -------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        annual_income = parse_amount(request.form.get("annual_income"))
        # monthly deductions
        pension_month = parse_amount(request.form.get("pension"))
        voluntary_pension_month = parse_amount(request.form.get("voluntary_pension"))
        health_month = parse_amount(request.form.get("health"))
        life_insurance_month = parse_amount(request.form.get("life_insurance"))
        # annual deductions
        rent_annual = parse_amount(request.form.get("rent_annual"))
        nhf_annual = parse_amount(request.form.get("nhf_annual"))
        nhis_annual = parse_amount(request.form.get("nhis_annual"))
        interest_owner_annual = parse_amount(request.form.get("interest_owner_annual"))

        # annualize monthly deductions
        pension_annual = pension_month * 12
        voluntary_pension_annual = voluntary_pension_month * 12
        health_annual = health_month * 12
        life_insurance_annual = life_insurance_month * 12

        statutory = (pension_annual + voluntary_pension_annual + health_annual +
                     life_insurance_annual + nhf_annual + nhis_annual + interest_owner_annual)

        # --- OLD LAW ---
        cra = compute_cra(annual_income, pension_annual)
        taxable_old = max(0.0, annual_income - statutory - cra)
        tax_old, breakdown_old = apply_brackets(taxable_old, OLD_BRACKETS)
        net_annual_old = annual_income - tax_old
        net_monthly_old = net_annual_old / 12 if annual_income else 0.0
        total_deductions_old = statutory + cra

        # --- NEW LAW ---
        rent_relief = rent_relief_calc(rent_annual)
        taxable_new = max(0.0, annual_income - statutory - rent_relief)
        tax_new, breakdown_new = apply_brackets(taxable_new, NEW_BRACKETS)
        net_annual_new = annual_income - tax_new
        net_monthly_new = net_annual_new / 12 if annual_income else 0.0
        total_deductions_new = statutory + rent_relief

        # Save record
        record = TaxRecord(
            annual_income=annual_income,
            total_deductions=total_deductions_new,
            taxable_old=taxable_old,
            tax_old=tax_old,
            taxable_new=taxable_new,
            tax_new=tax_new,
            net_annual_old=net_annual_old,
            net_annual_new=net_annual_new,
            net_monthly_old=net_monthly_old,
            net_monthly_new=net_monthly_new
        )
        db.session.add(record)
        db.session.commit()

        return render_template("result.html",
                               annual_income=annual_income,
                               pension_annual=pension_annual,
                               voluntary_pension_annual=voluntary_pension_annual,
                               health_annual=health_annual,
                               life_insurance_annual=life_insurance_annual,
                               rent_annual=rent_annual,
                               nhf_annual=nhf_annual,
                               nhis_annual=nhis_annual,
                               interest_owner_annual=interest_owner_annual,
                               statutory=statutory,
                               cra=cra,
                               rent_relief=rent_relief,
                               total_deductions_old=total_deductions_old,
                               total_deductions_new=total_deductions_new,
                               taxable_old=taxable_old,
                               tax_old=tax_old,
                               breakdown_old=breakdown_old,
                               net_annual_old=net_annual_old,
                               net_monthly_old=net_monthly_old,
                               taxable_new=taxable_new,
                               tax_new=tax_new,
                               breakdown_new=breakdown_new,
                               net_annual_new=net_annual_new,
                               net_monthly_new=net_monthly_new)
    return render_template("index.html")

# -------------------------
# PDF Export with full breakdown
# -------------------------
@app.route("/download_pdf", methods=["POST"])
def download_pdf():
    annual_income = parse_amount(request.form.get("annual_income"))
    tax_old = parse_amount(request.form.get("tax_old"))
    tax_new = parse_amount(request.form.get("tax_new"))
    net_annual_old = parse_amount(request.form.get("net_annual_old"))
    net_annual_new = parse_amount(request.form.get("net_annual_new"))
    chart_image = request.form.get("chart_image")

    # Get breakdowns from JSON passed from frontend
    breakdown_old = json.loads(request.form.get("breakdown_old", "[]"))
    breakdown_new = json.loads(request.form.get("breakdown_new", "[]"))

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    title_style = styles["Heading2"]
    normal = styles["Normal"]

    elements.append(Paragraph("Nigeria Personal Income Tax Comparison (Old vs New)", title_style))
    elements.append(Spacer(1,12))
    elements.append(Paragraph(f"Annual Gross Income: ₦{annual_income:,.2f}", normal))
    elements.append(Spacer(1,12))

    # Old Law Table
    elements.append(Paragraph("Old Law Detailed Breakdown", styles["Heading3"]))
    data_old = [["Band Amount (₦)","Rate (%)","Tax (₦)"]]
    for amt, rate, tax in breakdown_old:
        data_old.append([f"₦{amt:,.2f}", f"{rate*100:.2f}", f"₦{tax:,.2f}"])
    data_old.append(["-","Total Tax", f"₦{tax_old:,.2f}"])
    data_old.append(["-","Net Annual", f"₦{net_annual_old:,.2f}"])
    table_old = Table(data_old)
    table_old.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.lightblue),
        ('TEXTCOLOR',(0,0),(-1,0),colors.white),
        ('ALIGN',(0,0),(-1,-1),'CENTER'),
        ('GRID',(0,0),(-1,-1),1,colors.black)
    ]))
    elements.append(table_old)
    elements.append(Spacer(1,12))

    # New Law Table
    elements.append(Paragraph("New Law Detailed Breakdown", styles["Heading3"]))
    data_new = [["Band Amount (₦)","Rate (%)","Tax (₦)"]]
    for amt, rate, tax in breakdown_new:
        data_new.append([f"₦{amt:,.2f}", f"{rate*100:.2f}", f"₦{tax:,.2f}"])
    data_new.append(["-","Total Tax", f"₦{tax_new:,.2f}"])
    data_new.append(["-","Net Annual", f"₦{net_annual_new:,.2f}"])
    table_new = Table(data_new)
    table_new.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.green),
        ('TEXTCOLOR',(0,0),(-1,0),colors.white),
        ('ALIGN',(0,0),(-1,-1),'CENTER'),
        ('GRID',(0,0),(-1,-1),1,colors.black)
    ]))
    elements.append(table_new)
    elements.append(Spacer(1,12))

    # Chart
    if chart_image:
        try:
            image_data = base64.b64decode(chart_image.split(",")[1])
            img = Image(BytesIO(image_data), width=480, height=300)
            elements.append(img)
        except Exception as e:
            print("Failed to embed chart:", e)

    doc.build(elements)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="nigeria_pit_comparison.pdf", mimetype="application/pdf")

# -------------------------
# Run app
# -------------------------
if __name__ == "__main__":
    app.run(debug=True)