import sqlite3
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'car_secret_key_999'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- ฟังก์ชันจัดการ Database ---
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT)''')
    conn.commit()
    conn.close()

init_db() # สร้างฐานข้อมูลเมื่อเริ่มรันแอป

class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT id, username FROM users WHERE id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    if user:
        return User(user[0], user[1])
    return None

# --- Routes ---

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        hashed_pw = generate_password_hash(password) # เข้ารหัสผ่านเพื่อความปลอดภัย

        try:
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_pw))
            conn.commit()
            conn.close()
            flash('สมัครสมาชิกสำเร็จ! กรุณาเข้าสู่ระบบ')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('ชื่อผู้ใช้นี้มีคนใช้แล้ว')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT id, username, password FROM users WHERE username = ?", (username,))
        user_data = c.fetchone()
        conn.close()

        if user_data and check_password_hash(user_data[2], password):
            user = User(id=user_data[0], username=user_data[1])
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง')
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return render_template('index.html', name=current_user.username)

@app.route('/calculate', methods=['POST'])
@login_required
def calculate():
    import random # เพิ่มไว้บรรทัดแรกของฟังก์ชันเพื่อสุ่มแนวโน้มราคา
    data = request.json
    fuel_pct = float(data.get('fuel_pct', 0))
    capacity = float(data.get('capacity', 50))
    consumption = float(data.get('consumption', 15))
    selected_oil_price = float(data.get('oil_price', 0))
    
    # --- ส่วนที่เพิ่มใหม่: Logic แนะนำการเติมน้ำมัน ---
    price_change = random.choice([-0.50, 0.0, 0.40]) # สุ่มว่าราคาจะลด, คงที่, หรือขึ้น
    fuel_to_fill = capacity - ((fuel_pct / 100) * capacity)
    savings = abs(fuel_to_fill * price_change)

    if price_change > 0:
        recommendation = f"🚀 เติมวันนี้เลย! พรุ่งนี้ราคาจะขึ้น {price_change} บาท ประหยัดได้ {round(savings, 2)} บาท"
        color = "danger"
    elif price_change < 0:
        if fuel_pct > 20:
            recommendation = f"⏳ รอพรุ่งนี้ดีกว่า! ราคาจะลดลง {abs(price_change)} บาท ประหยัดได้ {round(savings, 2)} บาท"
            color = "success"
        else:
            recommendation = "⚠️ ท่านเหลือน้ำมันน้อยเกินไป แนะนำให้เติมทันที"
            color = "warning"
    else:
        recommendation = "✅ ราคายังคงที่ เติมเมื่อสะดวกได้เลย"
        color = "info"

    # ส่วนคำนวณเดิม
    odometer = float(data.get('odometer', 0))
    engine_life = max(0, 100 - (odometer / 300000 * 100))
    range_left = ((fuel_pct / 100) * capacity) * consumption
    cost_per_km = selected_oil_price / consumption if consumption > 0 else 0

    return jsonify({
        "engine_life": round(engine_life, 1),
        "range_left": round(range_left, 1),
        "cost_per_km": round(cost_per_km, 2),
        "recommendation": recommendation, # ส่งข้อความแนะนำไปหน้าบ้าน
        "rec_color": color # ส่งสีเตือนไปหน้าบ้าน
    })
    
# ข้อมูลการรองรับน้ำมันแยกตามยี่ห้อและประเภทเครื่องยนต์หลักๆ ในไทย
CAR_FUEL_COMPATIBILITY = {
    # --- กลุ่มรถญี่ปุ่นยอดนิยม ---
    "Toyota": ["GSH95", "GSH91", "E20", "E85", "Benzine", "Diesel", "Premium_Diesel"],
    "Honda": ["GSH95", "GSH91", "E20", "E85", "Premium_GSH95"],
    "Isuzu": ["Diesel", "Premium_Diesel"],
    "Mitsubishi": ["GSH95", "GSH91", "E20", "Diesel", "Premium_Diesel"],
    "Mazda": ["GSH95", "GSH91", "E20", "Diesel", "Premium_Diesel"],
    "Nissan": ["GSH95", "GSH91", "E20", "E85", "Diesel"],
    "Suzuki": ["GSH95", "GSH91", "E20", "E85"],
    "Subaru": ["GSH95", "GSH91", "Benzine"],

    # --- กลุ่มรถยุโรป (เน้นน้ำมันค่าออกเทนสูงและดีเซลพรีเมียม) ---
    "BMW": ["GSH95", "Premium_GSH95", "Benzine", "Diesel", "Premium_Diesel"],
    "Mercedes-Benz": ["GSH95", "Premium_GSH95", "Benzine", "Diesel", "Premium_Diesel"],
    "Audi": ["GSH95", "Premium_GSH95", "Benzine"],
    "Volvo": ["GSH95", "E20", "Diesel", "Premium_Diesel"],
    "Porsche": ["Premium_GSH95", "Benzine", "Premium_Benzine"],

    # --- กลุ่มรถอื่นๆ ---
    "MG": ["GSH95", "GSH91", "E20", "E85", "Diesel"],
    "Ford": ["Diesel", "Premium_Diesel", "GSH95", "E20"],
    "Chevrolet": ["GSH95", "E20", "Diesel", "Premium_Diesel"],
    "Hyundai": ["GSH95", "Diesel", "Premium_Diesel"],
    "Kia": ["GSH95", "Diesel", "Premium_Diesel"]
}
# 2. ข้อมูลราคาน้ำมันแยกตามปั๊ม (อ้างอิงราคาที่คุณให้มา)
STATION_DATA = {
    "บางจาก": {
        "GSH95": ("GSH95S EVO", 42.05), "GSH91": ("GSH91S EVO", 41.68),
        "E20": ("GSH E20S EVO", 37.05), "E85": ("GSH E85S EVO", 33.79),
        "Diesel": ("ดีเซล", 40.74), "Premium_Diesel": ("ไฮพรีเมียมดีเซล S", 58.64)
    },
    "ปตท.": {
        "GSH95": ("GSH95S EVO", 42.05), "GSH91": ("GSH91S EVO", 41.68),
        "E20": ("GSH E20S EVO", 37.05), "E85": ("GSH E85S EVO", 33.79),
        "Benzine": ("เบนซิน", 50.64), "Diesel": ("ดีเซล", 40.74),
        "Premium_Diesel": ("ซูเปอร์พาวเวอร์ ดีเซล", 56.44),
        "Premium_GSH95": ("ซูเปอร์พาวเวอร์ แก๊สโซฮอล์ 95", 53.04)
    },
    "เชลล์": {
        "E20": ("เชลล์ ฟิวเซฟ E20", 37.55), "GSH91": ("เชลล์ ฟิวเซฟ 91", 41.93),
        "GSH95": ("เชลล์ ฟิวเซฟ 95", 42.55), "Premium_GSH95": ("เชลล์ วี-เพาเวอร์ 95", 49.84),
        "Diesel": ("เชลล์ ฟิวเซฟ ดีเซล", 40.94), "Premium_Diesel": ("เชลล์ วี-เพาเวอร์ ดีเซล", 59.84)
    },
    "พีที": {
        "Diesel": ("ดีเซล", 40.74), 
        "GSH95": ("แก๊สโซฮอล์ 95", 42.05),
        "GSH91": ("แก๊สโซฮอล์ 91", 41.68), 
        "Benzine": ("เบนซิน", 51.14), 
        "E20": ("แก๊สโซฮอล์ E20", 37.05)
    },
    "ซัสโก้": {
        "Diesel": ("ดีเซล", 40.74),
        "Benzine": ("เบนซิน", 50.79),
        "GSH95": ("แก๊สโซฮอล์ 95", 42.05),
        "GSH91": ("แก๊สโซฮอล์ 91", 41.68),
        "E20": ("แก๊สโซฮอล์ E20", 37.05)
    },
    "คาลเท็กซ์": {
        "Premium_Benzine": ("โกลด์ 95 เทครอน", 57.51),
        "GSH95": ("แก๊สโซฮอล์ 95 เทครอน", 42.05),
        "GSH91": ("แก๊สโซฮอล์ 91 เทครอน", 41.68),
        "E20": ("แก๊สโซฮอล์ E20", 37.05),
        "Diesel": ("ดีเซล เทครอน", 40.74),
        "Premium_Diesel": ("พาวเวอร์ ดีเซล เทครอน", 58.64)
    }
}
    # สามารถเพิ่มปั๊ม ซัสโก้ และ คาลเท็กซ์ ตามรูปแบบนี้ได้เลยครับ


@app.route('/get_filtered_oil', methods=['POST'])
@login_required
def get_filtered_oil():
    data = request.json
    brand = data.get('brand')
    station = data.get('station')
    
    # ดึงรายการน้ำมันที่รถยี่ห้อนี้ใช้ได้
    compatible_keys = CAR_FUEL_COMPATIBILITY.get(brand, [])
    # ดึงข้อมูลน้ำมันที่ปั๊มนี้มีขาย
    station_oils = STATION_DATA.get(station, {})
    
    # กรองเฉพาะน้ำมันที่ "รถใช้ได้" และ "ปั๊มมีขาย"
    final_options = []
    for key in compatible_keys:
        if key in station_oils:
            name, price = station_oils[key]
            final_options.append({"name": name, "price": price})
            
    return jsonify(final_options)

if __name__ == '__main__':
    app.run(debug=True)