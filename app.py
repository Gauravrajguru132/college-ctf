from flask import Flask, render_template, request, redirect, url_for, session, flash, g
import sqlite3
import hashlib
import os
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = "college-ctf-secret-change-me-in-production-2026"

DATABASE = "ctf.db"

def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                is_admin INTEGER DEFAULT 0,
                score INTEGER DEFAULT 0,
                created_at TEXT
            );

            CREATE TABLE IF NOT EXISTS challenges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                points INTEGER NOT NULL,
                flag TEXT NOT NULL,
                difficulty TEXT DEFAULT 'Easy',
                hint TEXT,
                is_visible INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS solves (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                challenge_id INTEGER NOT NULL,
                solved_at TEXT,
                UNIQUE(user_id, challenge_id),
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(challenge_id) REFERENCES challenges(id)
            );
        """)
        db.commit()

        # Create default admin (username: admin, password: admin123)
        admin_pass = hashlib.sha256("admin123".encode()).hexdigest()
        try:
            db.execute(
                "INSERT INTO users (username, password, is_admin, score, created_at) VALUES (?, ?, 1, 0, ?)",
                ("admin", admin_pass, datetime.now().isoformat())
            )
            db.commit()
        except sqlite3.IntegrityError:
            pass  # admin already exists

        # Insert sample beginner challenges (28 total)
        challenges = [
            # ===== ORIGINAL 8 =====
            (
                "Welcome to the CTF!",
                "General",
                "Welcome to our college CTF!\n\nThe flag is: flag{welcome_to_college_ctf_2026}\n\nJust submit it to get your first points.",
                10,
                "flag{welcome_to_college_ctf_2026}",
                "Easy",
                "The flag is already written in the description!"
            ),
            (
                "Base64 Basics",
                "Crypto",
                "Someone encoded a secret message using Base64.\n\nDecode this: ZmxhZ3tiYXNlNjRfaXNfZWFzeX0=\n\nTools: Use CyberChef, or Python (base64 module), or any online Base64 decoder.",
                20,
                "flag{base64_is_easy}",
                "Easy",
                "Search for 'base64 decode online' or use Python: import base64; print(base64.b64decode('...'))"
            ),
            (
                "Inspect Me",
                "Web",
                "The flag is hidden somewhere on this page.\n\nLook carefully at the HTML source code (Right click → View Page Source or Ctrl+U).\n\nHint: Developers love to leave comments.",
                30,
                "flag{html_comments_are_useful}",
                "Easy",
                "Right-click the page → View Page Source. Look for HTML comments (<!-- ... -->)."
            ),
            (
                "Caesar Salad",
                "Crypto",
                "Julius Caesar used a simple cipher. Shift every letter by 3 positions backwards.\n\nCiphertext: iodj{fdhvdu_flskhu_lv_ixq}\n\nExample: d → a, e → b, f → c ...",
                30,
                "flag{caesar_cipher_is_fun}",
                "Easy",
                "Try shifting each letter back by 3. Or use CyberChef 'ROT13' / 'Caesar' recipe."
            ),
            (
                "Hidden in Plain Sight",
                "Forensics",
                "Download the file below and find the flag.\n\n(This challenge uses a text file. In a real CTF you would get an image or binary.)\n\nFile content is shown here for simplicity:\n\nThis is a normal looking text file.\nNothing suspicious here...\nJust some random words: apple banana cherry\nOh wait... flag{strings_command_rocks} is hidden between the lines.\nKeep looking!",
                40,
                "flag{strings_command_rocks}",
                "Easy",
                "Just read the description carefully. The flag is written in plain text."
            ),
            (
                "Simple XOR",
                "Crypto",
                "The message was XORed with a single-byte key.\n\nHex ciphertext: 0a0d0a1d1b0c1a0b1c0d1b0a1d0c1b0a\n\nThe key is a single printable ASCII character (try letters a-z).\n\nPython tip:\n```python\ncipher = bytes.fromhex('0a0d0a1d1b0c1a0b1c0d1b0a1d0c1b0a')\nfor key in range(32, 127):\n    print(key, bytes([b ^ key for b in cipher]))\n```",
                50,
                "flag{xor_is_cool}",
                "Medium",
                "XOR each byte with possible keys (32-126). Look for readable text starting with 'flag{'."
            ),
            (
                "Cookie Monster",
                "Web",
                "This challenge simulates a web cookie.\n\nImagine you have a cookie named 'role' with value 'user'.\n\nChange it to 'admin' to get the flag.\n\n(In a real challenge this would be done in browser DevTools → Application → Cookies)\n\nFor this demo, the flag is: flag{cookies_can_be_changed}",
                40,
                "flag{cookies_can_be_changed}",
                "Easy",
                "In real life: F12 → Application/Storage → Cookies. Change the value."
            ),
            (
                "Google Fu",
                "OSINT",
                "Use your search skills.\n\nWhat is the full name of the creator of Python programming language?\n\nFormat the flag as: flag{firstname_lastname} (all lowercase)\n\nExample: flag{john_doe}",
                25,
                "flag{guido_van_rossum}",
                "Easy",
                "Just Google 'creator of Python programming language'."
            ),
            # ===== 20 NEW CHALLENGES =====
            (
                "ROT13 Fun",
                "Crypto",
                "ROT13 is a special case of the Caesar cipher (shift by 13).\n\nCiphertext: synt{ebg13_vf_fvzcyr}\n\nDecode it to get the flag.",
                25,
                "flag{rot13_is_simple}",
                "Easy",
                "Use CyberChef or any online ROT13 decoder. In Python: import codecs; print(codecs.decode(text, 'rot_13'))"
            ),
            (
                "Binary Message",
                "Crypto",
                "Convert this binary to ASCII text:\n\n01100110 01101100 01100001 01100111 01111011 01100010 01101001 01101110 01100001 01110010 01111001 01011111 01101001 01110011 01011111 01100110 01110101 01101110 01111101",
                30,
                "flag{binary_is_fun}",
                "Easy",
                "Use CyberChef (From Binary) or an online binary-to-text converter."
            ),
            (
                "Secret in the Source",
                "Web",
                "The flag is hidden in this page's HTML source code.\n\nRight-click → View Page Source (or press Ctrl+U) and search carefully.\n\n<!-- flag{developers_leave_secrets} -->",
                35,
                "flag{developers_leave_secrets}",
                "Easy",
                "Look for HTML comments that start with <!--"
            ),
            (
                "Broken Hash",
                "Crypto",
                "This is an MD5 hash of the flag:\n\n5f4dcc3b5aa765d61d8327deb882cf99\n\nWait... that's the MD5 of the word \"password\".\n\nActually the real hash of the flag is:\n\n8f4e3c2b1a0d9e8f7c6b5a4d3e2f1a0b\n\nNo, that was a joke.\n\nThe real flag is simply: flag{md5_is_broken}",
                40,
                "flag{md5_is_broken}",
                "Easy",
                "Read the description carefully till the end."
            ),
            (
                "Hexadecimal",
                "Crypto",
                "Decode this hexadecimal string:\n\n666c61677b6865785f6465636f64696e675f726f636b737d",
                30,
                "flag{hex_decoding_rocks}",
                "Easy",
                "Use CyberChef (From Hex) or Python: bytes.fromhex('...').decode()"
            ),
            (
                "Fake QR",
                "Misc",
                "In a real CTF you would scan a QR code.\n\nFor this challenge, the \"QR content\" is:\n\nflag{qr_codes_are_cool}\n\nJust submit it!",
                20,
                "flag{qr_codes_are_cool}",
                "Easy",
                "The flag is written in the description."
            ),
            (
                "robots.txt",
                "Web",
                "Websites often have a file called robots.txt that tells search engines which pages not to visit.\n\nSometimes they accidentally reveal secret paths.\n\nImagine robots.txt contains:\n\nUser-agent: *\nDisallow: /secret-admin-panel\nDisallow: /flag-here.txt\n\nAnd /flag-here.txt contains the flag: flag{robots_tell_secrets}",
                45,
                "flag{robots_tell_secrets}",
                "Easy",
                "In real life you would visit http://target/robots.txt"
            ),
            (
                "Hidden Message",
                "Forensics",
                "Steganography is the art of hiding data inside other data (usually images).\n\nFor this beginner challenge, the hidden message is written below in plain text:\n\nThe password is flag{stego_basics}",
                40,
                "flag{stego_basics}",
                "Easy",
                "Just read the description."
            ),
            (
                "Dangerous Eval",
                "Misc",
                "A developer wrote this dangerous Python code:\n\ncode = input(\"Enter expression: \")\nprint(eval(code))\n\nWhat could go wrong?\n\nAnyway, the flag is: flag{never_use_eval}",
                50,
                "flag{never_use_eval}",
                "Medium",
                "The flag is in the description. In real challenges this would be a remote code execution challenge."
            ),
            (
                "Base32 Encoding",
                "Crypto",
                "This time the message is encoded with Base32:\n\nMZXW6YTBONSXE43FOMQHI2DFON2GS4ZAMFRGG===\n\nDecode it.",
                35,
                "flag{base32_works_too}",
                "Easy",
                "Use CyberChef (From Base32) or Python: import base64; print(base64.b32decode('...'))"
            ),
            (
                "URL Encoding",
                "Web",
                "Sometimes data is URL-encoded.\n\nDecode this:\n\nflag%7Burl_encoding_is_easy%7D",
                25,
                "flag{url_encoding_is_easy}",
                "Easy",
                "Use CyberChef (URL Decode) or any online URL decoder. %7B = { and %7D = }"
            ),
            (
                "Morse Code",
                "Crypto",
                "Decode this Morse code:\n\n..-. .-.. .- --. { -- --- .-. ... . _ .. ... _ ..-. ..- -. }",
                30,
                "flag{morse_is_fun}",
                "Easy",
                "Use CyberChef or any online Morse code decoder. . = short, - = long"
            ),
            (
                "Reverse Me",
                "Misc",
                "Someone wrote the flag backwards.\n\n}nuF_sI_esreveR{galf\n\nReverse it to get the real flag.",
                20,
                "flag{Reverse_Is_Fun}",
                "Easy",
                "Just reverse the string character by character."
            ),
            (
                "ASCII Codes",
                "Crypto",
                "These are ASCII codes of the flag characters:\n\n102 108 97 103 123 97 115 99 105 105 95 99 111 100 101 115 125",
                35,
                "flag{ascii_codes}",
                "Easy",
                "Convert each number to its ASCII character. 102 = f, 108 = l, etc."
            ),
            (
                "Password Strength",
                "Misc",
                "A weak password was used: password123\n\nBut the flag is not that.\n\nThe flag is: flag{strong_passwords_matter}",
                15,
                "flag{strong_passwords_matter}",
                "Easy",
                "Read the last line of the description."
            ),
            (
                "JWT Intro",
                "Web",
                "JSON Web Tokens (JWT) are used for authentication.\n\nA JWT has 3 parts separated by dots: header.payload.signature\n\nHere is a sample JWT header (Base64):\n\neyJhbGciOiJub25lIn0\n\nDecode it. The flag is: flag{jwt_none_algorithm}",
                45,
                "flag{jwt_none_algorithm}",
                "Medium",
                "Decode the Base64 header. The 'none' algorithm is dangerous."
            ),
            (
                "File Extension",
                "Forensics",
                "A file was renamed from .txt to .jpg to hide it.\n\nIn real life you would use the 'file' command or look at magic bytes.\n\nFor this challenge the flag is: flag{magic_bytes_matter}",
                30,
                "flag{magic_bytes_matter}",
                "Easy",
                "The flag is in the description. Real tip: never trust file extensions."
            ),
            (
                "SQL Injection Intro",
                "Web",
                "A login form is vulnerable to SQL Injection.\n\nThe query looks like:\nSELECT * FROM users WHERE username = 'INPUT' AND password = 'INPUT'\n\nWhat if you enter: ' OR 1=1 --\n\nAnyway the flag for this intro is: flag{sqli_is_dangerous}",
                50,
                "flag{sqli_is_dangerous}",
                "Medium",
                "The flag is written in the description. Real SQLi can bypass logins."
            ),
            (
                "Linux Basics",
                "Misc",
                "On Linux, the command to list files is 'ls'.\n\nThe command to print a file is 'cat'.\n\nThe flag is hidden in this sentence: flag{linux_commands_are_useful}",
                20,
                "flag{linux_commands_are_useful}",
                "Easy",
                "Just read the description carefully."
            ),
            (
                "Base64 Double",
                "Crypto",
                "This message was Base64 encoded twice.\n\nWVhOa1lYTmtaV052Ym5SbGNqST0=\n\nDecode it twice to get the flag.",
                40,
                "flag{double_base64}",
                "Medium",
                "Decode once, then decode the result again with Base64."
            ),
            (
                "Pigpen Cipher",
                "Crypto",
                "The Pigpen cipher uses symbols instead of letters.\n\nFor this beginner version we just tell you the flag:\n\nflag{pigpen_is_old_school}",
                25,
                "flag{pigpen_is_old_school}",
                "Easy",
                "The flag is written plainly. Real Pigpen looks like tic-tac-toe grids."
            ),
            (
                "User-Agent",
                "Web",
                "Websites can see your User-Agent header (browser name).\n\nSometimes they show different content based on it.\n\nFor this challenge the flag is: flag{user_agent_matters}",
                30,
                "flag{user_agent_matters}",
                "Easy",
                "In real life you change User-Agent with browser extensions or curl -A"
            ),
            (
                "Whitespace",
                "Forensics",
                "Sometimes flags are hidden with extra spaces or tabs.\n\nLook carefully between these words:\n\nflag { whitespace _ is _ sneaky }\n\nRemove the spaces to get: flag{whitespace_is_sneaky}",
                35,
                "flag{whitespace_is_sneaky}",
                "Easy",
                "Remove the spaces inside the curly braces."
            ),
            (
                "Year of Python",
                "OSINT",
                "In which year was the first version of Python released?\n\nFormat the flag as: flag{YYYY}\n\nExample: flag{1990}",
                30,
                "flag{1991}",
                "Easy",
                "Google 'when was python first released' or 'python history'."
            ),
            (
                "Atbash Cipher",
                "Crypto",
                "Atbash cipher reverses the alphabet (A↔Z, B↔Y, C↔X...).\n\nCiphertext: uozt{zgyzhs_xrkovi}\n\nDecode it.",
                35,
                "flag{atbash_cipher}",
                "Easy",
                "A becomes Z, B becomes Y, etc. Or use CyberChef Atbash."
            ),
            (
                "Comment in Code",
                "Misc",
                "Developers often leave comments in code.\n\n# TODO: remove this before production\n# flag{check_the_comments}\n\nprint('Hello World')",
                20,
                "flag{check_the_comments}",
                "Easy",
                "Look at the comments in the code snippet."
            ),
            (
                "HTTP Status",
                "Web",
                "HTTP status code 404 means 'Not Found'.\n\nStatus 200 means 'OK'.\n\nStatus 403 means 'Forbidden'.\n\nThe flag is: flag{know_your_status_codes}",
                25,
                "flag{know_your_status_codes}",
                "Easy",
                "The flag is in the description."
            ),
            (
                "Final Boss",
                "General",
                "Congratulations on reaching the last challenge!\n\nYou have learned the basics of CTFs.\n\nYour final flag is: flag{you_are_ready_for_real_ctfs}",
                100,
                "flag{you_are_ready_for_real_ctfs}",
                "Easy",
                "Just submit the flag written above."
            ),
        ]

        for c in challenges:
            try:
                db.execute(
                    "INSERT INTO challenges (title, category, description, points, flag, difficulty, hint) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    c
                )
            except:
                pass
        db.commit()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login first.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login first.", "warning")
            return redirect(url_for("login"))
        db = get_db()
        user = db.execute("SELECT is_admin FROM users WHERE id = ?", (session["user_id"],)).fetchone()
        if not user or not user["is_admin"]:
            flash("Admin access required.", "danger")
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        if not username or not password:
            flash("Username and password are required.", "danger")
            return redirect(url_for("register"))
        if password != confirm:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("register"))
        if len(username) < 3:
            flash("Username must be at least 3 characters.", "danger")
            return redirect(url_for("register"))

        db = get_db()
        try:
            db.execute(
                "INSERT INTO users (username, password, created_at) VALUES (?, ?, ?)",
                (username, hash_password(password), datetime.now().isoformat())
            )
            db.commit()
            flash("Registration successful! Please login.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Username already exists.", "danger")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username = ? AND password = ?",
            (username, hash_password(password))
        ).fetchone()
        if user:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["is_admin"] = bool(user["is_admin"])
            flash(f"Welcome, {user['username']}!", "success")
            return redirect(url_for("challenges"))
        flash("Invalid username or password.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("index"))

@app.route("/challenges")
@login_required
def challenges():
    db = get_db()
    challenges = db.execute(
        "SELECT * FROM challenges WHERE is_visible = 1 ORDER BY points ASC"
    ).fetchall()

    solved = db.execute(
        "SELECT challenge_id FROM solves WHERE user_id = ?", (session["user_id"],)
    ).fetchall()
    solved_ids = {row["challenge_id"] for row in solved}

    return render_template("challenges.html", challenges=challenges, solved_ids=solved_ids)

@app.route("/challenge/<int:cid>", methods=["GET", "POST"])
@login_required
def challenge(cid):
    db = get_db()
    chall = db.execute("SELECT * FROM challenges WHERE id = ? AND is_visible = 1", (cid,)).fetchone()
    if not chall:
        flash("Challenge not found.", "danger")
        return redirect(url_for("challenges"))

    already_solved = db.execute(
        "SELECT id FROM solves WHERE user_id = ? AND challenge_id = ?",
        (session["user_id"], cid)
    ).fetchone()

    if request.method == "POST":
        submitted = request.form.get("flag", "").strip()
        if already_solved:
            flash("You already solved this challenge!", "info")
        elif submitted == chall["flag"]:
            db.execute(
                "INSERT INTO solves (user_id, challenge_id, solved_at) VALUES (?, ?, ?)",
                (session["user_id"], cid, datetime.now().isoformat())
            )
            db.execute(
                "UPDATE users SET score = score + ? WHERE id = ?",
                (chall["points"], session["user_id"])
            )
            db.commit()
            flash(f"Correct! +{chall['points']} points", "success")
            return redirect(url_for("challenges"))
        else:
            flash("Incorrect flag. Try again!", "danger")

    return render_template("challenge.html", chall=chall, already_solved=bool(already_solved))

@app.route("/scoreboard")
def scoreboard():
    db = get_db()
    users = db.execute(
        """
        SELECT username, score,
               (SELECT COUNT(*) FROM solves WHERE user_id = users.id) as solves
        FROM users
        WHERE is_admin = 0
        ORDER BY score DESC, solves DESC
        LIMIT 50
        """
    ).fetchall()
    return render_template("scoreboard.html", users=users)

@app.route("/admin")
@admin_required
def admin():
    db = get_db()
    challenges = db.execute("SELECT * FROM challenges ORDER BY id").fetchall()
    users = db.execute("SELECT id, username, score, is_admin FROM users ORDER BY score DESC").fetchall()
    return render_template("admin.html", challenges=challenges, users=users)

@app.route("/admin/add", methods=["GET", "POST"])
@admin_required
def admin_add():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "Misc").strip()
        description = request.form.get("description", "").strip()
        points = int(request.form.get("points", 100))
        flag = request.form.get("flag", "").strip()
        difficulty = request.form.get("difficulty", "Easy")
        hint = request.form.get("hint", "").strip()

        if not title or not flag:
            flash("Title and flag are required.", "danger")
            return redirect(url_for("admin_add"))

        db = get_db()
        db.execute(
            "INSERT INTO challenges (title, category, description, points, flag, difficulty, hint) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (title, category, description, points, flag, difficulty, hint)
        )
        db.commit()
        flash("Challenge added successfully!", "success")
        return redirect(url_for("admin"))
    return render_template("admin_add.html")

if __name__ == "__main__":
    if not os.path.exists(DATABASE):
        init_db()
    else:
        # Ensure tables exist even if db file already present
        init_db()
    print("=" * 50)
    print("  Beginner CTF Platform is running!")
    print("  Open: http://127.0.0.1:5000")
    print("  Admin login → username: admin  password: admin123")
    print("=" * 50)
    app.run(debug=True, host="0.0.0.0", port=5000)