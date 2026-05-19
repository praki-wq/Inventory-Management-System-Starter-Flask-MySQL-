# Inventory Management System — Starter (Flask + MySQL)

## Features included
- Product CRUD (Add / Edit / Delete)
- Searchable & sortable product table (DataTables)
- Low-stock report
- Simple Bootstrap UI

## Prereqs
- Python 3.8+
- MySQL 8.x
- pip

## Setup (quick)
1. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate   # on Windows: venv\Scripts\activate
   ```
2. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```
3. Create database and seed sample data:
   ```bash
   mysql -u root -p < db/schema.sql
   ```
4. (Optional) Set environment variables for DB connection:
   ```bash
   export DB_HOST=localhost
   export DB_USER=root
   export DB_PASS=yourpass
   export DB_NAME=inventorydb
   export FLASK_SECRET='change_this'
   ```
   On Windows use `set` or create a `.env` file.
5. Run the app:
   ```bash
   python app.py
   ```
6. Open http://localhost:5000 in your browser.

## Next steps you can add
- User authentication & roles (admin/staff)
- Import CSV bulk product upload
- Export reports to CSV / PDF
- Pagination / server-side search for large datasets
- Alerts (email / SMS) for low stock
- Barcode scanning integration for quick stock updates

## Notes
- The UI uses CDNs for Bootstrap & DataTables; ensure internet access or self-host these assets.
- This starter is intentionally simple and ready to extend for a semester project.
