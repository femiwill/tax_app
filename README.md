# Nigeria PIT Tax Calculator

A web app that compares Nigerian Personal Income Tax (PIT) liability under the **old** and **new** tax laws. Enter your income and deductions to see a side-by-side breakdown of tax brackets, net income, and savings.

## Features

- Side-by-side comparison of old vs new tax regimes
- Supports multiple deduction types: pension, voluntary pension, health insurance, life insurance, rent relief, NHF, NHIS, and mortgage interest
- CRA (Consolidated Relief Allowance) calculation for old law
- Rent relief calculation for new law
- PDF export with detailed bracket breakdown and chart
- Dark/light mode toggle
- Responsive design (Bootstrap 5)

## Tax Brackets

**Old Law:** 7%–24% across 6 bands
**New Law:** 0%–25% across 6 bands (first ₦800,000 tax-free)

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py
```

Open http://localhost:5000 in your browser.

## Tech Stack

- **Backend:** Python / Flask / SQLAlchemy
- **Frontend:** Bootstrap 5 / Chart.js
- **PDF Generation:** ReportLab
- **Database:** SQLite
