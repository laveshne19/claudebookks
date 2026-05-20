from app.brokers.paper import PaperBroker
from app.models import OrderStatus, Side


def test_buy_then_sell_realizes_pnl():
    b = PaperBroker(starting_cash=100_000)
    o = b.place_order("RELIANCE", Side.BUY, 10, 2900, "entry")
    assert o.status is OrderStatus.FILLED
    assert b.cash() == 100_000 - 29_000
    pos = b.get_position("RELIANCE")
    assert pos.qty == 10 and pos.avg_price == 2900

    s = b.place_order("RELIANCE", Side.SELL, 10, 2950, "exit")
    assert s.status is OrderStatus.FILLED
    assert round(b.last_realized_pnl, 2) == 500.0
    assert b.get_position("RELIANCE") is None
    assert round(b.cash(), 2) == round(100_000 + 500, 2)


def test_buy_rejected_when_insufficient_cash():
    b = PaperBroker(starting_cash=1_000)
    o = b.place_order("TCS", Side.BUY, 10, 3850, "too big")
    assert o.status is OrderStatus.REJECTED
    assert b.cash() == 1_000


def test_sell_rejected_without_position():
    b = PaperBroker(starting_cash=10_000)
    o = b.place_order("INFY", Side.SELL, 5, 1500, "no holding")
    assert o.status is OrderStatus.REJECTED


def test_averaging_up():
    b = PaperBroker(starting_cash=100_000)
    b.place_order("SBIN", Side.BUY, 10, 800, "first")
    b.place_order("SBIN", Side.BUY, 10, 820, "second")
    pos = b.get_position("SBIN")
    assert pos.qty == 20
    assert pos.avg_price == 810
