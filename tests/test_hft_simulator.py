import pytest
import time
from hft_simulator import MatchingEngine, LimitOrder

def test_matching_engine_initialization():
    engine = MatchingEngine(ticker="NIFTY", base_price=22000.0)
    assert engine.ticker == "NIFTY"
    assert len(engine.bids) > 0
    assert len(engine.asks) > 0
    
    # Verify bid sorting: descending price, then ascending timestamp
    for i in range(len(engine.bids) - 1):
        assert engine.bids[i].price >= engine.bids[i+1].price
        if engine.bids[i].price == engine.bids[i+1].price:
            assert engine.bids[i].timestamp <= engine.bids[i+1].timestamp

    # Verify ask sorting: ascending price, then ascending timestamp
    for i in range(len(engine.asks) - 1):
        assert engine.asks[i].price <= engine.asks[i+1].price
        if engine.asks[i].price == engine.asks[i+1].price:
            assert engine.asks[i].timestamp <= engine.asks[i+1].timestamp

def test_limit_buy_order_queueing():
    engine = MatchingEngine(ticker="NIFTY", base_price=22000.0)
    best_bid = engine.get_best_bid()
    best_ask = engine.get_best_ask()
    
    # Place a buy order below the best ask (should queue, not execute)
    target_price = best_bid - 10.0
    qty = 50
    trades = engine.add_limit_order(target_price, qty, side="buy", is_user=True)
    
    assert len(trades) == 0
    # Check that it is added to bids
    user_bids = [o for o in engine.bids if o.is_user]
    assert len(user_bids) == 1
    assert user_bids[0].price == target_price
    assert user_bids[0].qty == qty

def test_limit_buy_order_execution():
    engine = MatchingEngine(ticker="NIFTY", base_price=22000.0)
    best_ask = engine.get_best_ask()
    
    # Place a buy order at the best ask price to trigger a trade
    target_price = best_ask
    qty = 10
    
    trades = engine.add_limit_order(target_price, qty, side="buy", is_user=True)
    assert len(trades) > 0
    assert sum(t["qty"] for t in trades) == qty
    assert trades[0]["price"] == best_ask
    assert trades[0]["buyer"] == "USER"

def test_limit_sell_order_queueing():
    engine = MatchingEngine(ticker="NIFTY", base_price=22000.0)
    best_bid = engine.get_best_bid()
    best_ask = engine.get_best_ask()
    
    # Place a sell order above the best bid (should queue, not execute)
    target_price = best_ask + 10.0
    qty = 50
    trades = engine.add_limit_order(target_price, qty, side="sell", is_user=True)
    
    assert len(trades) == 0
    # Check that it is added to asks
    user_asks = [o for o in engine.asks if o.is_user]
    assert len(user_asks) == 1
    assert user_asks[0].price == target_price
    assert user_asks[0].qty == qty

def test_limit_sell_order_execution():
    engine = MatchingEngine(ticker="NIFTY", base_price=22000.0)
    best_bid = engine.get_best_bid()
    
    # Place a sell order at the best bid price to trigger a trade
    target_price = best_bid
    qty = 10
    
    trades = engine.add_limit_order(target_price, qty, side="sell", is_user=True)
    assert len(trades) > 0
    assert sum(t["qty"] for t in trades) == qty
    assert trades[0]["price"] == best_bid
    assert trades[0]["seller"] == "USER"

def test_market_buy_order_sweeping():
    engine = MatchingEngine(ticker="NIFTY", base_price=22000.0)
    best_ask = engine.get_best_ask()
    second_best_ask = engine.asks[1].price
    
    # Place a market buy order that requires sweeping multiple asks
    qty = engine.asks[0].qty + 10
    
    trades = engine.add_market_order(qty, side="buy", is_user=True)
    assert len(trades) >= 2
    assert sum(t["qty"] for t in trades) == qty
    assert trades[0]["price"] == best_ask
    assert trades[1]["price"] == second_best_ask

def test_market_sell_order_sweeping():
    engine = MatchingEngine(ticker="NIFTY", base_price=22000.0)
    best_bid = engine.get_best_bid()
    second_best_bid = engine.bids[1].price
    
    # Place a market sell order that requires sweeping multiple bids
    qty = engine.bids[0].qty + 10
    
    trades = engine.add_market_order(qty, side="sell", is_user=True)
    assert len(trades) >= 2
    assert sum(t["qty"] for t in trades) == qty
    assert trades[0]["price"] == best_bid
    assert trades[1]["price"] == second_best_bid

def test_cancel_order():
    engine = MatchingEngine(ticker="NIFTY", base_price=22000.0)
    best_bid = engine.get_best_bid()
    
    # Queue a limit order
    trades = engine.add_limit_order(best_bid - 5.0, 50, side="buy", is_user=True)
    assert len(trades) == 0
    
    user_order = [o for o in engine.bids if o.is_user][0]
    order_id = user_order.order_id
    
    # Cancel it
    assert engine.cancel_order(order_id) is True
    # Make sure it's gone
    assert len([o for o in engine.bids if o.is_user]) == 0
    # Try cancelling a non-existent one
    assert engine.cancel_order("non_existent_id") is False

def test_simulate_background_hft_activity():
    engine = MatchingEngine(ticker="NIFTY", base_price=22000.0)
    
    # Run simulation a few times
    for _ in range(5):
        engine.simulate_background_hft_activity()
        
    # Invariant checks: book must remain sorted correctly
    for i in range(len(engine.bids) - 1):
        assert engine.bids[i].price >= engine.bids[i+1].price
    for i in range(len(engine.asks) - 1):
        assert engine.asks[i].price <= engine.asks[i+1].price
