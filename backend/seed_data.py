"""Seed Nalanda Enterprises with realistic distribution data."""
import random
from datetime import datetime, timezone, timedelta
from auth import hash_password
from models import now_iso, new_id

BRANDS = ["Boat", "Fireboltt", "Noise", "Logitech", "Amazon", "Swiss Military", "Mivi"]

PRODUCTS = {
    "Boat": [("Airdopes 141", 1299), ("Rockerz 450", 1499), ("Wave Call", 2499), ("Stone 1200", 3499)],
    "Fireboltt": [("Ninja Pro", 1799), ("Phoenix Pro", 2499), ("Talk 2", 1999)],
    "Noise": [("ColorFit Pulse 3", 1999), ("Buds VS104", 999), ("ColorFit Ultra", 4499)],
    "Logitech": [("M185 Mouse", 799), ("MX Master 3S", 9999), ("K380 Keyboard", 2999)],
    "Amazon": [("Echo Dot 5", 4499), ("Fire TV Stick 4K", 5999), ("Kindle PW", 13999)],
    "Swiss Military": [("Backpack X1", 2499), ("Power Bank 20K", 1999)],
    "Mivi": [("DuoPods A25", 999), ("Roam 2", 1499), ("Play 5W", 799)],
}

MUMBAI_AREAS = [
    ("Andheri West", 19.1364, 72.8296),
    ("Bandra", 19.0596, 72.8295),
    ("Borivali", 19.2335, 72.8567),
    ("Dadar", 19.0176, 72.8431),
    ("Goregaon", 19.1545, 72.8497),
    ("Juhu", 19.1075, 72.8263),
    ("Kandivali", 19.2058, 72.8526),
    ("Khar", 19.0710, 72.8345),
    ("Malad", 19.1875, 72.8485),
    ("Powai", 19.1197, 72.9056),
    ("Santacruz", 19.0822, 72.8403),
    ("Thane", 19.2183, 72.9781),
    ("Vile Parle", 19.0998, 72.8470),
    ("Worli", 19.0096, 72.8175),
    ("Mulund", 19.1726, 72.9425),
]

CUSTOMER_PREFIXES = [
    "Sharma Electronics", "Mehta Gadgets", "Patel Mobile World", "Krishna Tele",
    "Star Communications", "Galaxy Mobiles", "Royal Electronics", "Modern Gadget House",
    "Prime Tech Store", "City Electronics", "Smart Buy", "Tech Bazaar",
    "Digital Junction", "Mobile Empire", "Gadget Galleria", "Elite Electronics",
    "Universal Mobiles", "Apex Tech", "Pinnacle Gadgets", "Trend Setters",
    "Mahesh Mobile", "Suraj Electronics", "Vivek Communications", "Anant Trading",
    "Bombay Electronics", "Marina Tech", "Sea Link Gadgets", "Powai Tech Hub",
    "Bandra Bazaar", "Juhu Electronics",
]


async def seed_database(db):
    """Idempotent seed: only seeds if collections are empty."""
    # ============ USERS ============
    # Always iterate users list; per-user existence is checked below
    if True:
        users_to_seed = [
            {"email": "manager@nalanda.com", "password": "Manager@123", "name": "Rajesh Kapoor", "role": "manager", "phone": "+91 98201 11111", "territory": "Mumbai West"},
            {"email": "sales1@nalanda.com", "password": "Sales@123", "name": "Amit Sharma", "role": "sales", "phone": "+91 98202 22222", "territory": "Andheri-Bandra"},
            {"email": "sales2@nalanda.com", "password": "Sales@123", "name": "Priya Iyer", "role": "sales", "phone": "+91 98203 33333", "territory": "Borivali-Malad"},
            {"email": "sales3@nalanda.com", "password": "Sales@123", "name": "Vikram Singh", "role": "sales", "phone": "+91 98204 44444", "territory": "Dadar-Worli"},
            {"email": "accounts@nalanda.com", "password": "Accounts@123", "name": "Neha Patel", "role": "accounts", "phone": "+91 98205 55555", "territory": "Head Office"},
            {"email": "boat@nalanda.com", "password": "Boat@123", "name": "Boat Partner View", "role": "viewer", "phone": "+91 98206 66666", "territory": "External · Boat Co.", "permissions": {"modules": ["dashboard"], "brands": ["Boat"], "view_scope": "totals_only", "customer_visibility": "none", "can_edit": False, "can_create": False, "can_export": False, "can_manage_users": False}},
        ]
        for u in users_to_seed:
            existing = await db.users.find_one({"email": u["email"]})
            if existing:
                continue
            doc = {
                "id": new_id(),
                "email": u["email"],
                "password_hash": hash_password(u["password"]),
                "name": u["name"],
                "role": u["role"],
                "phone": u["phone"],
                "territory": u["territory"],
                "active": True,
                "created_at": now_iso(),
            }
            if u.get("permissions"):
                doc["permissions"] = u["permissions"]
            await db.users.insert_one(doc)

    # Fetch sales users for assignment
    sales_users = await db.users.find({"role": "sales"}, {"_id": 0}).to_list(100)
    if not sales_users:
        return

    # ============ CUSTOMERS ============
    if await db.customers.count_documents({}) == 0:
        random.seed(42)
        customers = []
        for i, prefix in enumerate(CUSTOMER_PREFIXES):
            area_name, lat, lng = random.choice(MUMBAI_AREAS)
            # add slight jitter
            lat += random.uniform(-0.01, 0.01)
            lng += random.uniform(-0.01, 0.01)
            sales_user = sales_users[i % len(sales_users)]
            credit_limit = random.choice([100000, 200000, 300000, 500000, 750000, 1000000])
            cust = {
                "id": new_id(),
                "name": prefix,
                "code": f"NAL-{1000+i}",
                "area": area_name,
                "city": "Mumbai",
                "state": "Maharashtra",
                "contact_person": random.choice(["Mr. Sharma", "Mr. Mehta", "Ms. Joshi", "Mr. Kulkarni", "Mr. Khan", "Ms. Desai"]),
                "phone": f"+91 9{random.randint(8000000000, 9999999999)}",
                "email": f"{prefix.lower().replace(' ', '')}@gmail.com",
                "gstin": f"27{random.choice(['AAACR', 'AABCS', 'AACCT'])}{random.randint(1000, 9999)}P1Z{random.randint(0,9)}",
                "credit_limit": credit_limit,
                "brand_preferences": random.sample(BRANDS, k=random.randint(2, 4)),
                "assigned_to": sales_user["id"],
                "lat": lat,
                "lng": lng,
                "outstanding": 0.0,
                "overdue": 0.0,
                "last_payment_date": None,
                "last_visit_date": (datetime.now(timezone.utc) - timedelta(days=random.randint(0, 30))).isoformat(),
                "last_order_date": (datetime.now(timezone.utc) - timedelta(days=random.randint(0, 45))).isoformat(),
                "total_purchases": 0.0,
                "credit_risk_score": random.randint(20, 90),
                "payment_behaviour_score": random.randint(30, 95),
                "created_at": now_iso(),
            }
            customers.append(cust)
        await db.customers.insert_many(customers)

    customers = await db.customers.find({}, {"_id": 0}).to_list(1000)

    # ============ INVOICES & PAYMENTS ============
    if await db.invoices.count_documents({}) == 0:
        invoices = []
        payments = []
        now = datetime.now(timezone.utc)
        invoice_counter = 1000
        for cust in customers:
            num_invoices = random.randint(4, 12)
            for j in range(num_invoices):
                inv_date = now - timedelta(days=random.randint(0, 120))
                due_date = inv_date + timedelta(days=30)
                brand = random.choice(cust["brand_preferences"])
                num_items = random.randint(1, 4)
                items = []
                total = 0.0
                for _ in range(num_items):
                    prod, price = random.choice(PRODUCTS[brand])
                    qty = random.randint(5, 50)
                    amount = qty * price
                    total += amount
                    items.append({"sku": f"SKU-{random.randint(10000, 99999)}", "product": prod, "brand": brand, "qty": qty, "unit_price": price, "amount": amount})

                # decide status
                days_old = (now - inv_date).days
                paid_amount = 0.0
                if days_old < 15:
                    status = "unpaid"
                elif days_old < 30:
                    status = random.choice(["unpaid", "partial", "paid"])
                else:
                    status = random.choice(["paid", "paid", "paid", "overdue", "partial"])

                if status == "paid":
                    paid_amount = total
                    pay_date = inv_date + timedelta(days=random.randint(15, 45))
                    payments.append({
                        "id": new_id(), "customer_id": cust["id"], "invoice_id": None,
                        "amount": total, "date": pay_date.isoformat(),
                        "method": random.choice(["neft", "rtgs", "upi", "cheque"]),
                        "reference": f"PAY-{random.randint(100000, 999999)}",
                        "notes": "", "created_at": now_iso()
                    })
                elif status == "partial":
                    paid_amount = total * random.uniform(0.3, 0.7)
                    pay_date = inv_date + timedelta(days=random.randint(10, 25))
                    payments.append({
                        "id": new_id(), "customer_id": cust["id"], "invoice_id": None,
                        "amount": paid_amount, "date": pay_date.isoformat(),
                        "method": random.choice(["neft", "upi"]),
                        "reference": f"PAY-{random.randint(100000, 999999)}",
                        "notes": "Part payment", "created_at": now_iso()
                    })

                inv = {
                    "id": new_id(),
                    "customer_id": cust["id"],
                    "invoice_no": f"INV-{datetime.now().year}-{invoice_counter:05d}",
                    "date": inv_date.isoformat(),
                    "due_date": due_date.isoformat(),
                    "items": items,
                    "amount": total,
                    "paid_amount": paid_amount,
                    "status": status,
                    "brand": brand,
                    "created_at": now_iso(),
                }
                invoices.append(inv)
                invoice_counter += 1

        if invoices:
            await db.invoices.insert_many(invoices)
        if payments:
            await db.payments.insert_many(payments)

        # Update customer outstanding/total_purchases
        for cust in customers:
            cust_invoices = [i for i in invoices if i["customer_id"] == cust["id"]]
            total_purchases = sum(i["amount"] for i in cust_invoices)
            outstanding = sum(i["amount"] - i["paid_amount"] for i in cust_invoices if i["status"] != "paid")
            overdue = sum(i["amount"] - i["paid_amount"] for i in cust_invoices if i["status"] == "overdue")
            cust_payments = [p for p in payments if p["customer_id"] == cust["id"]]
            last_payment = max((p["date"] for p in cust_payments), default=None)
            await db.customers.update_one(
                {"id": cust["id"]},
                {"$set": {
                    "total_purchases": total_purchases,
                    "outstanding": outstanding,
                    "overdue": overdue,
                    "last_payment_date": last_payment,
                }}
            )

    # ============ SCHEMES ============
    if await db.schemes.count_documents({}) == 0:
        now = datetime.now(timezone.utc)
        schemes = [
            {"id": new_id(), "name": "Boat Q1 Volume Booster", "brand": "Boat", "type": "volume", "description": "Buy 100+ Airdopes, get 10% extra discount + cashback ₹15,000", "start_date": (now - timedelta(days=20)).isoformat(), "end_date": (now + timedelta(days=40)).isoformat(), "target_amount": 500000, "reward": "10% discount + ₹15,000 cashback", "active": True, "progress": 62.5, "created_at": now_iso()},
            {"id": new_id(), "name": "Fireboltt Smart Watch Push", "brand": "Fireboltt", "type": "product", "description": "Sell 50 Ninja Pro watches in February to unlock incentive", "start_date": (now - timedelta(days=10)).isoformat(), "end_date": (now + timedelta(days=20)).isoformat(), "target_amount": 250000, "reward": "₹25,000 incentive + Goa trip", "active": True, "progress": 38.0, "created_at": now_iso()},
            {"id": new_id(), "name": "Noise ColorFit Quarterly", "brand": "Noise", "type": "value", "description": "₹3L+ purchase in Q1 — earn 2% bonus credit", "start_date": (now - timedelta(days=30)).isoformat(), "end_date": (now + timedelta(days=60)).isoformat(), "target_amount": 300000, "reward": "2% bonus credit", "active": True, "progress": 71.0, "created_at": now_iso()},
            {"id": new_id(), "name": "Logitech MX Series Push", "brand": "Logitech", "type": "incentive", "description": "Top 5 dealers selling MX Master 3S — overseas trip", "start_date": (now - timedelta(days=15)).isoformat(), "end_date": (now + timedelta(days=45)).isoformat(), "target_amount": 150000, "reward": "Bangkok 3N/4D trip", "active": True, "progress": 22.0, "created_at": now_iso()},
            {"id": new_id(), "name": "Amazon Echo Festival Boost", "brand": "Amazon", "type": "volume", "description": "Festival season — Echo Dot bulk orders ≥75 units", "start_date": (now - timedelta(days=5)).isoformat(), "end_date": (now + timedelta(days=25)).isoformat(), "target_amount": 200000, "reward": "Free 10 Fire TV Sticks", "active": True, "progress": 14.0, "created_at": now_iso()},
            {"id": new_id(), "name": "Mivi True Wireless Drive", "brand": "Mivi", "type": "value", "description": "Mivi Earbuds — ₹1L+ purchase for free POS display", "start_date": (now - timedelta(days=25)).isoformat(), "end_date": (now + timedelta(days=35)).isoformat(), "target_amount": 100000, "reward": "Free POS display + Banner", "active": True, "progress": 84.0, "created_at": now_iso()},
        ]
        await db.schemes.insert_many(schemes)

    # ============ TARGETS ============
    if await db.targets.count_documents({}) == 0:
        now = datetime.now(timezone.utc)
        period = now.strftime("%Y-%m")
        for user in sales_users:
            target_amount = random.choice([800000, 1000000, 1200000, 1500000])
            achieved = target_amount * random.uniform(0.4, 0.95)
            await db.targets.insert_one({
                "id": new_id(),
                "user_id": user["id"],
                "period": period,
                "target_amount": target_amount,
                "achieved_amount": achieved,
                "target_collection": target_amount * 0.85,
                "collected_amount": target_amount * 0.85 * random.uniform(0.5, 0.95),
                "created_at": now_iso(),
            })

    # ============ TASKS ============
    if await db.tasks.count_documents({}) == 0:
        now = datetime.now(timezone.utc)
        tasks = []
        for cust in customers[:15]:
            user_id = cust["assigned_to"]
            tasks.append({
                "id": new_id(),
                "assigned_to": user_id,
                "customer_id": cust["id"],
                "title": random.choice([
                    f"Collect overdue payment from {cust['name']}",
                    f"Pitch new Boat Airdopes range to {cust['name']}",
                    f"Follow-up on credit note for {cust['name']}",
                    f"Schedule visit — {cust['area']} cluster",
                    f"Share Q1 scheme details with {cust['name']}",
                ]),
                "description": "",
                "due_date": (now + timedelta(days=random.randint(0, 7))).isoformat(),
                "priority": random.choice(["medium", "high", "urgent", "low"]),
                "status": random.choice(["open", "open", "open", "in_progress"]),
                "created_at": now_iso(),
            })
        await db.tasks.insert_many(tasks)

    # ============ NOTIFICATIONS ============
    if await db.notifications.count_documents({}) == 0:
        now = datetime.now(timezone.utc)
        notes = [
            {"id": new_id(), "user_id": None, "title": "Q1 Scheme Live", "body": "Boat Q1 Volume Booster scheme is now active. Push to all priority customers.", "type": "scheme", "link": "/schemes", "read": False, "created_at": (now - timedelta(hours=2)).isoformat()},
            {"id": new_id(), "user_id": None, "title": "12 Customers Overdue >45 Days", "body": "Critical: 12 customers have invoices overdue beyond 45 days. Total exposure ₹18.2L.", "type": "overdue", "link": "/accounts", "read": False, "created_at": (now - timedelta(hours=5)).isoformat()},
            {"id": new_id(), "user_id": None, "title": "Zoho Sync Successful", "body": "Last sync at 09:30 AM. 47 invoices, 22 payments updated.", "type": "system", "link": None, "read": True, "created_at": (now - timedelta(hours=8)).isoformat()},
            {"id": new_id(), "user_id": None, "title": "Monthly Target Review", "body": "Sales team has achieved 68% of Feb target with 7 days remaining.", "type": "announcement", "link": "/sales", "read": False, "created_at": (now - timedelta(days=1)).isoformat()},
        ]
        await db.notifications.insert_many(notes)

    # ============ VISITS ============
    if await db.visits.count_documents({}) == 0:
        now = datetime.now(timezone.utc)
        visits = []
        for cust in customers[:20]:
            for _ in range(random.randint(1, 3)):
                visits.append({
                    "id": new_id(),
                    "user_id": cust["assigned_to"],
                    "customer_id": cust["id"],
                    "date": (now - timedelta(days=random.randint(0, 30))).isoformat(),
                    "duration_minutes": random.randint(15, 60),
                    "notes": random.choice(["Discussed Q1 scheme", "Collected partial payment", "Customer interested in Logitech range", "Followup for credit note"]),
                    "lat": cust["lat"],
                    "lng": cust["lng"],
                    "outcome": random.choice(["sale", "followup", "collection", "no_response"]),
                    "created_at": now_iso(),
                })
        if visits:
            await db.visits.insert_many(visits)
