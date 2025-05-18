import os # to access .env
from flask import Flask, request, render_template, redirect, url_for, flash, jsonify, session
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from psycopg2.errors import UniqueViolation

from server_functions import get_db_connection, login_user, register_user, extract_domain, subpage_voting_allowed

from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer # creating tokens for the confirmation mail

import bcrypt # Hash passwords
import psycopg2 # Connect to fact.check.database

from dotenv import load_dotenv
load_dotenv()  # Lädt die Datei “.env” aus dem aktuellen Arbeitsverzeichnis

app = Flask(__name__)

app.secret_key = os.environ.get("SECRET_KEY")

allowed_origins = [
    "moz-extension://0ac2c540-7aea-4cd1-bdcb-7ad25e2b8f94"
]

CORS(app, origins=allowed_origins, supports_credentials=True)

serializer = URLSafeTimedSerializer([app.secret_key])

limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    storage_uri="redis://localhost:6379/0", # Using redis as backend; "pip install redis" recommended
    default_limits=["10 per minute"]
)

app.config.update(
    MAIL_SERVER=os.environ.get("MAIL_SERVER"),
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME=os.environ.get("MAIL_USERNAME"),
    MAIL_PASSWORD=os.environ.get("MAIL_PASSWORD"),
    MAIL_DEFAULT_SENDER=os.environ.get("MAIL_DEFAULT_SENDER")
)

mail = Mail(app)

#ToDo: Designing the "limited" page
@app.route('/limited')
@limiter.limit("10 per minute")
def limited():
    flash("You are voting too fast.", "warning")
    return "This endpoint is rate limited to 10 per minute."


@app.route("/")
def index():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("select 1")
        conn.close()
        cur.close()
        db_status = "Database Connected"
        badge_class = "badge-success"
    except Exception as e:
        db_status = "Database not connected"
        badge_class = "badge-danger"
    return render_template("index.html", db_status=db_status, badge_class=badge_class)


#ToDo: Designing the success page
@app.route("/success")
def success():
    return "Success"


@app.route("/register", methods=["POST", "GET"])
def register():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        if register_user(email, password):
            flash("Registration successful. Please log in.", "success")
            return redirect(url_for("success"))
        else:
            flash("Registration failed. Please try again later.", "error")
            return redirect(url_for("register"))
    else:
        return render_template("register.html")



def generate_confirmation_token(email):
    return serializer.dumps(email, salt='email-confirmation-salt')

def confirm_token(token, expiration=3600):
    try:
        email = serializer.loads(
            token,
            salt='email-confirmation-salt',
            max_age=expiration
        )
    except Exception:
        return False
    return email

def send_confirmation_email(user_email):
    token = generate_confirmation_token(user_email)
    confirm_url = url_for('success', token=token, _external=True)
    html = render_template('activate.html', confirm_url=confirm_url)
    msg = Message("Please activate your E-Mail for fact.check", recipients=[user_email], html=html)
    try:
        mail.send(msg)
    except Exception as e:
        print(f"Error sending email: {e}")


@app.route("/login", methods=["POST", "GET"])
def login():
    send_confirmation_email("gutermaxrgbg@gmail.com")

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        # Check login
        if login_user(email, password):
            flash("You successfully logged in.", "success")
            session['user_email'] = email

            conn = get_db_connection()
            cur = conn.cursor()

            #Get the user-id
            cur.execute("SELECT id FROM users WHERE email = %s", (email,))
            rows = cur.fetchall()
            session['user_id'] = int(rows[0][0])
            cur.execute("UPDATE users SET last_login = NOW() WHERE id = %s", (session['user_id'],))
            conn.commit()
            conn.close()
            cur.close()

            print("[TEST] ", session['user_email'], " with id ", session['user_id'], " logged in.")
            return redirect(url_for("success"))
        else:
            flash("Log-in failed. Please try again later.", "error")
            return redirect(url_for("login"))
    else:
        if session.get('user_id'):
            return "You are already logged in as " + session['user_email']
        return render_template("login.html")


@app.route("/logout")
def logout():
    if session.get('user_id'):
        session.clear()
        return "You are successfully logged out."
    else:
        return "You are not currently logged in."


@app.route("/get-votes", methods=["GET"])
def get_votes():
    url = request.args.get('url') # Get url

    if not url:
        print("URL parameter missing")
        return jsonify({"error": "URL parameter is missing"}), 400

    conn = get_db_connection()
    cur = conn.cursor()

    hostname, path = extract_domain(url)

    if url[:8] == "https://": # Checks if the domain exists; only https domains are supported
        if subpage_voting_allowed(hostname): # Subpage Voting allowed --> Search for votings for the specific path
            cur.execute("SELECT domain, path, upvotes, downvotes FROM domains d JOIN votable_domains v ON d.id = v.domain_id WHERE domain = %s AND path = %s", (hostname, path))
            rows = cur.fetchall()
            if not rows:
                cur.execute("SELECT id FROM domains WHERE domain = %s", (hostname,))
                domain_id = cur.fetchall()[0][0]
                cur.execute("INSERT INTO public.votable_domains (entity_id, domain_id, path, upvotes, downvotes, voting_allowed) VALUES (DEFAULT, %s, %s, DEFAULT, DEFAULT, DEFAULT)", (domain_id, path))
                conn.commit()

                cur.close()
                conn.close()
                return jsonify([hostname, path, 0, 0]) # No votes if the domain didn't exist yet

        else: # Subpage voting not allowed
            url = hostname
            cur.execute(
                "SELECT domain, path, upvotes, downvotes FROM votable_domains JOIN public.domains d ON d.id = votable_domains.domain_id WHERE domain = %s;", (url,))
            rows = cur.fetchall()

            if not rows: # If the domain isn't listed yet, create a new entry
                cur.execute("INSERT INTO domains(domain) VALUES (%s);", (url,))
                rows = cur.execute("SELECT domain, path, upvotes, downvotes FROM votable_domains JOIN public.domains d ON d.id = votable_domains.domain_id WHERE domain = %s;",(url,)) # default up-/and downvotes: 0

                rows = cur.fetchall()
                conn.commit()
        cur.close()
        conn.close()
        return jsonify(rows)
    cur.close()
    conn.close()
    flash("Domain not supported.", "Not supported")
    return jsonify([0, 0, 0, 0]) # Not supported? -> Empty Array


@app.route("/vote/<argument>", methods=["GET"])
@limiter.limit("10 per minute")
def upvote_domain(argument):
    # The user has to be logged in to vote
    if session.get('user_id'):
        conn = get_db_connection()
        cur = conn.cursor()

        url = request.args.get('url') # Get url
        try:
            hostname, path = extract_domain(url)
        except ValueError as e:
            return jsonify({"error": "Domain not supported."}), 404

        if argument != "up" and argument != "down":
            return jsonify({"error": "Site not found."}), 404

        if subpage_voting_allowed(hostname):
            try:
                if argument == 'up':
                    cur.execute( # Count the vote (+1)
                        "UPDATE votable_domains v SET upvotes = upvotes + 1 FROM domains d WHERE v.domain_id = d.id AND d.domain = %s AND v.path = %s RETURNING entity_id, upvotes, downvotes;",
                        (hostname,path,))
                else:
                    cur.execute(  # Count the vote (+1)
                        "UPDATE votable_domains v SET downvotes = downvotes + 1 FROM domains d WHERE v.domain_id = d.id AND d.domain = %s AND v.path = %s RETURNING entity_id, upvotes, downvotes;",
                        (hostname, path,))
                returned = cur.fetchall()
                entity_id = returned[0][0]
                updated_upvotes = returned[0][1]
                updated_downvotes = returned[0][2]
                cur.execute("INSERT INTO user_votes(user_id, entity_id, vote_value) VALUES (%s, %s, True);",
                            (session.get('user_id'), entity_id)) # Add it to the user_votes
            except UniqueViolation as e:
                flash("The user already voted.", "error")
                conn.rollback()
                cur.execute(
                    "SELECT domain, path, upvotes, downvotes FROM domains d JOIN votable_domains v ON d.id = v.domain_id WHERE domain = %s AND path = %s",
                    (hostname, path))
                updated_upvotes, updated_downvotes = cur.fetchall()
            else:
                conn.commit()
                flash("Voting successful.", "success")
        else:
            try:
                if argument == 'up':
                    cur.execute( # Count the vote (+1)
                        "UPDATE votable_domains v SET upvotes = upvotes + 1 FROM domains d WHERE v.domain_id = d.id AND d.domain = %s RETURNING entity_id, upvotes, downvotes;",
                        (hostname,))
                else:
                    cur.execute(  # Count the vote (+1)
                        "UPDATE votable_domains v SET downvotes = downvotes + 1 FROM domains d WHERE v.domain_id = d.id AND d.domain = %s RETURNING entity_id, upvotes, downvotes;",
                        (hostname,))
                returned = cur.fetchall()
                entity_id = returned[0][0]
                updated_upvotes = returned[0][1]
                updated_downvotes = returned[0][2]
                cur.execute("INSERT INTO user_votes(user_id, entity_id, vote_value) VALUES (%s, %s, True);", # Add the vote to user_votes
                            (session.get('user_id'), entity_id))  # Add it to the user_votes
            except UniqueViolation as e:
                flash("The user already voted.", "error")
                cur.execute(
                    "SELECT domain, path, upvotes, downvotes FROM votable_domains JOIN public.domains d ON d.id = votable_domains.domain_id WHERE domain = %s;",
                    (url,))
                updated_upvotes, updated_downvotes = cur.fetchall()
                conn.rollback()
            else:
                conn.commit()
                flash("Voting successful.", "success")

        conn.commit()

        cur.close()
        conn.close()


        return jsonify([hostname, path, updated_upvotes, updated_downvotes])
        # return jsonify({"error": "Domain not found"}), 404

    else:
        flash("You have to be logged in to vote.", "Not logged in.")
        return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8085, debug=True)

# More ToDos:

# ToDo: Deactivate Account for a certain time when the password is entered wrong multiple times
# ToDo: Sending a mail with confirmation link when registering

# Less important
# ToDo: Designing and implementing "Forgot password?"-Page
# ToDo: Designing and implementing "Change password"-Page

# When everything works: ToDo: Migrating to WSGI Server in production environment