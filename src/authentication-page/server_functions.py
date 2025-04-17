import os # to access .env
import psycopg2 # Connect to fact.check.database
import bcrypt # Hash passwords
from flask import flash

from urllib.parse import urlparse # To work with domains
from tld import get_fld, get_tld # To get all current Top-Level-Domains


def get_db_connection():
    conn = psycopg2.connect(
        host=os.environ.get("DB_HOST"),
        database=os.environ.get("DB_NAME"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
    )
    return conn


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


def extract_domain(domain):
    if domain[:8] == "https://": # Checks if the domain exists
        domain = domain[8:]  # Delete the https:// before

    hostname = get_fld(domain, fail_silently=True, fix_protocol=True)

    path = domain.split('/', 1)[1]  # Only the first subpath is supported e.g. youtube.com/@username; everything beyond that will be cut off
    if path.count('/'):
        path = path.split('/', 1)[0]

    return hostname, path

def subpage_voting_allowed(hostname):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT allow_subpage_voting FROM votable_domains JOIN public.domains d ON d.id = votable_domains.domain_id WHERE domain = %s;",(hostname,))
    allow_subpage_voting = cur.fetchall()
    if not allow_subpage_voting:
        allow_subpage_voting = [[False]]

    if allow_subpage_voting[0][0]:
        return True
    else:
        return False