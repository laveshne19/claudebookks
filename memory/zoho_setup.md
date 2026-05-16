## How to (re)generate a Zoho Books refresh token

Your account is on the **`.in` data centre** — we already detected that. Now create a refresh token that gives Nalanda ERP read access to Books.

---

### Method A — Self Client (5 minutes, recommended)

1. Go to **https://api-console.zoho.in/** → click **Self Client** → tab **Generate Code**
2. Enter scope: `ZohoBooks.fullaccess.all`
3. Time duration: `10 minutes`
4. Scope description: `nalanda-erp`
5. Click **Create** → copy the code (looks like `1000.xxxx...`)
6. Within 10 minutes, run on any terminal:

```bash
curl -X POST "https://accounts.zoho.in/oauth/v2/token" \
  -d "grant_type=authorization_code" \
  -d "client_id=1000.Z89SM23VNUJTZUB9ESPZOQ6P2ZSNPM" \
  -d "client_secret=4701fead0e3b8209c1516b7223e6b8f8f6360894c9" \
  -d "code=PASTE_THE_CODE_HERE"
```

Response contains:
```json
{
  "access_token": "1000.xxx...",
  "refresh_token": "1000.xxx...",      ← THIS is the long-lived token I need
  "expires_in": 3600
}
```

Send me the `refresh_token` value.

---

### Method B — Browser flow (if Self Client is disabled)

1. Open this URL in your browser (already filled with your client id + needed scope):

```
https://accounts.zoho.in/oauth/v2/auth?scope=ZohoBooks.fullaccess.all&client_id=1000.Z89SM23VNUJTZUB9ESPZOQ6P2ZSNPM&response_type=code&access_type=offline&prompt=consent&redirect_uri=https://api-console.zoho.in
```

2. Login → click **Accept**
3. Browser redirects to `https://api-console.zoho.in/?code=1000.xxx...&...`
4. Copy the `code=` value and run the curl from Method A step 6.

---

### Common gotchas

- ❌ The first `1000.xxx` you get is the **authorization code** (single-use, 60 sec). You need to **exchange it** for the refresh token via the curl call above.
- ❌ Scope must be `ZohoBooks.fullaccess.all` (not just `ZohoBooks.invoices.READ`)
- ❌ `access_type=offline` and `prompt=consent` are **required** to get a refresh token
- ✅ Once obtained, refresh tokens are valid until manually revoked

---

### Once you send the refresh token

I'll paste it into `.env` and the system will:
1. Auto-detect your Organization ID
2. Run an initial full historical sync from Zoho Books → MongoDB (customers, invoices, payments, credit notes)
3. Enable the **30-minute scheduled sync** going forward
4. Feed historical data into Claude for better customer pattern analysis
