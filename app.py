from flask import Flask, render_template, redirect, url_for, request, session
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///yazilim_kilavuzu.db'
app.config['SECRET_KEY'] = 'gizli-anahtarim'
db = SQLAlchemy(app)

# Veritabanı Modelleri
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    tech_stack = db.Column(db.String(100), nullable=False)
    demo_link = db.Column(db.String(200), nullable=True)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)

class AdminUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='Admin')

# Uygulama bağlamı ve varsayılan admin hesabı
with app.app_context():
    db.create_all()
    if not AdminUser.query.filter_by(username='admin').first():
        db.session.add(AdminUser(username='admin', password='1234', role='Admin'))
        db.session.commit()

# Ana Sayfa Rotası
@app.route('/')
def index():
    return render_template('index.html')

# Projeler / Ürünler Sayfası Rotası
@app.route('/urunler')
def urunler():
    tum_urunler = Product.query.all()
    return render_template('products.html', products=tum_urunler)

# İletişim Sayfası Rotası
@app.route('/iletisim', methods=['GET', 'POST'])
def iletisim():
    basari = None
    if request.method == 'POST':
        yeni_mesaj = Message(
            name=request.form.get('name'),
            email=request.form.get('email'),
            phone=request.form.get('phone'),
            message=request.form.get('message')
        )
        db.session.add(yeni_mesaj)
        db.session.commit()
        basari = "Mesajınız başarıyla iletildi!"
    return render_template('contact.html', basari=basari)

# Yönetim Giriş Rotası
@app.route('/yonetim', methods=['GET', 'POST'])
def yonetim():
    hata = None
    if request.method == 'POST':
        kullanici_adi = request.form.get('username')
        sifre = request.form.get('password')
        admin = AdminUser.query.filter_by(username=kullanici_adi, password=sifre).first()
        if admin:
            session['user'] = admin.username
            session['role'] = admin.role
            return redirect(url_for('dashboard'))
        hata = "Hatalı kullanıcı adı veya şifre!"
    return render_template('admin/login.html', hata=hata)

# Yönetim Paneli (Dashboard) Rotası
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user' not in session:
        return redirect(url_for('yonetim'))
    
    hata = None
    basari = None
    
    aktif_kullanici_adi = session.get('user')
    aktif_rol = session.get('role')

    if request.method == 'POST':
        islem = request.form.get('islem')
        
        if islem == 'urun_ekle':
            yeni_urun = Product(
                title=request.form.get('title'),
                category=request.form.get('category'),
                description=request.form.get('description'),
                tech_stack=request.form.get('tech_stack'),
                demo_link=request.form.get('demo_link')
            )
            db.session.add(yeni_urun)
            db.session.commit()
            basari = "Proje başarıyla eklendi."
            
        elif islem == 'urun_sil':
            urun_id = request.form.get('urun_id')
            urun = Product.query.get(urun_id)
            if urun:
                db.session.delete(urun)
                db.session.commit()
                basari = "Proje silindi."
                
        elif islem == 'kullanici_ekle':
            if aktif_rol != 'Admin':
                hata = "Yeni kullanıcı ekleme yetkiniz yok! Yalnızca 'Admin' rolündekiler kullanıcı ekleyebilir."
            else:
                yeni_admin = AdminUser(
                    username=request.form.get('username'),
                    password=request.form.get('password'),
                    role=request.form.get('role')
                )
                db.session.add(yeni_admin)
                db.session.commit()
                basari = "Yeni kullanıcı başarıyla eklendi."

        elif islem == 'kullanici_sil':
            kullanici_id = request.form.get('kullanici_id')
            hedef_kullanici = AdminUser.query.get(kullanici_id)
            toplam_admin = AdminUser.query.count()
            
            if aktif_rol != 'Admin':
                hata = "Kullanıcı silme yetkiniz yok! Bu işlem için 'Admin' rolü gereklidir."
            elif hedef_kullanici and hedef_kullanici.username == aktif_kullanici_adi:
                hata = "Kendi hesabınızı yönetim panelinden silemezsiniz!"
            elif toplam_admin <= 1:
                hata = "Sistemdeki son yönetici hesabını silemezsiniz!"
            elif hedef_kullanici:
                db.session.delete(hedef_kullanici)
                db.session.commit()
                basari = "Kullanıcı başarıyla silindi."

        elif islem == 'sifre_degistir':
            aktif_user = AdminUser.query.filter_by(username=aktif_kullanici_adi).first()
            eski_sifre = request.form.get('eski_sifre')
            yeni_sifre = request.form.get('yeni_sifre')
            
            if aktif_user and aktif_user.password == eski_sifre:
                aktif_user.password = yeni_sifre
                db.session.commit()
                basari = "Şifreniz başarıyla güncellendi."
            else:
                hata = "Mevcut şifrenizi hatalı girdiniz!"
                
        elif islem == 'mesaj_okundu':
            mesaj_id = request.form.get('mesaj_id')
            msg = Message.query.get(mesaj_id)
            if msg:
                msg.is_read = True
                db.session.commit()
                
    tum_urunler = Product.query.all()
    tum_mesajlar = Message.query.all()
    tum_adminler = AdminUser.query.all()
    
    return render_template('admin/dashboard.html', 
                           products=tum_urunler, 
                           messages=tum_mesajlar, 
                           admins=tum_adminler,
                           hata=hata,
                           basari=basari)

# Çıkış Yapma Rotası
@app.route('/cikis')
def cikis():
    session.clear()
    return redirect(url_for('yonetim'))

if __name__ == '__main__':
    app.run(debug=True)