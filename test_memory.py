from order_memory import extract_and_store, get_context, clear


def test_stores_order_id():
    extract_and_store("sess-1", "What about order DM-1037?")
    assert get_context("sess-1")["active_order_id"] == "DM-1037"


def test_clears_on_session_end():
    extract_and_store("sess-2", "order DM-0001")
    clear("sess-2")
    assert get_context("sess-2") == {}


def test_no_order_leaves_context_empty():
    extract_and_store("sess-3", "Hello, is the system online?")
    assert "active_order_id" not in get_context("sess-3")