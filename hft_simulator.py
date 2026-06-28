"""
HFT Limit Order Book (LOB) & Matching Simulator.
Features a pure-Python matching engine, synthetic quote generator,
latency-induced slippage modeling, and interactive order placement.
"""

import time
import random
import uuid
import pandas as pd
import streamlit as st

class LimitOrder:
    def __init__(self, price, qty, side, is_user=False, timestamp=None):
        self.order_id = str(uuid.uuid4())[:8]
        self.price = round(float(price), 2)
        self.qty = int(qty)
        self.side = side.lower()  # 'buy' or 'sell'
        self.is_user = is_user
        self.timestamp = timestamp or time.time()

    def __repr__(self):
        return f"[{'USER' if self.is_user else 'MOCK'}] {self.side.upper()} {self.qty} @ {self.price:.2f}"

class MatchingEngine:
    def __init__(self, ticker="NIFTY", base_price=22000.0):
        self.ticker = ticker
        self.base_price = base_price
        # bids sorted descending (highest buy price first), then timestamp ascending
        self.bids = []
        # asks sorted ascending (lowest sell price first), then timestamp ascending
        self.asks = []
        # trade history: list of dicts
        self.trades = []
        # Initialize order book with some initial depth
        self.reset_book()

    def reset_book(self):
        self.bids.clear()
        self.asks.clear()
        self.trades.clear()
        
        # Seed bids and asks around the base price
        spread = 0.05
        step = 0.05
        price = self.base_price
        
        # Buy orders (bids) below base price
        for i in range(1, 11):
            bid_price = round(price - (spread / 2) - (i - 1) * step * random.uniform(0.8, 1.2), 2)
            bid_qty = random.randint(10, 200)
            self.bids.append(LimitOrder(bid_price, bid_qty, "buy"))
            
        # Sell orders (asks) above base price
        for i in range(1, 11):
            ask_price = round(price + (spread / 2) + (i - 1) * step * random.uniform(0.8, 1.2), 2)
            ask_qty = random.randint(10, 200)
            self.asks.append(LimitOrder(ask_price, ask_qty, "sell"))
            
        self.sort_book()

    def sort_book(self):
        # bids: highest price first, then oldest first
        self.bids.sort(key=lambda o: (-o.price, o.timestamp))
        # asks: lowest price first, then oldest first
        self.asks.sort(key=lambda o: (o.price, o.timestamp))

    def get_best_bid(self):
        return self.bids[0].price if self.bids else None

    def get_best_ask(self):
        return self.asks[0].price if self.asks else None

    def add_limit_order(self, price, qty, side, is_user=False):
        order = LimitOrder(price, qty, side, is_user=is_user)
        matched_trades = []
        
        if side.lower() == "buy":
            # Match against asks
            while qty > 0 and self.asks and self.asks[0].price <= price:
                best_ask = self.asks[0]
                trade_qty = min(qty, best_ask.qty)
                trade_price = best_ask.price
                
                matched_trades.append({
                    "price": trade_price,
                    "qty": trade_qty,
                    "buyer": "USER" if is_user else "HFT_BOT",
                    "seller": "USER" if best_ask.is_user else "HFT_BOT",
                    "timestamp": time.time(),
                })
                
                qty -= trade_qty
                best_ask.qty -= trade_qty
                if best_ask.qty == 0:
                    self.asks.pop(0)
            
            # If remaining qty, add to bids
            if qty > 0:
                order.qty = qty
                self.bids.append(order)
                
        else:  # sell side
            # Match against bids
            while qty > 0 and self.bids and self.bids[0].price >= price:
                best_bid = self.bids[0]
                trade_qty = min(qty, best_bid.qty)
                trade_price = best_bid.price
                
                matched_trades.append({
                    "price": trade_price,
                    "qty": trade_qty,
                    "buyer": "USER" if best_bid.is_user else "HFT_BOT",
                    "seller": "USER" if is_user else "HFT_BOT",
                    "timestamp": time.time(),
                })
                
                qty -= trade_qty
                best_bid.qty -= trade_qty
                if best_bid.qty == 0:
                    self.bids.pop(0)
                    
            # If remaining qty, add to asks
            if qty > 0:
                order.qty = qty
                self.asks.append(order)

        self.sort_book()
        self.trades.extend(matched_trades)
        return matched_trades

    def add_market_order(self, qty, side, is_user=False):
        matched_trades = []
        
        if side.lower() == "buy":
            while qty > 0 and self.asks:
                best_ask = self.asks[0]
                trade_qty = min(qty, best_ask.qty)
                trade_price = best_ask.price
                
                matched_trades.append({
                    "price": trade_price,
                    "qty": trade_qty,
                    "buyer": "USER" if is_user else "HFT_BOT",
                    "seller": "USER" if best_ask.is_user else "HFT_BOT",
                    "timestamp": time.time(),
                })
                
                qty -= trade_qty
                best_ask.qty -= trade_qty
                if best_ask.qty == 0:
                    self.asks.pop(0)
        else:  # sell side
            while qty > 0 and self.bids:
                best_bid = self.bids[0]
                trade_qty = min(qty, best_bid.qty)
                trade_price = best_bid.price
                
                matched_trades.append({
                    "price": trade_price,
                    "qty": trade_qty,
                    "buyer": "USER" if best_bid.is_user else "HFT_BOT",
                    "seller": "USER" if is_user else "HFT_BOT",
                    "timestamp": time.time(),
                })
                
                qty -= trade_qty
                best_bid.qty -= trade_qty
                if best_bid.qty == 0:
                    self.bids.pop(0)
                    
        self.sort_book()
        self.trades.extend(matched_trades)
        return matched_trades

    def cancel_order(self, order_id):
        # Search bids
        for i, order in enumerate(self.bids):
            if order.order_id == order_id:
                self.bids.pop(i)
                return True
        # Search asks
        for i, order in enumerate(self.asks):
            if order.order_id == order_id:
                self.asks.pop(i)
                return True
        return False

    def simulate_background_hft_activity(self):
        """Place random limit orders and cancellations to make the book dynamic."""
        best_bid = self.get_best_bid() or self.base_price
        best_ask = self.get_best_ask() or self.base_price
        mid = (best_bid + best_ask) / 2
        
        # 1. Cancel some random non-user orders
        non_user_bids = [o for o in self.bids if not o.is_user]
        non_user_asks = [o for o in self.asks if not o.is_user]
        
        if non_user_bids and random.random() < 0.3:
            self.cancel_order(random.choice(non_user_bids).order_id)
        if non_user_asks and random.random() < 0.3:
            self.cancel_order(random.choice(non_user_asks).order_id)
            
        # 2. Place random bids and asks around the spread
        step = 0.05
        for _ in range(random.randint(1, 3)):
            if random.random() < 0.5:
                # Add bid
                price = round(mid - step * random.uniform(0.5, 4.0), 2)
                qty = random.randint(5, 100)
                self.add_limit_order(price, qty, "buy")
            else:
                # Add ask
                price = round(mid + step * random.uniform(0.5, 4.0), 2)
                qty = random.randint(5, 100)
                self.add_limit_order(price, qty, "sell")

def render_hft_simulator():
    st.markdown("### ⚡ High-Frequency Trading (HFT) Matching Simulator")
    st.markdown(
        "Experience order matching dynamics and how transmission latency "
        "triggers execution price slippage against a simulated Limit Order Book (LOB)."
    )

    # State initialization
    if "engine" not in st.session_state:
        st.session_state.engine = MatchingEngine(ticker="NIFTY", base_price=22000.0)
    
    engine = st.session_state.engine

    # Layout: Control panel on left, Order Book / logs on right
    c1, c2 = st.columns([1, 1.8])

    with c1:
        st.markdown("##### Order Placement Console")
        
        ticker = st.selectbox("Symbol Target", ["NIFTY", "RELIANCE", "HDFCBANK", "TCS"], index=0)
        if ticker != engine.ticker:
            base_prices = {"NIFTY": 22000.0, "RELIANCE": 2900.0, "HDFCBANK": 1500.0, "TCS": 3800.0}
            st.session_state.engine = MatchingEngine(ticker=ticker, base_price=base_prices[ticker])
            engine = st.session_state.engine
            st.rerun()

        # Inputs for mock orders
        side = st.radio("Transaction Side", ["Buy", "Sell"], horizontal=True)
        order_type = st.radio("Order Execution Type", ["Limit", "Market"], horizontal=True)
        
        best_bid = engine.get_best_bid() or engine.base_price
        best_ask = engine.get_best_ask() or engine.base_price
        spread = best_ask - best_bid
        
        st.metric("Spread Detail", f"Bid: {best_bid:.2f} | Ask: {best_ask:.2f}", f"Spread: {spread:.2f}")

        # Limit price input (only for Limit orders)
        price_val = best_bid if side == "Buy" else best_ask
        if order_type == "Limit":
            price = st.number_input(
                "Limit Price (₹)", 
                value=float(price_val), 
                step=0.05, 
                format="%.2f"
            )
        else:
            price = None

        qty = st.number_input("Order Quantity (Shares)", min_value=1, max_value=5000, value=100, step=10)
        
        # Latency slider
        latency = st.select_slider(
            "Transmission Latency",
            options=["Co-location (1ms)", "Corporate API (20ms)", "Retail Fiber (50ms)", "Retail Mobile (200ms)"],
            value="Retail Fiber (50ms)"
        )
        
        # Map selected label to milliseconds
        latency_ms_map = {
            "Co-location (1ms)": 1,
            "Corporate API (20ms)": 20,
            "Retail Fiber (50ms)": 50,
            "Retail Mobile (200ms)": 200
        }
        latency_ms = latency_ms_map[latency]

        # Trigger button
        place_order_btn = st.button("Transmit Order to Exchange", type="primary", use_container_width=True)
        
        st.markdown("---")
        # Action controls
        col_act1, col_act2 = st.columns(2)
        with col_act1:
            if st.button("Generate Market Activity", use_container_width=True):
                engine.simulate_background_hft_activity()
                st.toast("Simulated HFT quote changes updated!")
                st.rerun()
        with col_act2:
            if st.button("Reset Order Book", use_container_width=True):
                engine.reset_book()
                st.toast("Order book reset to default!")
                st.rerun()

    with c2:
        # If user placed an order, process it with simulated latency
        if place_order_btn:
            # Capturing the pre-execution best price to evaluate slippage
            target_best_price = best_ask if side == "Buy" else best_bid
            
            # LATENCY SIMULATION:
            # During the latency window, other high-frequency participants modify the book!
            # The higher the latency, the more the book shifts before the user's order arrives.
            shifts = max(1, int(latency_ms / 15))  # ~1 shift per 15ms
            for _ in range(shifts):
                engine.simulate_background_hft_activity()
                
            # Process order
            start_time = time.time()
            if order_type == "Limit":
                trades = engine.add_limit_order(price, qty, side, is_user=True)
            else:
                trades = engine.add_market_order(qty, side, is_user=True)
            execution_time = (time.time() - start_time) * 1000 + latency_ms
            
            # Display results
            if trades:
                total_traded = sum(t["qty"] for t in trades)
                avg_exec_price = sum(t["price"] * t["qty"] for t in trades) / total_traded
                
                # Slippage calculations
                price_diff = abs(avg_exec_price - target_best_price)
                slippage_pct = (price_diff / target_best_price) * 100
                
                st.success(
                    f"✅ Order Executed!\n\n"
                    f"Traded {total_traded} shares at Average Price: ₹{avg_exec_price:.2f}.\n\n"
                    f"Total Latency: {execution_time:.1f}ms | Slippage: {slippage_pct:.3f}%"
                )
            else:
                if order_type == "Limit":
                    st.info(f"Limit order for {qty} shares placed at ₹{price:.2f} (unfilled, waiting in queue).")
                else:
                    st.warning("Order Cancelled/Failed: Insufficient liquidity on the opposite side of the book.")

        # Render Live Limit Order Book
        st.markdown("##### Live Limit Order Book (LOB)")
        
        # Display Bids and Asks side-by-side or as a ladder
        bid_df = pd.DataFrame([{"Price": o.price, "Qty": o.qty, "Owner": "USER" if o.is_user else "HFT"} for o in engine.bids[:10]])
        ask_df = pd.DataFrame([{"Price": o.price, "Qty": o.qty, "Owner": "USER" if o.is_user else "HFT"} for o in engine.asks[:10]])

        col_bid, col_ask = st.columns(2)
        
        with col_bid:
            st.markdown("<h6 style='color:#22b573;text-align:center;'>BUY BIDS (Demand)</h6>", unsafe_allow_html=True)
            if not bid_df.empty:
                st.dataframe(
                    bid_df.style.background_gradient(subset=["Qty"], cmap="Greens"),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.caption("No buy orders")
                
        with col_ask:
            st.markdown("<h6 style='color:#f85149;text-align:center;'>SELL ASKS (Supply)</h6>", unsafe_allow_html=True)
            if not ask_df.empty:
                st.dataframe(
                    ask_df.style.background_gradient(subset=["Qty"], cmap="Reds"),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.caption("No sell orders")

        # Live Trade log
        st.markdown("##### Recent Execution Log")
        if engine.trades:
            trade_df = pd.DataFrame(engine.trades[-8:])
            trade_df["time"] = trade_df["timestamp"].apply(lambda t: pd.to_datetime(t, unit="s").strftime("%H:%M:%S"))
            trade_df = trade_df[["time", "price", "qty", "buyer", "seller"]]
            st.dataframe(trade_df.iloc[::-1], use_container_width=True, hide_index=True)
        else:
            st.caption("No executions in this session yet.")
