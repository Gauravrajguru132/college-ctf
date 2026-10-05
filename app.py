from flask import Flask, render_template, request, redirect, url_for, session, flash, g
import hashlib
import os
from datetime import datetime
from functools import wraps
from urllib.parse import urlparse

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "college-ctf-secret-change-me-in-production-2026")

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        if DATABASE_URL:
            import psycopg
            from psycopg.rows import dict_row
            result = urlparse(DATABASE_URL)
            db = g._database = psycopg.connect(
                dbname=result.path[1:],
                user=result.username,
                password=result.password,
                host=result.hostname,
                port=result.port,
                row_factory=dict_row
            )
            db.autocommit = True
        else:
            import sqlite3
            db = g._database = sqlite3.connect("ctf.db")
            db.row_factory = sqlite3.Row
    return db

def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()

app.teardown_appcontext(close_connection)

def execute(query, params=None, fetchone=False, fetchall=False):
    db = get_db()
    if DATABASE_URL:
        # psycopg3 uses %s placeholders
        query = query.replace("?", "%s")
        cur = db.cursor()
        cur.execute(query, params or ())
        if fetchone:
            return cur.fetchone()
        if fetchall:
            return cur.fetchall()
        return cur
    else:
        cur = db.execute(query, params or ())
        if fetchone:
            return cur.fetchone()
        if fetchall:
            return cur.fetchall()
        db.commit()
        return cur

def init_db():
    with app.app_context():
        if DATABASE_URL:
            execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    is_admin INTEGER DEFAULT 0,
                    score INTEGER DEFAULT 0,
                    created_at TEXT
                )
            """)
            execute("""
                CREATE TABLE IF NOT EXISTS challenges (
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    category TEXT NOT NULL,
                    description TEXT NOT NULL,
                    points INTEGER NOT NULL,
                    flag TEXT NOT NULL,
                    difficulty TEXT DEFAULT 'Easy',
                    hint TEXT,
                    is_visible INTEGER DEFAULT 1
                )
            """)
            execute("""
                CREATE TABLE IF NOT EXISTS solves (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    challenge_id INTEGER NOT NULL,
                    solved_at TEXT,
                    UNIQUE(user_id, challenge_id)
                )
            """)
        else:
            execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    is_admin INTEGER DEFAULT 0,
                    score INTEGER DEFAULT 0,
                    created_at TEXT
                )
            """)
            execute("""
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
                )
            """)
            execute("""
                CREATE TABLE IF NOT EXISTS solves (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    challenge_id INTEGER NOT NULL,
                    solved_at TEXT,
                    UNIQUE(user_id, challenge_id)
                )
            """)

        admin_pass = hashlib.sha256("admin123".encode()).hexdigest()
        existing = execute("SELECT id FROM users WHERE username = ?", ("admin",), fetchone=True)
        if not existing:
            execute(
                "INSERT INTO users (username, password, is_admin, score, created_at) VALUES (?, ?, 1, 0, ?)",
                ("admin", admin_pass, datetime.now().isoformat())
            )

        # Force replace challenges
        execute("DELETE FROM solves")
        execute("DELETE FROM challenges")

        challenges = [
    ("Welcome", "General",
     "Welcome to the College CTF!\n\nThis is the only challenge where the flag is given.\n\nFlag: flag{welcome_to_the_real_ctf}",
     10, "flag{welcome_to_the_real_ctf}", "Easy", "Just submit the flag written above."),

    ("Base64 Decode", "Crypto",
     "Decode this Base64 string to get the flag:\n\nZmxhZ3tiYXNlNjRfZGVjb2RlX3N1Y2Nlc3N9",
     20, "flag{base64_decode_success}", "Easy", "Use CyberChef or any online Base64 decoder."),

    ("Caesar Shift", "Crypto",
     "The flag was encrypted with a Caesar cipher (shift of 3).\n\nCiphertext: iodj{fdhvdu_flskhu_hdv|}",
     25, "flag{caesar_cipher_easy}", "Easy", "Shift each letter backwards by 3 positions."),

    ("ROT13", "Crypto",
     "Apply ROT13 to this text:\n\nsynt{ebg13_vf_rnfl}",
     20, "flag{rot13_is_easy}", "Easy", "ROT13 shifts letters by 13 places. Use CyberChef or online ROT13 tool."),

    ("Hex to Text", "Crypto",
     "Convert this hexadecimal to text:\n\n666c61677b6865785f746f5f746578745f776f726b737d",
     25, "flag{hex_to_text_works}", "Easy", "Use CyberChef (From Hex) or Python: bytes.fromhex('...').decode()"),

    ("Binary Message", "Crypto",
     "Convert this binary to ASCII:\n\n01100110 01101100 01100001 01100111 01111011 01100010 01101001 01101110 01100001 01110010 01111001 01011111 01100110 01110101 01101110 01111101",
     30, "flag{binary_fun}", "Easy", "Use CyberChef (From Binary) or an online binary converter."),

    ("Reverse It", "Misc",
     "The flag is written backwards:\n\n}ysaE_esreveR{galf",
     15, "flag{Reverse_Easy}", "Easy", "Just reverse the entire string."),

    ("ASCII Numbers", "Crypto",
     "These numbers are ASCII codes of the flag:\n\n102 108 97 103 123 97 115 99 105 105 95 110 117 109 98 101 114 115 125",
     30, "flag{ascii_numbers}", "Easy", "Convert each number to its character (102 = f, 108 = l, etc)."),

    ("URL Decode", "Web",
     "Decode this URL-encoded string:\n\nflag%7Burl_decode_is_simple%7D",
     20, "flag{url_decode_is_simple}", "Easy", "Use CyberChef (URL Decode) or any URL decoder."),

    ("Morse Code", "Crypto",
     "Decode this Morse code:\n\n..-. .-.. .- --. { -- --- .-. ... . _ -.-. --- -.. . }",
     30, "flag{morse_code}", "Easy", "Use an online Morse code decoder."),

    ("Atbash Cipher", "Crypto",
     "Atbash reverses the alphabet (A↔Z, B↔Y...). Decode:\n\nuozt{zgyzhs_xrkovi}",
     30, "flag{atbash_cipher}", "Easy", "A becomes Z, B becomes Y, etc. Or use CyberChef Atbash."),

    ("Simple Math", "Misc",
     "Solve: (15 * 4) + (100 / 5) - 7\n\nThe flag is flag{answer} where answer is the result.",
     15, "flag{73}", "Easy", "Calculate the expression carefully."),

    ("Hidden Spaces", "Forensics",
     "There are extra spaces in this text. Remove them to get the flag:\n\nf l a g { n o _ s p a c e s }",
     25, "flag{no_spaces}", "Easy", "Remove all spaces from the text."),

    ("Year of Python", "OSINT",
     "In which year was the first version of Python released?\n\nFlag format: flag{YYYY}",
     25, "flag{1991}", "Easy", "Search on Google: 'when was python first released'"),

    ("Creator of Linux", "OSINT",
     "Who created the Linux kernel?\n\nFlag format: flag{firstname_lastname} (all lowercase)",
     25, "flag{linus_torvalds}", "Easy", "Google 'who created linux'"),

    ("Base32 Decode", "Crypto",
     "Decode this Base32 string:\n\nMZXW6YTBONSXE43FOMQHI2DFON2GS4ZAMFRGG===",
     30, "flag{base32_works_too}", "Easy", "Use CyberChef (From Base32)."),

    ("Comment Finder", "Misc",
     "Look at this Python code carefully:\n\nprint('Hello')\n# This is a normal comment\n# flag{check_comments_carefully}\nprint('World')",
     20, "flag{check_comments_carefully}", "Easy", "Read the comments in the code."),

    ("HTTP Status", "Web",
     "What does HTTP status code 404 mean?\n\nFlag format: flag{not_found} (all lowercase with underscore)",
     20, "flag{not_found}", "Easy", "Google 'HTTP status code 404'"),

    ("Lowercase Me", "Misc",
     "Convert this to lowercase to get the flag:\n\nFLAG{LOWERCASE_IS_IMPORTANT}",
     10, "flag{lowercase_is_important}", "Easy", "Just make everything lowercase."),

    ("Double Base64", "Crypto",
     "This was Base64 encoded twice. Decode it twice:\n\nV2xOa1lYTmtaV052Ym5SbGNqST0=",
     40, "flag{double_base64}", "Easy", "Decode once, then decode the result again."),

    ("Caesar + Base64", "Crypto",
     "The flag was first Caesar shifted by 5, then Base64 encoded.\n\nCiphertext: aG1mbHtqaGxmc2Jfa2F0c2J9",
     70, "flag{caesar_base64}", "Medium", "First decode Base64, then shift letters back by 5."),

    ("XOR Single Byte", "Crypto",
     "This hex was XORed with a single byte key (try keys from 1 to 20):\n\n0a0d0a1d1b0c1a0b1c0d1b0a1d0c1b0a",
     80, "flag{xor_is_cool}", "Medium", "XOR every byte with the same key. Look for readable text starting with 'flag{'."),

    ("Rail Fence", "Crypto",
     "This message was encrypted with Rail Fence cipher (3 rails):\n\nfa{alsnece}lgri_ee",
     70, "flag{rail_fence}", "Medium", "Search for 'rail fence cipher decoder' and try 3 rails."),

    ("Vigenere Easy", "Crypto",
     "Encrypted with Vigenere cipher. Key = 'key'\n\nCiphertext: pldh{rmlirivi_iewc}",
     90, "flag{vigenere_easy}", "Medium", "Use CyberChef Vigenere Decrypt with key 'key'."),

    ("HTML Entities", "Web",
     "Decode these HTML entities:\n\n&#102;&#108;&#97;&#103;&#123;&#104;&#116;&#109;&#108;&#95;&#101;&#110;&#116;&#105;&#116;&#105;&#101;&#115;&#125;",
     60, "flag{html_entities}", "Medium", "Use CyberChef or an HTML entity decoder."),

    ("Layered Encoding", "Crypto",
     "The flag is hidden under multiple layers.\nFirst it was reversed, then Base64 encoded.\n\nCiphertext: fXNlY2FsX2RldmVyc2V7Z2FsZg==",
     80, "flag{reversed_layers}", "Medium", "Decode Base64 first, then reverse the result."),

    ("Keyboard Shift", "Misc",
     "The flag was typed with fingers shifted one key to the right on a QWERTY keyboard.\n\nCiphertext: g;sh{jrtvphs_sodt}",
     70, "flag{keyboard_shift}", "Medium", "On QWERTY, shift each key one position left."),

    ("Pig Latin Style", "Misc",
     "Each word was moved: first letter to the end + 'ay'.\n\nlagfay {igpay atinlay isay unfay}",
     60, "flag{pig_latin_is_fun}", "Medium", "Move the last 'ay' and put the letter before it to the front of each word."),

    ("Date Puzzle", "OSINT",
     "The first public release of the World Wide Web was in which year?\n\nFlag format: flag{YYYY}",
     60, "flag{1991}", "Medium", "Search for 'when was the world wide web released'"),

    ("Simple Substitution", "Crypto",
     "A=1, B=2, C=3... Z=26. The flag numbers are:\n\n6 12 1 7 27 19 21 2 19 20 9 20 21 20 9 15 14 28",
     70, "flag{substitution}", "Medium", "Convert numbers back to letters. 27 = { and 28 = }"),

    ("Base64 + ROT13", "Crypto",
     "First ROT13, then Base64:\n\nc3ludHtoYmcyM19uYl9yYm9yZ30=",
     75, "flag{base64_and_rot13}", "Medium", "Decode Base64 first, then apply ROT13."),

    ("Phone Keypad", "Misc",
     "On old phone keypads: 2=ABC, 3=DEF, 4=GHI, 5=JKL, 6=MNO, 7=PQRS, 8=TUV, 9=WXYZ\n\nThe flag is typed as: 3 5 2 4 { 7 4 6 6 3 5 2 9 7 2 3 }",
     70, "flag{phone_keypad}", "Medium", "Map the numbers back to possible letters and find the meaningful flag."),

    ("Leetspeak", "Misc",
     "Decode this leetspeak:\n\nf14g{1337_5p34k_15_c00l}",
     50, "flag{leet_speak_is_cool}", "Medium", "Replace numbers with similar looking letters (1=l/i, 3=e, 4=a, 5=s, 0=o, 7=t)."),

    ("Whitespace Stego", "Forensics",
     "The flag is hidden using only the visible text. Read carefully:\n\nThe secret is flag{look_carefully} right here.",
     65, "flag{look_carefully}", "Medium", "Sometimes the flag is written in plain sight."),

    ("MD5 Hint", "Crypto",
     "I took MD5 of a common word. The hash starts with 5f4dcc3b...\n\nThe flag is flag{that_word}",
     80, "flag{password}", "Medium", "Search for the beginning of the hash or try common passwords."),

    ("Triple Layer", "Crypto",
     "The flag went through three steps:\n1. Reversed\n2. Caesar shift +4\n3. Base64\n\nFinal ciphertext: ZmhsaHt2eXNsaF9lbHBpcnQ=",
     180, "flag{triple_layer}", "Hard", "Decode Base64 → shift back by 4 → reverse the string."),

    ("XOR Repeating", "Crypto",
     "XORed with the repeating key 'ctf'. Hex output:\n\n05001a1b0a160a0b1c0d0a1b0c0a1d",
     200, "flag{xor_repeating}", "Hard", "XOR with repeating key 'ctf'. Use CyberChef or a small Python script."),

    ("Custom Alphabet", "Crypto",
     "Alphabet mapped as: a→q b→w c→e d→r e→t f→y g→u h→i i→o j→p k→a l→s m→d n→f o→g p→h q→j r→k s→l t→z u→x v→c w→v x→b y→n z→m\n\nCiphertext: ysqu{exlzgd_lxnlzozxzogf}",
     160, "flag{custom_substitution}", "Hard", "Reverse the given mapping carefully."),

    ("Brainfuck", "Misc",
     "This is Brainfuck code. Interpret it to get the flag:\n\n++++++++++[>+++++++>++++++++++>+++>+<<<<-]>++.>+.+++++++..+++.>++.<<+++++++++++++++.>.+++.------.--------.>+.>.",
     150, "flag{brainfuck}", "Hard", "Use an online Brainfuck interpreter."),

    ("Tiny RSA", "Crypto",
     "Tiny RSA. n = 33, e = 3, ciphertext c = 8\n\nDecrypt to get a number. Flag format: flag{number}",
     220, "flag{2}", "Hard", "Find private exponent d, then m = c^d mod n."),

    ("Multi Encoding", "Crypto",
     "Flag was Base64 encoded, then the result was turned into hex.\n\nHex: 5a6d78685a334e6a62334e6c636d397562334e6a62334e6c636d3975",
     170, "flag{multi_base}", "Hard", "Convert hex → text (you get Base64) → decode Base64."),

    ("Keyboard Walk", "Misc",
     "Someone walked on the QWERTY keyboard to type the flag.\nThe flag is flag{qwerty_walk}",
     150, "flag{qwerty_walk}", "Hard", "The flag is given in the description this time as a special case."),

    ("Hash Crack", "Crypto",
     "MD5 of the flag starts with: 5f4dcc3b\nThe original word is a very common password.\nFlag format: flag{word}",
     180, "flag{password}", "Hard", "The famous MD5 of 'password' starts with 5f4dcc3b."),

    ("Double Reverse + Base64", "Crypto",
     "Steps: reverse → Base64 → reverse again.\n\nFinal: ==gCNlJXZ2Vmcj9GauV2YpR3Y",
     190, "flag{double_reverse}", "Hard", "Reverse the string → decode Base64 → reverse again."),

    ("Final Boss", "General",
     "You have reached the final challenge.\n\nThe flag is the first 8 characters of the MD5 of 'college_ctf_final' in the format flag{xxxxxxxx}",
     250, "flag{8f4e3c2b}", "Hard", "Calculate MD5('college_ctf_final') and take the first 8 characters."),
]

        for c in challenges:
            execute(
                "INSERT INTO challenges (title, category, description, points, flag, difficulty, hint) VALUES (?, ?, ?, ?, ?, ?, ?)",
                c
            )

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
        user = execute("SELECT is_admin FROM users WHERE id = ?", (session["user_id"],), fetchone=True)
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
        try:
            execute(
                "INSERT INTO users (username, password, created_at) VALUES (?, ?, ?)",
                (username, hash_password(password), datetime.now().isoformat())
            )
            flash("Registration successful! Please login.", "success")
            return redirect(url_for("login"))
        except Exception:
            flash("Username already exists.", "danger")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = execute(
            "SELECT * FROM users WHERE username = ? AND password = ?",
            (username, hash_password(password)),
            fetchone=True
        )
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

@app.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        current = request.form.get("current_password", "")
        new_pass = request.form.get("new_password", "")
        confirm = request.form.get("confirm_password", "")
        if not current or not new_pass or not confirm:
            flash("All fields are required.", "danger")
            return redirect(url_for("change_password"))
        if new_pass != confirm:
            flash("New passwords do not match.", "danger")
            return redirect(url_for("change_password"))
        if len(new_pass) < 4:
            flash("New password must be at least 4 characters.", "danger")
            return redirect(url_for("change_password"))
        user = execute("SELECT * FROM users WHERE id = ?", (session["user_id"],), fetchone=True)
        if not user or user["password"] != hash_password(current):
            flash("Current password is incorrect.", "danger")
            return redirect(url_for("change_password"))
        execute("UPDATE users SET password = ? WHERE id = ?", (hash_password(new_pass), session["user_id"]))
        flash("Password changed successfully!", "success")
        return redirect(url_for("challenges"))
    return render_template("change_password.html")

@app.route("/challenges")
@login_required
def challenges():
    challenges = execute("SELECT * FROM challenges WHERE is_visible = 1 ORDER BY points ASC", fetchall=True)
    solved = execute("SELECT challenge_id FROM solves WHERE user_id = ?", (session["user_id"],), fetchall=True)
    solved_ids = {row["challenge_id"] for row in solved} if solved else set()
    return render_template("challenges.html", challenges=challenges, solved_ids=solved_ids)

@app.route("/challenge/<int:cid>", methods=["GET", "POST"])
@login_required
def challenge(cid):
    chall = execute("SELECT * FROM challenges WHERE id = ? AND is_visible = 1", (cid,), fetchone=True)
    if not chall:
        flash("Challenge not found.", "danger")
        return redirect(url_for("challenges"))
    already_solved = execute("SELECT id FROM solves WHERE user_id = ? AND challenge_id = ?", (session["user_id"], cid), fetchone=True)
    if request.method == "POST":
        submitted = request.form.get("flag", "").strip()
        if already_solved:
            flash("You already solved this challenge!", "info")
        elif submitted == chall["flag"]:
            execute("INSERT INTO solves (user_id, challenge_id, solved_at) VALUES (?, ?, ?)", (session["user_id"], cid, datetime.now().isoformat()))
            execute("UPDATE users SET score = score + ? WHERE id = ?", (chall["points"], session["user_id"]))
            flash(f"Correct! +{chall['points']} points", "success")
            return redirect(url_for("challenges"))
        else:
            flash("Incorrect flag. Try again!", "danger")
    return render_template("challenge.html", chall=chall, already_solved=bool(already_solved))

@app.route("/scoreboard")
def scoreboard():
    users = execute("""
        SELECT username, score,
               (SELECT COUNT(*) FROM solves WHERE user_id = users.id) as solves
        FROM users WHERE is_admin = 0
        ORDER BY score DESC, solves DESC LIMIT 50
    """, fetchall=True)
    return render_template("scoreboard.html", users=users or [])

@app.route("/admin")
@admin_required
def admin():
    challenges = execute("SELECT * FROM challenges ORDER BY id", fetchall=True)
    users = execute("SELECT id, username, score, is_admin FROM users ORDER BY score DESC", fetchall=True)
    return render_template("admin.html", challenges=challenges or [], users=users or [])

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
        execute("INSERT INTO challenges (title, category, description, points, flag, difficulty, hint) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (title, category, description, points, flag, difficulty, hint))
        flash("Challenge added successfully!", "success")
        return redirect(url_for("admin"))
    return render_template("admin_add.html")

with app.app_context():
    init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("=" * 50)
    print("  Beginner CTF Platform is running!")
    print(f"  Port: {port}")
    print("  Admin login → username: admin  password: admin123")
    print("=" * 50)
    app.run(host="0.0.0.0", port=port)