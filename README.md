# BrandVoice — Simple, Beautiful Invoice Generator

Build professional, print-ready invoices in seconds. BrandVoice is a lightweight Flask app with Tailwind-powered templates and a clean, guided form to collect your invoice details.

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.x-000000?logo=flask&logoColor=white)
![TailwindCSS](https://img.shields.io/badge/TailwindCSS-CDN-38B2AC?logo=tailwindcss&logoColor=white)

> Note: More branding utilities will be added to this repo.

---

## Features

- Dynamic invoice builder with add/remove line items
- Upload and embed your brand logo
- Payment instructions/bank details field
- Custom thank-you note
- 3 print-friendly Tailwind templates (select at runtime)
- One-click print (save as PDF via your browser)

---

## Quick Start (Windows, PowerShell)

```powershell
# 1) (Optional) Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2) Install dependencies
pip install -r requirements.txt

# 3) Run the app
python app.py
```

Open your browser at: `http://127.0.0.1:5000/generate`

---

## How It Works

1) Fill the form on the Generate page:
   - Business details (name, address, phone, email)
   - Invoice number
   - Client details
   - Line items (add as many as you need)
   - Payment instructions / bank details
   - Thank-you note
   - Brand logo upload
   - Choose one of the available templates

2) Submit the form and preview your invoice rendered with the selected Tailwind template.

3) Click Print and "Save as PDF" from your browser dialog.

---

## Available Templates

- `invoice_template_1.html` — Clean, professional layout
- `invoice_template_2.html` — Sidebar layout with strong branding area
- `invoice_template_3.html` — Minimalist, compact design

All templates are built with Tailwind via CDN and optimized for printing.

---

## Project Structure

```
Brandvoice/
├─ app.py
├─ requirements.txt
├─ static/
│  └─ uploads/           # Saved brand logos
└─ templates/
   ├─ form.html          # Data entry UI
   ├─ preview.html       # Simple preview/landing (not used for rendering invoices)
   ├─ invoice_template_1.html
   ├─ invoice_template_2.html
   └─ invoice_template_3.html
```

---

## Routes

- `GET /` → `index.html` (landing)
- `GET /generate` → `form.html`
- `POST /generate` → Parses form, saves uploaded logo, and renders the chosen invoice template

> The app validates the selected template against an allowlist before rendering.

---

## Form → Template Data Mapping

The following fields are posted and rendered by templates:

- `business_name`, `Invoice_number`, `address`, `phone`, `email`
- `client_name`, `client_contact`
- `items[][name|price|quantity|subtotal]` (repeatable rows)
- `payment_instructions`, `thank_you_note`
- `logo` (file upload) → saved to `static/uploads` and passed to templates as `brand_logo` URL
- `template` → which invoice template to use

---

## Tips

- Use the browser print dialog to export PDFs (Chrome/Edge: Print → Destination: Save as PDF).
- Keep your logos in PNG or high-quality JPG for best print results.
- If you add a new template, include it under `templates/` and add an option in `form.html`.

---

## Contributing / Roadmap

- Add more invoice templates and styles
- Export to PDF server-side (optional enhancement)
- Multi-currency and tax handling
- Reusable components for branding assets

> More branding utilities will be added to this repo.

---

## Troubleshooting

- If the logo doesn't appear, confirm the uploaded file is saved under `static/uploads/` and that the path is accessible in the rendered HTML.
- Tailwind is included via CDN; ensure you have an active internet connection when rendering pages.

---

## License

TBD
