from flask import Flask,request,render_template_string,render_template,redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from numpy import log as Ln
from numpy import exp as e
import random
from flask_mail import Mail, Message

app=Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI']='sqlite:///todo.db'
db =SQLAlchemy(app)

class LoginTable(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(80), nullable=False, unique=True) 
    password = db.Column(db.VARCHAR(8), nullable=False,) 
    
with app.app_context():
    db.create_all()

def calcul_diffusion(Xa, T, aBA, aAB, rA, rB, qA, qB, lambda_A, lambda_B, D_AB, D_BA, V_exp):
    if 0 <= Xa <= 1 and T > 0:
        Xb = 1 - Xa
        phiA = (Xa * lambda_A) / (Xa * lambda_A + Xb * lambda_B)
        phiB = (Xb * lambda_B) / (Xa * lambda_A + Xb * lambda_B)
        tauxAB, tauxBA = e(-aAB / T), e(-aBA / T)
        tetaA = (Xa * qA) / (Xa * qA + Xb * qB)
        tetaB = (Xb * qB) / (Xa * qA + Xb * qB)
        tetaAA = tetaA / (tetaA + tetaB * tauxBA)
        tetaBB = tetaB / (tetaB + tetaA * tauxAB)
        tetaAB = (tetaA * tauxAB) / (tetaA * tauxAB + tetaB)
        tetaBA = (tetaB * tauxBA) / (tetaB * tauxBA + tetaA)

        première_terme = Xb * Ln(D_AB) + Xa * Ln(D_BA) + 2 * (Xa * Ln(Xa / phiA) + Xb * Ln(Xb / phiB))
        deuxième_terme = 2 * Xb * Xa * ((phiA / Xa) * (1 - (lambda_A / lambda_B)) + (phiB / Xb) * (1 - (lambda_B / lambda_A)))
        troisième_terme = Xb * qA * ((1 - (tetaBA) ** 2) * Ln(tauxBA) + (1 - (tetaBB) ** 2) * tauxAB * Ln(tauxAB))
        quatrième_terme = Xa * qB * ((1 - (tetaAB) ** 2) * Ln(tauxAB) + (1 - (tetaAA) ** 2) * tauxBA * Ln(tauxBA))

        solution1 = première_terme + deuxième_terme + troisième_terme + quatrième_terme
        solution2 = e(solution1)
        erreur = (abs(solution2 - V_exp) / V_exp) * 100
        return solution1, solution2, erreur, Xb, phiA, phiB, tauxAB, tauxBA, tetaA, tetaB, tetaAA, tetaBB, tetaAB, tetaBA
    else:
        return None, None, None, None, None, None, None, None, None, None, None, None, None, None



@app.route("/calcul", methods=["GET", "POST"])
def calcul():
    # 🔒 Vérification de connexion
    if 'user' not in session:
        return redirect(url_for('login'))  # Redirige vers la page de login
    result = ""
    detail = ""
    if request.method == "POST":
        try:
            V_exp = float(request.form["V_exp"])
            Xa = float(request.form["Xa"])
            T = float(request.form["T"])
            aBA = float(request.form["aBA"])
            aAB = float(request.form["aAB"])
            rA = float(request.form["rA"])
            rB = float(request.form["rB"])
            qA = float(request.form["qA"])
            qB = float(request.form["qB"])
            lambda_A = float(request.form["lambda_A"])
            lambda_B = float(request.form["lambda_B"])
            D_AB = float(request.form["D_AB"])
            D_BA = float(request.form["D_BA"])
            
            lnDab, Dab, erreur, Xb, phiA, phiB, tauxAB, tauxBA, tetaA, tetaB, tetaAA, tetaBB, tetaAB, tetaBA = calcul_diffusion(Xa, T, aBA, aAB, rA, rB, qA, qB, lambda_A, lambda_B, D_AB, D_BA, V_exp)
            if Dab is not None:
                result = f"""
                    <p><strong>Dab :</strong> {Dab:.5e}</p>
                    <p><strong>Erreur :</strong> {erreur:.2f} %</p>
                """
                detail = f"""
                        <p style="position: relative"><strong>Xb :</strong> {Xb:.5f}</p>
                        <p style="position: relative"><strong>phiA :</strong> {phiA:.5f} </p>
                        <p style="position: relative"><strong>phiB :</strong> {phiB:.5f}</p>
                        <p style="position: relative"><strong>tauxAB :</strong> {tauxAB:.5f} </p>
                        <p style="position: relative"><strong>tauxBA :</strong> {tauxBA:.5f}</p>
                        <p style="position: relative"><strong>tetaA:</strong> {tetaA:.5f} </p>
                        <p style="position: relative"><strong>tetaB :</strong> {tetaB:.5f}</p>
                        <p style="position: relative"><strong>tetaAA :</strong> {tetaAA:.5f} </p>
                        <p style="position: relative"><strong>tetaBB :</strong> {tetaBB:.5f}</p>
                        <p style="position: relative"><strong>tetaAB :</strong> {tetaAB:.5f} </p>
                        <p style="position: relative"><strong>tetaBA :</strong> {tetaBA:.5f}</p>
                       """
            else:
                result = "<p style='color:red;'>Les valeurs de Xa ou T ne sont pas correctes.</p>"
        except ValueError:
            result = "<p style='color:red;'>Veuillez entrer des valeurs numériques valides.</p>"
    return render_template("app_calcul.html", result=result, detail=detail)

@app.route("/")
def home():
    return redirect(url_for("login")) 

@app.route("/logout")
def logout():
    session.clear()  # ou session.pop('user', None) selon ta logique
    return redirect(url_for("login"))  # rediriger vers la page de login

@app.route("/login", methods=["GET", "POST"])
def login():
    message = ""
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user = LoginTable.query.filter_by(email=email, password=password).first()
        if user:
            message = "<p style='color:green;'>Connexion réussie !</p>"
            return render_template("app_interface.html")
        else:
            message = "<p style='color:red;'>Identifiants incorrects.</p>"
    
    return render_template("app_login.html", message=message)

@app.errorhandler(404)
def not_found_error(error):
    return render_template('erreur.html'), 404


@app.errorhandler(500)
def internal_error(error):
    return render_template('erreur.html'), 500

@app.route("/interface")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))  
    return render_template("app_interface.html")



@app.route("/returne_to_interface")
def interface():
    return render_template("app_interface.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    message = ""
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        existing_user = LoginTable.query.filter_by(email=email).first()
        if existing_user:
            message = "<p style='color:red;'>Cet email est déjà utilisé.</p>"
        else:
            new_user = LoginTable(email=email, password=password)
            db.session.add(new_user)
            db.session.commit()
            message = "<p style='color:green;'>Inscription réussie !</p>"
    
    return render_template("app_register.html", message=message)

app.secret_key = 'cle_secrete'  # Nécessaire pour flash()

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///login.db'  
app.config['SECRET_KEY'] = 'votre_cle_secrete'
app.config['MAIL_SERVER'] = 'smtp.gmail.com'  
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'elboujgaming@gmail.com'
app.config['MAIL_PASSWORD'] = 'tzbi ymrf kgjz hmxk' 

mail = Mail(app)



@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        email = request.form['email']
        user = LoginTable.query.filter_by(email=email).first()
        
        if user:
            reset_code = str(random.randint(100000, 999999))
            user.password = reset_code  
            db.session.commit()

           
            msg = Message('Code de récupération de mot de passe', sender='elboujgaming@gmail.com', recipients=[user.email])
            msg.body = f'Votre code de récupération est: {reset_code}'
            mail.send(msg)

            flash('Un code de récupération a été envoyé à votre email.', 'success')
            return redirect(url_for('verify_code'))

        flash('Aucun utilisateur trouvé avec cet email.', 'error')

    return render_template('reset_password.html')


@app.route('/verify-code', methods=['GET', 'POST'])
def verify_code():
    if request.method == 'POST':
        email = request.form['email']
        reset_code = request.form['reset_code']
        new_password = request.form['new_password']
        user = LoginTable.query.filter_by(email=email).first()

        if user and reset_code == user.password: 
            user.password = new_password 
            db.session.commit()
            flash('Mot de passe réinitialisé avec succès.', 'success')
            return redirect(url_for('login'))  
        else:
            flash('Code invalide.', 'error')

    return render_template('verify_code.html')

if __name__ == "__main__":
    app.run(debug=True)