from flask_login import LoginManager, UserMixin, current_user, login_user, logout_user, login_required
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, EqualTo, ValidationError, Email
from flask import Flask, render_template, flash, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_mail import Message, Mail
from itsdangerous import URLSafeTimedSerializer as Serializer
import os

# inicializavimas
app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'data.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key_here'
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

login_manager = LoginManager(app)
login_manager.login_view = "prisijungti"
login_manager.login_message_category = 'info'

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'MAIL_USERNAME'
app.config['MAIL_PASSWORD'] = 'MAIL_PASSWORD'

mail = Mail(app)



@login_manager.user_loader
def load_user(user_id):
    return Vartotojas.query.get(int(user_id))

# forms
class RegistracijosForma(FlaskForm):
    vardas = StringField('Vardas', [DataRequired()])
    el_pastas = StringField('El. paštas', [DataRequired()])
    slaptazodis = PasswordField('Slaptažodis', [DataRequired()])
    patvirtintas_slaptazodis = PasswordField("Pakartokite slaptažodį",
                                             [EqualTo('slaptazodis', "Slaptažodis turi sutapti.")])
    submit = SubmitField('Prisiregistruoti')

    def tikrinti_varda(self, vardas):
        vartotojas = app.Vartotojas.query.filter_by(vardas=vardas.data).first()
        if vartotojas:
            raise ValidationError('Šis vardas panaudotas. Pasirinkite kitą.')

    def tikrinti_pasta(self, el_pastas):
        vartotojas = app.Vartotojas.query.filter_by(el_pastas=el_pastas.data).first()
        if vartotojas:
            raise ValidationError('Šis el. pašto adresas panaudotas. Pasirinkite kitą.')


class PrisijungimoForma(FlaskForm):
    vardas = StringField('Vardas', [DataRequired()])
    slaptazodis = PasswordField('Slaptažodis', [DataRequired()])
    submit = SubmitField('Prisijungti')


class UzduotisForma(FlaskForm):
    pavadinimas = StringField('Pavadinimas', [DataRequired()])
    atlikta = BooleanField('Atlikta')
    submit = SubmitField('Įvesti')

class UzklausosAtnaujinimoForma(FlaskForm):
    el_pastas = StringField('El. paštas', [DataRequired(), Email()])
    submit = SubmitField('Įvesti')

class SlaptazodzioAtnaujinimoForma(FlaskForm):
    slaptazodis = PasswordField("Slaptažodis", validators=[DataRequired()])
    patvirtintas_slaptazodis = PasswordField("Pakartokite slaptažodį", validators=[DataRequired(), EqualTo("slaptazodis")])
    submit = SubmitField('Įvesti')

# modeliai
class Vartotojas(db.Model, UserMixin):
    __tablename__ = "vartotojas"
    id = db.Column(db.Integer, primary_key=True)
    vardas = db.Column("Vardas", db.String(20), unique=True, nullable=False)
    el_pastas = db.Column("El. pašto adresas", db.String(120), unique=True, nullable=False)
    slaptazodis = db.Column("Slaptažodis", db.String(60), unique=True, nullable=False)

    def get_reset_token(self):
        s = Serializer(app.config['SECRET_KEY'])
        return s.dumps({"user_id": self.id})

    @staticmethod
    def verify_reset_token(token):
        s = Serializer(app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token)['user_id']
        except:
            return None
        return db.session.get(Vartotojas, user_id)


class Uzduotis(db.Model):
    __tablename__ = "uzduotis"
    id = db.Column(db.Integer, primary_key=True)
    pavadinimas = db.Column("Pavadinimas", db.String)
    atlikta = db.Column("Atlikta", db.Boolean)
    vartotojas_id = db.Column(db.Integer, db.ForeignKey("vartotojas.id"))
    vartotojas = db.relationship("Vartotojas")


# rodiniai
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/registruotis", methods=['GET', 'POST'])
def registruotis():
    form = RegistracijosForma()
    if current_user.is_authenticated:
        flash('Jau esate prisijungę', 'danger')
        return redirect(url_for("index"))
    if form.validate_on_submit():
        koduotas_slaptazodis = bcrypt.generate_password_hash(form.slaptazodis.data).decode("utf-8")
        vartotojas = Vartotojas(vardas=form.vardas.data, el_pastas=form.el_pastas.data, slaptazodis=koduotas_slaptazodis)
        db.session.add(vartotojas)
        db.session.commit()
        flash('Sėkmingai prisiregistravote! Galite prisijungti', 'success')
        return redirect(url_for("index"))
    return render_template('registruotis.html', form=form)

@app.route("/prisijungti", methods=['GET', 'POST'])
def prisijungti():
    form = PrisijungimoForma()
    if current_user.is_authenticated:
        flash('Jau esate prisijungę', 'danger')
        return redirect(url_for("index"))
    if form.validate_on_submit():
        user = Vartotojas.query.filter_by(vardas=form.vardas.data).first()
        if user and bcrypt.check_password_hash(user.slaptazodis, form.slaptazodis.data):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Prisijungti nepavyko. Patikrinkite vardą ir slaptažodį', 'danger')
    return render_template("prisijungti.html", form=form)


@app.route("/atsijungti")
def atsijungti():
    logout_user()
    return redirect(url_for('index'))

@app.route("/uzduotys")
@login_required
def uzduotys():
    uzduotys = Uzduotis.query.filter_by(vartotojas=current_user).all()
    return render_template("uzduotys.html", uzduotys=uzduotys)

@app.route("/uzduotys/nauja", methods=['GET', 'POST'])
@login_required
def sukurti_uzduoti():
    form = UzduotisForma()
    if form.validate_on_submit():
        uzduotis = Uzduotis(pavadinimas=form.pavadinimas.data, atlikta=form.atlikta.data, vartotojas_id=current_user.id)
        db.session.add(uzduotis)
        db.session.commit()
        flash('Užduotis sukurta!', 'success')
        return redirect(url_for("uzduotys"))
    return render_template("uzduotis_form.html", form=form)


@app.route('/uzduotys/redaguoti/<int:id>', methods=['GET', 'POST'])
@login_required
def redaguoti_uzduoti(id):
    uzduotis = Uzduotis.query.filter_by(id=id, vartotojas_id=current_user.id).first_or_404()
    form = UzduotisForma(obj=uzduotis)
    if form.validate_on_submit():
        uzduotis.pavadinimas = form.pavadinimas.data
        uzduotis.atlikta = form.atlikta.data
        db.session.commit()
        flash('Užduotis atnaujinta!', 'success')
        return redirect(url_for('uzduotys'))
    return render_template("uzduotis_form.html", form=form)

@app.route('/uzduotys/istrinti/<int:id>', methods=['GET', 'POST'])
@login_required
def istrinti_uzduoti(id):
    uzduotis = Uzduotis.query.filter_by(id=id, vartotojas_id=current_user.id).first_or_404()
    db.session.delete(uzduotis)
    db.session.commit()
    flash('Užduotis ištrinta!', 'success')
    return redirect(url_for('uzduotys'))


def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message("Slaptažodžio atnaujinimo užklausa",
                  sender="el@pastas.lt",
                  recipients=[user.el_pastas])
    msg.body = f'''Norėdami atnaujinti slaptažodį, paspauskite nuorodą:
    {url_for('reset_token', token=token, _external=True)}
    Jei jūs nedarėte šios užklausos, nieko nedarykite ir slaptažodis nebus pakeistas.'''
    print(msg.body)
    # mail.send(msg)


@app.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = SlaptazodzioAtnaujinimoForma()
    user = Vartotojas.verify_reset_token(token)
    if user is None:
        flash("Užklausa netinkama arba pasibaigusio galiojimo", 'warning')
        return redirect(url_for("reset_request"))
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.slaptazodis.data).decode("utf-8")
        user.slaptazodis = hashed_password
        db.session.commit()
        flash("Tavo slaptažodis buvo atnaujintas! Gali prisijungti", "success")
        return redirect(url_for("prisijungti"))
    return render_template("reset_token.html", form=form)


@app.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = UzklausosAtnaujinimoForma()
    if form.validate_on_submit():
        user = Vartotojas.query.filter_by(el_pastas=form.el_pastas.data).first()
        flash("Jums išsiųstas el. laiškas su staptažodžio atnaujinimo instrukcijomis. Jeigu negavote, patikrinkite, ar teisingai įvedėte el. pašto adresą.", "info")
        if user:
            send_reset_email(user)
        return redirect(url_for("prisijungti"))
    return render_template("reset_request.html", form=form)


@app.errorhandler(404)
def klaida_404(klaida):
    return render_template("404.html"), 404


@app.errorhandler(403)
def klaida_403(klaida):
    return render_template("403.html"), 403

@app.errorhandler(500)
def klaida_500(klaida):
    return render_template("500.html"), 500

# paleidimas
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
