import random
import secrets
from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_mail import Mail, Message as MailMessage
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///yazilim_kilavuzu.db'
app.config['SECRET_KEY'] = 'gizli-anahtarim'

# Mail Ayarları
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'abdulsametmemiis@gmail.com'
app.config['MAIL_PASSWORD'] = 'eggn ylbv xxsv siuc'
app.config['MAIL_DEFAULT_SENDER'] = 'abdulsametmemiis@gmail.com'

db = SQLAlchemy(app)
mail = Mail(app)


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
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    role = db.Column(db.String(20), nullable=False, default='User')
    private_key = db.Column(db.String(100), unique=True, nullable=False)
    is_banned = db.Column(db.Boolean, default=False)
    is_verified = db.Column(db.Boolean, default=False)


# Uygulama bağlamı ve varsayılan admin hesabı
with app.app_context():
    db.create_all()
    if not AdminUser.query.filter_by(username='admin').first():
        varsayilan_key = 'pk_' + secrets.token_hex(16)
        db.session.add(
            AdminUser(
                username='admin',
                password='1234',
                email='admin@yazilimkilavuzu.com',
                phone='05000000000',
                role='Admin',
                private_key=varsayilan_key,
                is_banned=False,
                is_verified=True,
            )
        )
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
            message=request.form.get('message'),
        )
        db.session.add(yeni_mesaj)
        db.session.commit()
        basari = 'Mesajınız başarıyla iletildi!'
    return render_template('contact.html', basari=basari)


# Kullanıcı Kayıt Olma Rotası (Mail Onaylı)
@app.route('/register', methods=['GET', 'POST'])
def register():
    hata = None
    basari = None
    if request.method == 'POST':
        kullanici_adi = request.form.get('username')
        sifre = request.form.get('password')
        email = request.form.get('email')
        telefon = request.form.get('phone')

        mevcut_kullanici = AdminUser.query.filter_by(
            username=kullanici_adi
        ).first()
        mevcut_email = AdminUser.query.filter_by(email=email).first()

        if mevcut_kullanici:
            hata = 'Bu kullanıcı adı zaten alınmış!'
        elif mevcut_email:
            hata = 'Bu e-posta adresiyle zaten bir kayıt mevcut!'
        else:
            generated_private_key = 'pk_' + secrets.token_hex(16)
            yeni_kullanici = AdminUser(
                username=kullanici_adi,
                password=sifre,
                email=email,
                phone=telefon if telefon else None,
                role='User',
                private_key=generated_private_key,
                is_banned=False,
                is_verified=False,
            )
            db.session.add(yeni_kullanici)
            db.session.commit()

            # E-posta Onay Linki Gönderme
            try:
                token = secrets.token_urlsafe(32)
                session[f'verify_{yeni_kullanici.id}'] = token

                onay_link = url_for(
                    'verify_email',
                    user_id=yeni_kullanici.id,
                    token=token,
                    _external=True,
                )

                msg = MailMessage(
                    'Hesap Onaylama - Yazılım Kılavuzu', recipients=[email]
                )
                msg.body = (
                    f'Merhaba {kullanici_adi},\n\nKayıt işleminizi tamamlamak'
                    f' için lütfen aşağıdaki linke'
                    f' tıklayın:\n{onay_link}\n\nÖzel Anahtarınız: {generated_private_key}\n\nİyi'
                    ' günler!'
                )
                mail.send(msg)

                basari = (
                    'Kayıt başarılı! Lütfen e-postanıza gelen onay linkine'
                    ' tıklayarak hesabınızı aktif edin.'
                )
            except Exception as e:
                basari = (
                    f'Kayıt oluşturuldu ancak mail gönderilemedi (Hata:'
                    f' {str(e)}). Özel Anahtarınız: {generated_private_key}'
                )

    return render_template('admin/register.html', hata=hata, basari=basari)


# E-Posta Onaylama Rotası
@app.route('/verify/<int:user_id>/<token>')
def verify_email(user_id, token):
    if session.get(f'verify_{user_id}') == token:
        user = AdminUser.query.get(user_id)
        if user:
            user.is_verified = True
            db.session.commit()
            session.pop(f'verify_{user_id}', None)
            return (
                'Hesabınız başarıyla onaylandı! Artık <a'
                ' href="/yonetim">Kullanıcı Girişi</a> sayfasından giriş'
                ' yapabilirsiniz.'
            )
    return 'Geçersiz veya süresi dolmuş onay bağlantısı!'


# Kullanıcı Girişi Rotası (Matematiksel Captcha ve Mail Onay Kontrolü ile)
@app.route('/yonetim', methods=['GET', 'POST'])
def yonetim():
    hata = None

    if 'math_answer' not in session or request.method == 'GET':
        n1 = random.randint(1, 10)
        n2 = random.randint(1, 10)
        session['math_answer'] = n1 + n2
        session['math_question'] = f'{n1} + {n2}'

    if request.method == 'POST':
        kullanici_adi = request.form.get('username')
        sifre = request.form.get('password')
        kullanici_cevabi = request.form.get('captcha_answer', '')

        try:
            cevap_int = int(kullanici_cevabi)
        except ValueError:
            cevap_int = -999

        if cevap_int != session.get('math_answer'):
            hata = 'Güvenlik doğrulaması (işlem sonucu) hatalı!'
        else:
            admin = AdminUser.query.filter_by(
                username=kullanici_adi, password=sifre
            ).first()
            if admin:
                if admin.is_banned:
                    hata = (
                        'Bu hesap sistem yöneticisi tarafından banlanmıştır!'
                    )
                elif not admin.is_verified:
                    hata = (
                        'Lütfen önce e-postanıza gelen onay linkine tıklayarak'
                        ' hesabınızı aktifleştirin!'
                    )
                else:
                    session['user'] = admin.username
                    session['role'] = admin.role
                    session.pop('math_answer', None)
                    session.pop('math_question', None)
                    return redirect(url_for('dashboard'))
            else:
                hata = 'Hatalı kullanıcı adı veya şifre!'

    soru = session.get('math_question', '1 + 1')
    return render_template('admin/login.html', hata=hata, soru=soru)


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
                demo_link=request.form.get('demo_link'),
            )
            db.session.add(yeni_urun)
            db.session.commit()
            basari = 'Proje başarıyla eklendi.'

        elif islem == 'urun_sil':
            urun_id = request.form.get('urun_id')
            urun = Product.query.get(urun_id)
            if urun:
                db.session.delete(urun)
                db.session.commit()
                basari = 'Proje silindi.'

        elif islem == 'kullanici_ekle':
            if aktif_rol != 'Admin':
                hata = (
                    "Yeni kullanıcı ekleme yetkiniz yok! Yalnızca 'Admin'"
                    ' yapabilir.'
                )
            else:
                yeni_username = request.form.get('username')
                mevcut_mu = AdminUser.query.filter_by(
                    username=yeni_username
                ).first()
                if mevcut_mu:
                    hata = 'Bu kullanıcı adı zaten mevcut!'
                else:
                    yeni_key = 'pk_' + secrets.token_hex(16)
                    yeni_admin = AdminUser(
                        username=yeni_username,
                        password=request.form.get('password'),
                        email=request.form.get('email'),
                        phone=request.form.get('phone'),
                        role=request.form.get('role'),
                        private_key=yeni_key,
                        is_banned=False,
                        is_verified=True,
                    )
                    db.session.add(yeni_admin)
                    db.session.commit()
                    basari = (
                        'Yeni kullanıcı ve private key başarıyla oluşturuldu.'
                    )

        elif islem == 'kullanici_sil':
            kullanici_id = request.form.get('kullanici_id')
            hedef_kullanici = AdminUser.query.get(kullanici_id)
            toplam_admin = AdminUser.query.filter_by(role='Admin').count()

            if aktif_rol != 'Admin':
                hata = 'Kullanıcı silme yetkiniz yok!'
            elif hedef_kullanici and hedef_kullanici.username == aktif_kullanici_adi:
                hata = 'Kendi hesabınızı panelden silemezsiniz!'
            elif (
                hedef_kullanici
                and hedef_kullanici.role == 'Admin'
                and toplam_admin <= 1
            ):
                hata = 'Sistemdeki son Admin hesabını silemezsiniz!'
            elif hedef_kullanici:
                db.session.delete(hedef_kullanici)
                db.session.commit()
                basari = 'Kullanıcı silindi.'

        elif islem == 'rol_degistir':
            if aktif_rol != 'Admin':
                hata = 'Rol değiştirme yetkiniz yalnızca Adminlere aittir!'
            else:
                kid = request.form.get('kullanici_id')
                yeni_rol = request.form.get('yeni_rol')
                hedef = AdminUser.query.get(kid)
                if hedef:
                    hedef.role = yeni_rol
                    db.session.commit()
                    basari = (
                        f"{hedef.username} kullanıcısının rolü '{yeni_rol}'"
                        ' yapıldı.'
                    )

        elif islem == 'ban_toggle':
            if aktif_rol != 'Admin':
                hata = 'Banlama yetkiniz yalnızca Adminlere aittir!'
            else:
                kid = request.form.get('kullanici_id')
                hedef = AdminUser.query.get(kid)
                if hedef and hedef.username != aktif_kullanici_adi:
                    hedef.is_banned = not hedef.is_banned
                    db.session.commit()
                    durum = (
                        'banlandı' if hedef.is_banned else 'banı kaldırıldı'
                    )
                    basari = f'{hedef.username} adlı kullanıcı {durum}.'
                else:
                    hata = 'Kendinizi banlayamazsınız!'

        elif islem == 'sifre_degistir':
            aktif_user = AdminUser.query.filter_by(
                username=aktif_kullanici_adi
            ).first()
            eski_sifre = request.form.get('eski_sifre')
            yeni_sifre = request.form.get('yeni_sifre')

            if aktif_user and aktif_user.password == eski_sifre:
                aktif_user.password = yeni_sifre
                db.session.commit()
                basari = 'Şifreniz başarıyla güncellendi.'
            else:
                hata = 'Mevcut şifrenizi hatalı girdiniz!'

        elif islem == 'mesaj_okundu':
            mesaj_id = request.form.get('mesaj_id')
            msg = Message.query.get(mesaj_id)
            if msg:
                msg.is_read = True
                db.session.commit()

    tum_urunler = Product.query.all()
    tum_mesajlar = Message.query.all()
    tum_adminler = AdminUser.query.all()

    return render_template(
        'admin/dashboard.html',
        products=tum_urunler,
        messages=tum_mesajlar,
        admins=tum_adminler,
        hata=hata,
        basari=basari,
    )


# Çıkış Yapma Rotası (Ana sayfaya yönlendirir)
@app.route('/cikis')
def cikis():
    session.clear()
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)