import os, secrets, hashlib, hmac, time
from pathlib import Path
from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from db import init_db, create_payment_request, list_payments, review_payment

load_dotenv()
app = FastAPI(title="AXC BOT Admin")
ROOT = Path(__file__).parent
PROOFS = ROOT / "payment_proofs"
PROOFS.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
PRICE = int(os.getenv("PRICE_INR", "99"))
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
SESSION_SECRET = os.getenv("SESSION_SECRET", "replace-me")
COOKIE_NAME = "axc_admin"

def signed_token():
    stamp = str(int(time.time()))
    sig = hmac.new(SESSION_SECRET.encode(), stamp.encode(), hashlib.sha256).hexdigest()
    return stamp + "." + sig

def is_admin(request: Request):
    token = request.cookies.get(COOKIE_NAME, "")
    try:
        stamp, sig = token.split(".", 1)
        expected = hmac.new(SESSION_SECRET.encode(), stamp.encode(), hashlib.sha256).hexdigest()
        return abs(int(time.time()) - int(stamp)) < 8 * 3600 and hmac.compare_digest(sig, expected)
    except Exception:
        return False

def page(body, title="AXC BOT"):
    return HTMLResponse(f"""<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>{title}</title><style>
    *{{box-sizing:border-box}}body{{margin:0;background:#0b1020;color:#eef2ff;font:16px system-ui}}
    main{{max-width:900px;margin:40px auto;padding:24px}}.card{{background:#151d33;border:1px solid #2b3654;border-radius:18px;padding:22px;margin:16px 0}}
    h1{{font-size:30px;margin:0 0 8px}}a{{color:#c4b5fd}}input,button{{font:inherit;padding:12px;border-radius:10px;border:1px solid #445070}}
    input{{background:#0b1020;color:white;width:100%;margin:7px 0 14px}}button{{background:#8b5cf6;color:white;border:0;font-weight:700;cursor:pointer}}
    .muted{{color:#aab5d1}}.row{{display:flex;gap:12px;flex-wrap:wrap}}.row form{{display:inline}}.pill{{color:#ddd6fe}}
    img{{display:block;max-width:min(100%,420px);height:auto;background:white;padding:10px;border-radius:12px;margin:14px auto}}
    table{{width:100%;border-collapse:collapse}}td,th{{padding:10px;border-bottom:1px solid #35415f;text-align:left;vertical-align:top;overflow-wrap:anywhere}}
    </style></head><body><main><h1>AXC BOT</h1><div class="muted">Premium access • ₹{PRICE} • Manual verification</div>{body}</main></body></html>""")

@app.on_event("startup")
def startup():
    init_db()

@app.get("/", response_class=HTMLResponse)
def home():
    return page(f"""<div class="card"><h2>AXC BOT Premium</h2><p>Premium functions unlock only after an admin verifies your payment.</p>
    <p><a href="/pay">Go to payment page</a> · <a href="/admin">Admin login</a></p></div>""")

@app.get("/pay", response_class=HTMLResponse)
def pay_page():
    return page(f"""<div class="card"><h2>Pay ₹{PRICE}</h2><p>Scan this QR using your UPI app. Before paying, verify the payee details shown in your own UPI app.</p>
    <img src="/static/payment_qr.webp" alt="AXC BOT payment QR">
    <p class="muted">After paying, submit your Discord user ID and UPI transaction reference. This form does not itself verify payment.</p>
    <form method="post" action="/submit-payment" enctype="multipart/form-data">
    <label>Discord user ID</label><input name="discord_user_id" required pattern="[0-9]{{17,20}}" placeholder="Your Discord numeric user ID">
    <label>UPI transaction reference</label><input name="upi_reference" required minlength="6" maxlength="80" placeholder="Transaction / UTR reference">
    <label>Payment screenshot (optional)</label><input type="file" name="proof" accept="image/png,image/jpeg,image/webp">
    <button type="submit">Submit for manual review</button></form></div>""")

@app.post("/submit-payment", response_class=HTMLResponse)
async def submit_payment(discord_user_id: str = Form(...), upi_reference: str = Form(...), proof: UploadFile | None = File(None)):
    if not discord_user_id.isdigit() or not 17 <= len(discord_user_id) <= 20:
        raise HTTPException(400, "Invalid Discord user ID")
    if len(upi_reference.strip()) < 6:
        raise HTTPException(400, "Invalid transaction reference")
    filename = None
    if proof and proof.filename:
        data = await proof.read(5 * 1024 * 1024 + 1)
        if len(data) > 5 * 1024 * 1024:
            raise HTTPException(413, "Screenshot must be 5 MB or smaller")
        suffix = Path(proof.filename).suffix.lower()
        if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
            raise HTTPException(400, "Only PNG, JPG, or WEBP screenshots are accepted")
        filename = secrets.token_hex(16) + suffix
        (PROOFS / filename).write_bytes(data)
    try:
        create_payment_request(discord_user_id, upi_reference, filename)
    except Exception:
        raise HTTPException(409, "This Discord ID and reference have already been submitted")
    return page("<div class='card'><h2>Request submitted</h2><p>Your request is pending. An admin must verify the transaction in their payment account before approving access.</p><a href='/pay'>Back</a></div>")

@app.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request):
    if not is_admin(request):
        return page("""<div class="card"><h2>Admin login</h2><form method="post" action="/admin/login">
        <label>Admin password</label><input type="password" name="password" required><button>Sign in</button></form></div>""")
    rows = list_payments()
    trs = ""
    for r in rows:
        proof = f"<a href='/admin/proof/{r['proof_filename']}'>View proof</a>" if r["proof_filename"] else "—"
        actions = ""
        if r["status"] == "pending":
            actions = f"""<form method="post" action="/admin/review/{r['id']}"><button name="decision" value="approve">Approve</button>
            <button name="decision" value="reject">Reject</button></form>"""
        trs += f"<tr><td>{r['id']}</td><td>{r['discord_user_id']}</td><td>{r['upi_reference']}</td><td>{r['status']}</td><td>{proof}</td><td>{actions}</td></tr>"
    return page(f"""<div class="card"><h2>Payment requests</h2><p>Verify each transaction in your UPI/bank app before approving. A screenshot or reference alone is not proof of settled payment.</p>
    <p><a href="/admin/logout">Log out</a></p><table><tr><th>ID</th><th>Discord ID</th><th>UPI reference</th><th>Status</th><th>Proof</th><th>Action</th></tr>{trs or '<tr><td colspan="6">No requests yet</td></tr>'}</table></div>""")

@app.post("/admin/login")
def admin_login(password: str = Form(...)):
    if not ADMIN_PASSWORD or not secrets.compare_digest(password, ADMIN_PASSWORD):
        raise HTTPException(401, "Invalid admin password")
    response = RedirectResponse("/admin", status_code=303)
    response.set_cookie(COOKIE_NAME, signed_token(), httponly=True, secure=os.getenv("COOKIE_SECURE", "0") == "1", samesite="strict", max_age=28800)
    return response

@app.get("/admin/logout")
def admin_logout():
    response = RedirectResponse("/admin", status_code=303)
    response.delete_cookie(COOKIE_NAME)
    return response

@app.post("/admin/review/{payment_id}")
def admin_review(payment_id: int, request: Request, decision: str = Form(...)):
    if not is_admin(request):
        raise HTTPException(401, "Admin login required")
    if decision not in {"approve", "reject"}:
        raise HTTPException(400, "Invalid decision")
    if not review_payment(payment_id, decision == "approve"):
        raise HTTPException(409, "Request was already reviewed or does not exist")
    return RedirectResponse("/admin", status_code=303)

@app.get("/admin/proof/{filename}")
def proof(filename: str, request: Request):
    if not is_admin(request):
        raise HTTPException(401, "Admin login required")
    if Path(filename).name != filename:
        raise HTTPException(400, "Invalid filename")
    path = PROOFS / filename
    if not path.exists():
        raise HTTPException(404, "Not found")
    return FileResponse(path)
