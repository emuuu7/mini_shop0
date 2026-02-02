# mini_shop0
mini_shop0 is a lightweight e-commerce web application that allows administrators to manage product carts and buyers to place and complete orders. Built using HTML, CSS, and Flask, this project provides a user-friendly interface for both admins and customers, streamlining the shopping experience.
# 🛒 Mini Shop — Flask Web Application
Mini Shop is a simple e-commerce web application built with **Flask (Python)**.  
The project demonstrates core backend and web development concepts including routing, template rendering, static file handling, and basic shopping workflows.
---
##  Features
- Product catalog display
- Shopping cart functionality
- Checkout and order summary
- Admin login and product management pages
- Image handling using Flask static folder

---
##  Tech Stack
- **Backend:** Python, Flask  
- **Frontend:** HTML5, CSS3  
- **Version Control:** Git & GitHub  

---
##  Project Structure
mini_shop0/
│── app.py
│── requirements.txt
│── README.md
│
├── templates/
│ ├── admin_login.html
│ ├── admin_products.html
│ ├── cart.html
│ ├── catalog.html
│ ├── checkout.html
│ ├── layout.html
│ └── order_summary.html
│
├── static/
│ └── img/
│ └── (product and UI images)


---
##  How to Run Locally
### 1️⃣ Clone the repository
```bash
git clone https://github.com/emuuu7/mini_shop0
cd mini_shop0
2️⃣ Create and activate a virtual environment (recommended)
python -m venv venv
venv\Scripts\activate
3️⃣ Install dependencies
pip install -r requirements.txt
4️⃣ Run the application
python app.py
Open your browser and visit:
http://127.0.0.1:5000/
```

## Project Purpose
This project was developed to practice and demonstrate:
Flask application structure
Template-based rendering
Static asset management
Building a small but complete web application
Using GitHub for version control and collaboration

🌍 Live Demo
🚧 Deployment coming soon (Render)

📌 Future Improvements
Database integration (SQLite / MySQL)
User authentication and authorization
Admin role separation
Payment gateway integration
Improved UI styling
