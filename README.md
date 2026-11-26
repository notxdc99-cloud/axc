# AXC BOT — Discord bot + payment dashboard

A starter project with a Discord.py bot, FastAPI web dashboard, ₹99 payment instructions, QR display, and manual payment approval.

## Important payment note
The QR image is displayed exactly as supplied. The app does **not** independently verify UPI payments. Admins must check the transaction in their own UPI/bank account before approving. Never approve based only on a screenshot or a user-entered reference. Confirm the payee name and amount in the payment app before paying.

## Requirements
- Python 3.10+
- A Discord application/bot and its token
- A server or computer to host the dashboard

## Setup (Windows PowerShell)
```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```
Edit `.env`:
- `DISCORD_TOKEN`: bot token from Discord Developer Portal
- `ADMIN_PASSWORD`: choose a long, unique password
- `SESSION_SECRET`: choose a long random secret
- `PUBLIC_BASE_URL`: public HTTPS URL once deployed
- `PRICE_INR=99`

Run the dashboard:
```powershell
uvicorn web:app --host 127.0.0.1 --port 8000
```
Open http://127.0.0.1:8000/pay for the QR/payment page and http://127.0.0.1:8000/admin for admin review.

Run the Discord bot in a second terminal:
```powershell
python bot.py
```

## Discord commands
- `/pay` — sends the payment page link privately
- `/premium` — checks whether the user has been approved
- `/giveaway` — demo giveaway announcement; requires approved access

## Deployment/security checklist
1. Use HTTPS and set `COOKIE_SECURE=1` in the hosting environment.
2. Set a strong `ADMIN_PASSWORD` and `SESSION_SECRET`; never publish `.env`.
3. Keep the database and `payment_proofs/` private and backed up.
4. Restrict dashboard access if possible (VPN/IP allowlist); add CSRF protection and rate limiting before public production use.
5. Use a payment provider with signed server-side webhooks if you later want automatic verification. Do not trust browser redirects or screenshots as proof.
6. Invite the bot with `bot` and `applications.commands` scopes and only the permissions it needs.
7. Replace the demo giveaway command with your complete giveaway workflow before production.
