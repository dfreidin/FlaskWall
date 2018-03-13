from flask import Flask, render_template, request, redirect, session, flash
from mysqlconnection import MySQLConnector
import md5
import os, binascii
import re
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$')
NAME_REGEX = re.compile(r'^[a-zA-Z-]+$')
app = Flask(__name__)
app.secret_key = "swordfish"
mysql = MySQLConnector(app, "wall")
@app.route('/')
def index():
    return render_template('index.html')
@app.route("/register", methods=["POST"])
def register():
    fn = request.form["first_name"]
    ln = request.form["last_name"]
    em = request.form["email"]
    pw = request.form["password"]
    pc = request.form["confirm_password"]
    valid = True
    if len(fn) < 2:
        flash("Must be at least 2 characters", "first_name")
        valid = False
    if not NAME_REGEX.match(fn):
        flash("Must be letters only", "first_name")
        valid = False
    if len(ln) < 2:
        flash("Must be at least 2 characters", "last_name")
        valid = False
    if not NAME_REGEX.match(ln):
        flash("Must be letters only", "last_name")
        valid = False
    if not EMAIL_REGEX.match(em):
        flash("Not a valid email address", "email")
        valid = False
    if len(pw) < 8:
        flash("Password must be at least 8 characters", "password")
        valid = False
    if pw != pc:
        flash("Password does not match", "confirm_password")
        valid = False
    if not valid:
        return redirect("/")
    salt = binascii.b2a_hex(os.urandom(15))
    hashed_pw = md5.new(pw + salt).hexdigest()
    query = "INSERT INTO users (first_name, last_name, email, password, salt, created_at, updated_at) VALUES(:fn, :ln, :em, :pw, :salt, NOW(), NOW());"
    query_data = {"fn": fn, "ln": ln, "em": em, "pw": hashed_pw, "salt": salt}
    mysql.query_db(query, query_data)
    query = "SELECT id FROM users WHERE email = :em;"
    query_data = {"em": em}
    row = mysql.query_db(query, query_data)
    session["user_id"] = row[0]["id"]
    return redirect("/wall")
@app.route("/login", methods=["POST"])
def login():
    em = request.form["email"]
    pw = request.form["password"]
    if not EMAIL_REGEX.match(em):
        flash("Not a valid email address", "login")
        return redirect("/")
    query = "SELECT id, password, salt FROM users WHERE email = :em;"
    query_data = {"em": em}
    user_data = mysql.query_db(query, query_data)
    if len(user_data) != 0 and user_data[0]["password"] == md5.new(pw + user_data[0]["salt"]).hexdigest():
        session["user_id"] = user_data[0]["id"]
        return redirect("/wall")
    else:
        flash("Login failed", "login")
        return redirect("/")
@app.route("/logout")
def logout():
    session.pop("user_id")
    return redirect("/")
@app.route("/wall")
def wall():
    if not session.get("user_id"):
        flash("Not logged in", "login")
        return redirect("/")
    query = "SELECT CONCAT(users.first_name, ' ', users.last_name) AS poster_name FROM users WHERE users.id = :user_id"
    query_data = {"user_id": session["user_id"]}
    username = mysql.query_db(query, query_data)
    query = "SELECT messages.id AS message_id, CONCAT(users.first_name, ' ', users.last_name) AS poster_name, DATE_FORMAT(messages.created_at, '%b %D %Y') AS post_date, messages.message FROM users JOIN messages ON users.id = messages.user_id;"
    messages = mysql.query_db(query)
    wall = []
    for i in range(len(messages)):
        wall.append({"message":messages[i]})
        query = "SELECT CONCAT(users.first_name, ' ', users.last_name) AS poster_name, DATE_FORMAT(comments.created_at, '%b %D %Y') AS post_date, comments.comment FROM users JOIN comments ON users.id = comments.user_id JOIN messages ON comments.message_id = messages.id WHERE messages.id = :message_id;"
        query_data = {"message_id": messages[i]["message_id"]}
        comments = mysql.query_db(query, query_data)
        wall[i]["comments"] = comments
    wall.reverse()
    return render_template("wall.html", name=username[0]["poster_name"], posts=wall)
@app.route("/message", methods=["POST"])
def message():
    if not session.get("user_id"):
        flash("Not logged in", "login")
        return redirect("/")
    content = request.form["content"]
    query = "INSERT INTO messages (message, user_id, created_at, updated_at) VALUES(:message, :user_id, NOW(), NOW());"
    query_data = {"message": content, "user_id": session["user_id"]}
    mysql.query_db(query, query_data)
    return redirect("/wall")
@app.route("/comment", methods=["POST"])
def comment():
    if not session.get("user_id"):
        flash("Not logged in", "login")
        return redirect("/")
    content = request.form["content"]
    message_id = request.form["message_id"]
    query = "INSERT INTO comments (comment, user_id, message_id, created_at, updated_at) VALUES(:comment, :user_id, :message_id, NOW(), NOW());"
    query_data = {"comment": content, "user_id": session["user_id"], "message_id": message_id}
    mysql.query_db(query, query_data)
    return redirect("/wall")
app.run(debug=True)