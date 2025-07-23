from flask_login import LoginManager, UserMixin, current_user, login_user, logout_user, login_required
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, EqualTo, ValidationError, Email
from flask import Flask, render_template, flash, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
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


# modeliai
class Vartotojas(db.Model, UserMixin):
    __tablename__ = "vartotojas"
    id = db.Column(db.Integer, primary_key=True)
    vardas = db.Column("Vardas", db.String(20), unique=True, nullable=False)
    el_pastas = db.Column("El. pašto adresas", db.String(120), unique=True, nullable=False)
    slaptazodis = db.Column("Slaptažodis", db.String(60), unique=True, nullable=False)


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



@app.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = UzklausosAtnaujinimoForma()
    if form.validate_on_submit():
        user = Vartotojas.query.filter_by(el_pastas=form.el_pastas.data).first()
        # siunčia email
        flash("Jums išsiųstas el. laiškas su staptažodžio atnaujinimo instrukcijomis", "info")
        return redirect(url_for("prisijungti"))
    return render_template("reset_request.html", form=form)


# paleidimas
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
