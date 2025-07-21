from flask_login import LoginManager, UserMixin
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
import os

# inicializavimas
app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'data.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key_here'
db = SQLAlchemy(app)

# login_manager = LoginManager(app)
# login_manager.login_view = "registruotis"
# login_manager.login_message_category = 'info'

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


# paleidimas
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
