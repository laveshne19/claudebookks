# Deploy at trade.nalandaenterprises.com

Goal: the dashboard reachable at **https://trade.nalandaenterprises.com**,
auto-starting on boot, with the app itself bound to localhost behind Nginx+HTTPS.

## 0. DNS (do this first, in your domain settings)

Add one record, then wait a few minutes for it to propagate:

| Type | Host  | Value                 | TTL  |
|------|-------|-----------------------|------|
| A    | trade | `<YOUR_VPS_PUBLIC_IP>`| 3600 |

Verify from your laptop: `ping trade.nalandaenterprises.com` should show the VPS IP.

## 1. Get the code on the VPS

```bash
sudo apt update && sudo apt install -y python3-venv nginx
# clone into your home dir (adjust user/path; the systemd unit assumes
# /home/ubuntu/claudebookks — edit it if different)
git clone <your-repo-url> ~/claudebookks
cd ~/claudebookks/trading
git checkout claude/automated-trading-app-220Zf

python3 -m venv .venv
./.venv/bin/pip install --upgrade pip
./.venv/bin/pip install -r requirements.txt

cp .env.example .env          # keep TRADING_MODE=paper for now
# optionally set DASHBOARD_PASSWORD in .env (or change it later in the UI)
```

## 2. Run it as a service (auto-start on boot)

```bash
# edit User= and the three paths in the unit if your user isn't "ubuntu"
sudo cp deploy/autotrader.service /etc/systemd/system/autotrader.service
sudo systemctl daemon-reload
sudo systemctl enable --now autotrader
sudo systemctl status autotrader        # should be "active (running)"
```

The app now listens on `127.0.0.1:8080` (not public yet).

## 3. Nginx + HTTPS

```bash
sudo cp deploy/nginx-trade.conf /etc/nginx/sites-available/trade.nalandaenterprises.com
sudo ln -s /etc/nginx/sites-available/trade.nalandaenterprises.com /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# free HTTPS cert (auto-renews). Needs DNS from step 0 to be live.
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d trade.nalandaenterprises.com
```

Open your firewall for web traffic if needed:
```bash
sudo ufw allow 'Nginx Full' && sudo ufw allow OpenSSH
```

## 4. First sign-in & configuration

1. Visit **https://trade.nalandaenterprises.com**
2. Log in with **admin / changeme** (or your `DASHBOARD_PASSWORD`).
3. Open **⚙ Settings** and immediately **change the password**.
4. Paste your **Claude API key** (for AI analysis / Claude-advisor strategy).
5. Keep **mode = paper**, click **Start**, and let it run a few sessions during
   market hours (09:15–15:30 IST). Review the trade log.

## 5. Going live (only after paper looks good)

In **⚙ Settings**:
1. Enter **Dhan Client ID + Access Token** and the **security map**
   (`{"RELIANCE":"2885", ...}` — get IDs from Dhan's instrument master).
2. Switch **mode → live**. The badge turns red; it will refuse to route real
   orders unless creds + security map are all present.
3. **Start tiny**: small `Max ₹ per trade` and a low `Daily loss limit`.
4. Keep the **PANIC** button in mind — it flattens everything and halts.

## Updating later

```bash
cd ~/claudebookks/trading && git pull
./.venv/bin/pip install -r requirements.txt
sudo systemctl restart autotrader
```

> Reminder: automated trading is risky and not guaranteed to profit. This is not
> investment advice. Run paper first, keep guardrails tight, and only risk
> capital you can afford to lose.
