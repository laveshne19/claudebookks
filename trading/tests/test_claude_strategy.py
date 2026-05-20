from types import SimpleNamespace

from app.models import Side
from app.strategy.claude_strategy import ClaudeStrategy


class FakeClient:
    """Stand-in for anthropic.Anthropic that returns a canned text block."""

    def __init__(self, text):
        self._text = text
        self.calls = 0
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.calls += 1
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=self._text)])


def make(text, holding=False, interval=300):
    closes = [100 + i * 0.1 for i in range(40)]
    s = ClaudeStrategy(api_key="", model="m", decision_interval=interval, client=FakeClient(text))
    return s, closes


def test_parse_buy():
    s, closes = make('{"action":"BUY","reason":"momentum up"}')
    sig = s.evaluate("RELIANCE", closes, holding=False)
    assert sig.side is Side.BUY and "Claude" in sig.reason


def test_parse_sell_only_when_holding():
    s, closes = make('{"action":"SELL","reason":"trend break"}')
    assert s.evaluate("X", closes, holding=False).side is None  # can't sell what we don't hold
    s2, closes2 = make('{"action":"SELL","reason":"trend break"}')
    assert s2.evaluate("X", closes2, holding=True).side is Side.SELL


def test_hold_returns_no_action():
    s, closes = make('{"action":"HOLD","reason":"choppy"}')
    assert s.evaluate("X", closes, holding=False).side is None


def test_json_embedded_in_prose_is_parsed():
    s, closes = make('Here is my call: {"action":"BUY","reason":"ok"} done')
    assert s.evaluate("X", closes, holding=False).side is Side.BUY


def test_bad_json_defaults_to_hold():
    s, closes = make("not json at all")
    assert s.evaluate("X", closes, holding=False).side is None


def test_cooldown_blocks_second_call():
    s, closes = make('{"action":"BUY","reason":"x"}', interval=300)
    s.evaluate("X", closes, holding=False)
    assert s._client.calls == 1
    # immediate second eval should be in cooldown -> no new API call
    sig = s.evaluate("X", closes, holding=False)
    assert sig.side is None and s._client.calls == 1


def test_warmup_no_call():
    s = ClaudeStrategy(api_key="", model="m", client=FakeClient('{"action":"BUY"}'))
    sig = s.evaluate("X", [100, 101], holding=False)
    assert sig.side is None and s._client.calls == 0


def test_no_client_holds():
    s = ClaudeStrategy(api_key="", model="m", client=None)
    closes = [100 + i for i in range(40)]
    assert s.evaluate("X", closes, holding=False).side is None
