import os, sqlite3, time
from dotenv import load_dotenv
load_dotenv()
DB = os.getenv("DATABASE_PATH", "axc_bot.sqlite3")

def connect():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with connect() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            discord_user_id TEXT NOT NULL,
            upi_reference TEXT NOT NULL,
            proof_filename TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at INTEGER NOT NULL,
            reviewed_at INTEGER,
            UNIQUE(discord_user_id, upi_reference)
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS access (
            discord_user_id TEXT PRIMARY KEY,
            approved_at INTEGER NOT NULL,
            payment_id INTEGER NOT NULL
        )""")

def create_payment_request(user_id, reference, proof_filename=None):
    with connect() as con:
        cur = con.execute(
            "INSERT INTO payments(discord_user_id,upi_reference,proof_filename,created_at) VALUES(?,?,?,?)",
            (str(user_id), reference.strip(), proof_filename, int(time.time()))
        )
        return cur.lastrowid

def list_payments():
    with connect() as con:
        return con.execute("SELECT * FROM payments ORDER BY created_at DESC").fetchall()

def review_payment(payment_id, approve):
    now = int(time.time())
    with connect() as con:
        row = con.execute("SELECT * FROM payments WHERE id=?", (payment_id,)).fetchone()
        if not row or row["status"] != "pending":
            return False
        status = "approved" if approve else "rejected"
        con.execute("UPDATE payments SET status=?, reviewed_at=? WHERE id=?", (status, now, payment_id))
        if approve:
            con.execute("INSERT OR REPLACE INTO access(discord_user_id,approved_at,payment_id) VALUES(?,?,?)",
                        (row["discord_user_id"], now, payment_id))
        return True

def has_active_access(user_id):
    with connect() as con:
        return con.execute("SELECT 1 FROM access WHERE discord_user_id=?", (str(user_id),)).fetchone() is not None
