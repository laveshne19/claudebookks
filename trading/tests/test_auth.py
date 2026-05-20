import time

from app import auth


def test_password_hash_roundtrip():
    h = auth.hash_password("s3cret")
    assert auth.verify_password("s3cret", h)
    assert not auth.verify_password("wrong", h)


def test_token_roundtrip_and_tamper():
    secret = "topsecretkey"
    tok = auth.issue_token("admin", secret)
    assert auth.verify_token(tok, secret) == "admin"
    # wrong secret rejected
    assert auth.verify_token(tok, "othersecret") is None
    # tampered body rejected
    body, sig = tok.split(".", 1)
    assert auth.verify_token("x" + body + "." + sig, secret) is None


def test_token_expiry():
    secret = "k"
    tok = auth.issue_token("admin", secret, ttl=-1)
    assert auth.verify_token(tok, secret) is None


def test_garbage_token():
    assert auth.verify_token("not-a-token", "k") is None
    assert auth.verify_token("", "k") is None
