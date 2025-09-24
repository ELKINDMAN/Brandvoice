from flask import Flask, render_template, request, redirect, url_for
import os
from werkzeug.utils import secure_filename


app =Flask(__name__)

@app.route("/")
def home():
    return render_template('index.html')

@app.route("/generate", methods=["GET", "POST"])
def generate():
    if request.method == "POST":
        # Business Details
        business_name = request.form.get("business_name")
        invoice_number = request.form.get("Invoice_number")
        address = request.form.get("address")
        phone = request.form.get("phone")
        email = request.form.get("email")
        # File input name in form is 'logo'
        logo_file = request.files.get("logo")
        payment_instructions = request.form.get("payment_instructions")
        thanks_message = request.form.get("thank_you_note")
        template = request.form.get("template")

        if not all([business_name, address, phone, invoice_number]):
            return "All fields are required!", 400
        
        # Client details
        client_name = request.form.get("client_name")
        client_contact = request.form.get("client_contact")
        if not all([client_name, client_contact]):
            return "All client fields are required!", 400
        
        #invoice items
        items = []
        index = 0

        while True:
            item_name = request.form.get(f"items[{index}][name]")
            item_price = request.form.get(f"items[{index}][price]")
            item_quantity = request.form.get(f"items[{index}][quantity]")
            item_subtotal = request.form.get(f"items[{index}][subtotal]")

            if not item_name:
                break
            
            items.append({
                "name": item_name,
                "price": float(item_price or 0),
                "quantity": int(item_quantity or 0),
                "subtotal": float(item_subtotal or 0),
            })
            index += 1
        # Save logo file if provided and build a URL for templates
        brand_logo_url = None
        if logo_file and logo_file.filename:
            uploads_dir = os.path.join(app.root_path, 'static', 'uploads')
            os.makedirs(uploads_dir, exist_ok=True)
            fname = secure_filename(logo_file.filename)
            save_path = os.path.join(uploads_dir, fname)
            logo_file.save(save_path)
            brand_logo_url = url_for('static', filename=f'uploads/{fname}')

        total_amount = sum(item["subtotal"] for item in items)

        # Allowlist of available templates to prevent path traversal
        allowed_templates = {"invoice_template_1.html", "invoice_template_2.html", "invoice_template_3.html"}
        chosen_template = template if template in allowed_templates else "invoice_template_1.html"

        return render_template(
            chosen_template,
            business_name=business_name,
            invoice_number=invoice_number,
            address=address,
            phone=phone,
            email=email,
            brand_logo=brand_logo_url,
            payment_instructions=payment_instructions,
            thanks_message=thanks_message,
            client_name=client_name,
            client_contact=client_contact,
            items=items,
            total_amount=total_amount,
        )
    return render_template("form.html")



@app.route("/preview", methods=["GET", "POST"])
def preview():
    return render_template("preview.html")



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)