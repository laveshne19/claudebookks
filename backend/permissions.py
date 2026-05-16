"""Granular permissions for Nalanda ERP.

Roles bundle a default permission profile. Admins can override any field per-user.
Permissions are read by routes to filter response data.
"""
from typing import Optional, List

# Module keys that map to sidebar nav and route guards
ALL_MODULES = ["dashboard", "customers", "sales", "accounts", "schemes", "route", "reports", "admin", "notifications", "attendance"]

ALL_BRANDS = ["Boat", "Fireboltt", "Noise", "Logitech", "Amazon", "Swiss Military", "Mivi"]

# View scope:
#   "full"            - sees customer-level detail
#   "aggregate_only"  - sees only aggregate / total numbers, no customer names
#   "totals_only"     - sees only top-level totals (e.g. day-wise total ₹)
VIEW_SCOPES = ["full", "aggregate_only", "totals_only"]

# Customer visibility:
#   "assigned" - only their own assigned customers
#   "all"      - all customers
#   "none"     - no customer list access (aggregate-only role like Boat partner)
CUSTOMER_VIS = ["assigned", "all", "none"]


def default_permissions(role: str) -> dict:
    if role == "super_admin":
        return {
            "modules": ALL_MODULES.copy(),
            "brands": [],  # empty = all
            "view_scope": "full",
            "customer_visibility": "all",
            "can_edit": True,
            "can_create": True,
            "can_export": True,
            "can_manage_users": True,
        }
    if role == "admin":
        return {
            "modules": [m for m in ALL_MODULES if m != "admin"] + ["admin"],
            "brands": [],
            "view_scope": "full",
            "customer_visibility": "all",
            "can_edit": True,
            "can_create": True,
            "can_export": True,
            "can_manage_users": True,
        }
    if role == "manager":
        return {
            "modules": ["dashboard", "customers", "sales", "accounts", "schemes", "route", "reports", "notifications", "attendance"],
            "brands": [],
            "view_scope": "full",
            "customer_visibility": "all",
            "can_edit": True,
            "can_create": True,
            "can_export": True,
            "can_manage_users": False,
        }
    if role == "sales":
        return {
            "modules": ["dashboard", "customers", "sales", "schemes", "route", "notifications", "attendance"],
            "brands": [],
            "view_scope": "full",
            "customer_visibility": "assigned",
            "can_edit": True,
            "can_create": True,
            "can_export": False,
            "can_manage_users": False,
        }
    if role == "accounts":
        return {
            "modules": ["dashboard", "customers", "accounts", "reports", "notifications"],
            "brands": [],
            "view_scope": "full",
            "customer_visibility": "all",
            "can_edit": True,
            "can_create": True,
            "can_export": True,
            "can_manage_users": False,
        }
    if role == "viewer":
        # Read-only external partner — e.g. brand company viewing only their brand sales
        return {
            "modules": ["dashboard"],
            "brands": [],
            "view_scope": "totals_only",
            "customer_visibility": "none",
            "can_edit": False,
            "can_create": False,
            "can_export": False,
            "can_manage_users": False,
        }
    return {
        "modules": ["dashboard"],
        "brands": [],
        "view_scope": "totals_only",
        "customer_visibility": "none",
        "can_edit": False,
        "can_create": False,
        "can_export": False,
        "can_manage_users": False,
    }


def merge_permissions(role: str, custom: Optional[dict]) -> dict:
    base = default_permissions(role)
    if not custom:
        return base
    out = dict(base)
    for k in ("modules", "brands", "view_scope", "customer_visibility", "can_edit", "can_create", "can_export", "can_manage_users"):
        if k in custom and custom[k] is not None:
            out[k] = custom[k]
    return out


def user_permissions(user: dict) -> dict:
    """Compute effective permissions for a user document."""
    return merge_permissions(user.get("role", "viewer"), user.get("permissions"))


def can_access_module(user: dict, module: str) -> bool:
    return module in user_permissions(user)["modules"]


def filter_invoices_by_brands(invoices: list, brands: List[str]) -> list:
    if not brands:
        return invoices
    bset = set(brands)
    return [i for i in invoices if i.get("brand") in bset or any(it.get("brand") in bset for it in i.get("items", []))]


def filter_customers_by_brands(customers: list, brands: List[str]) -> list:
    if not brands:
        return customers
    bset = set(brands)
    return [c for c in customers if any(b in bset for b in c.get("brand_preferences", []))]
