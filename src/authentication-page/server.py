import os # to access .env
from flask import Flask, request, render_template, redirect, url_for, flash, jsonify, session
import bcrypt # Hash passwords
import psycopg2 # Connect to fact.check.database
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

#Check if it works

app = Flask(__name__)

app.secret_key = os.environ.get("SECRET_KEY")

limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    storage_uri="redis://localhost:6379/0", # Using redis as backend -> "pip install redis" recommended
    default_limits=["10 per minute"]
)


#ToDo: Designing the "limited" page
@app.route('/limited')
@limiter.limit("10 per minute")
def limited():
    return "This endpoint is rate limited to 10 per minute."


def get_db_connection():
    conn = psycopg2.connect(
        host=os.environ.get("DB_HOST"),
        database=os.environ.get("DB_NAME"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
    )
    return conn


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


def register_user(email, password):
    conn = get_db_connection()
    cur = conn.cursor()

    password = password.encode("utf-8")
    hashed = bcrypt.hashpw(password, bcrypt.gensalt()).decode("utf-8")

    try:
        cur.execute("INSERT INTO users(email, password_hash) VALUES(%s, %s)", (email, hashed))
        conn.commit()
    except psycopg2.Error as e:
        flash(f"Error creating the user. Maybe the user already exists or the email format is wrong? Reason: {e}", "error")
        print(f"[ConsoleLog] Error creating the user. Maybe the user already exists or the email format is wrong? Reason: {e}")
        conn.rollback()
        cur.close()
        conn.close()
        return False
    cur.close()
    conn.close()
    return True


def login_user(email, password):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT password_hash FROM users WHERE email = %s", (email,))
    rows = cur.fetchall()
    conn.close()
    cur.close()

    if not rows:  # No record existing
        return False
    stored_hash = rows[0][0]
    
    try:
        # Ensure stored_hash is bytes for bcrypt.checkpw
        if isinstance(stored_hash, str):
            stored_hash = stored_hash.encode("utf-8")
            
        # Check the password
        if bcrypt.checkpw(password.encode("utf-8"), stored_hash):
            return True
        else:
            return False
    except ValueError as e:
        print(f"Error checking password: {e}")
        return False


@app.route("/login", methods=["POST", "GET"])
def login():
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

#ToDo: Direct transfer of the domain, not with <argument>
@app.route("/get-votes/<argument>", methods=["GET"])
def get_votes(argument):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT domain, path, upvotes, downvotes FROM votable_domains JOIN public.domains d ON d.id = votable_domains.domain_id WHERE domain = %s;",(argument,))
    rows = cur.fetchall()

    if not rows: # If the domain isn't listed yet, create a new entry
        cur.execute("INSERT INTO domains(domain) VALUES (%s);", (argument,))
        rows = cur.execute("SELECT domain, path, upvotes, downvotes FROM votable_domains JOIN public.domains d ON d.id = votable_domains.domain_id WHERE domain = %s;",(argument,))
        # ToDo: Only insert if the domain actually exists (clientsided)

        rows = cur.fetchall()
        conn.commit()
    cur.close()
    conn.close()

    return jsonify(rows)


@app.route("/upvote/<argument>", methods=["GET"])
@limiter.limit("2 per minute")
def upvote_domain(argument):
    # The user has to be logged in to vote
    if session.get('user_id'):
        conn = get_db_connection()
        cur = conn.cursor()

        # ToDo: Add the entry to user_votes and count +1 on table votable_domains
        # cur.execute("UPDATE domains SET upvotes = upvotes + 1 WHERE domain = %s RETURNING upvotes",(argument,))

        updated = cur.fetchone()
        conn.commit()

        cur.close()
        conn.close()

        if updated:
            return jsonify({"domain": argument, "new_upvotes": updated[0]})
        else:
            return jsonify({"error": "Domain not found"}), 404
    else:
        return "You have to be logged in to vote."


@app.route("/downvote/<argument>", methods=["GET"])
@limiter.limit("5 per minute")
def downvote_domain(argument):
    # ToDo:  The user has to be logged in to be able to downvote

    conn = get_db_connection()
    cur = conn.cursor()

    # ToDo: Add the entry to user_votes and count +1 on table votable_domains
    # cur.execute("UPDATE domains SET downvotes = downvotes + 1 WHERE domain = %s RETURNING downvotes",(argument,))
    updated = cur.fetchone()
    conn.commit()

    cur.close()
    conn.close()

    if updated:
        return jsonify({"domain": argument, "new_downvotes": updated[0]})
    else:
        return jsonify({"error": "Domain not found"}), 404

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8085, debug=True)


# More ToDos:
# ToDo: Designing and implementing "Forgot password?"-Page
# ToDo: Designing and implementing "Change password"-Page
# ToDo: Deactivation Account for a certain time when the password is entered wrong multiple times
# ToDo: Using redis or memcached for the flask limiter
# ToDo: Sending a mail with confirmation link when registering

# ToDo when everything works: Migrating to WSGI Server in production environment