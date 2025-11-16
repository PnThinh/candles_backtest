import json
import asyncio
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

class BacktestConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        await self.accept()
        self.data = []
        self.pointer = 0
        self.is_running = False
        self.speed = 1
        self.positions = []
        self.next_position_id = 1
        self.current_time = 0
        self.current_price = 0
        self.closed_positions = []  # Track closed positions for statistics
        self.stream_task = None  # Track the streaming task
        await self.channel_layer.group_add("backtest.group", self.channel_name)
        await self.send_json({"status": "connected"})

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("backtest.group", self.channel_name)

    async def receive_json(self, content):
        action = content.get("action")
        try:
            if action == "load":
                filepath = content.get("file", "market/data/temp.json")
                await self.load_file(filepath)
                await self.send_json({"status": "loaded", "total": len(self.data)})
            elif action == "start":
                if not self.is_running:
                    self.is_running = True
                    # Cancel existing task if any
                    if self.stream_task and not self.stream_task.done():
                        self.stream_task.cancel()
                    # Create new streaming task
                    self.stream_task = asyncio.create_task(self.stream_loop())
                    await self.send_json({"status": "started"})
                else:
                    await self.send_json({"status": "already_running"})
            elif action == "stop":
                self.is_running = False
                # Cancel the streaming task
                if self.stream_task and not self.stream_task.done():
                    self.stream_task.cancel()
                    self.stream_task = None
                await self.send_json({"status": "stopped"})
            elif action == "set_speed":
                self.speed = float(content.get("speed", 1))
                await self.send_json({"status": "speed_changed", "speed": self.speed})
            elif action == "jump":
                idx = int(content.get("index", 0))
                self.pointer = max(0, min(idx, len(self.data)-1))
                await self.send_json({"status": "jumped", "pointer": self.pointer})
            elif action == "place_order":
                await self.place_order(
                    content.get("side"),
                    content.get("quantity"),
                    content.get("price"),
                    content.get("tp"),
                    content.get("sl")
                )
            elif action == "close_position":
                await self.close_position(content.get("position_id"))
        except Exception as e:
            await self.send_json({"status": "error", "message": str(e)})

    async def load_file(self, filepath):
        # allow relative path from app dir
        p = BASE_DIR / Path(filepath)
        try:
            with open(p, "r") as f:
                raw_data = json.load(f)
            
            # Convert from dict of arrays to array of objects
            if isinstance(raw_data, dict) and 'time' in raw_data:
                times = raw_data['time']
                opens = raw_data['open']
                highs = raw_data['high']
                lows = raw_data['low']
                closes = raw_data['close']
                
                self.data = []
                for i in range(len(times)):
                    self.data.append({
                        'time': times[i] / 1000,  # convert ms to seconds
                        'open': opens[i],
                        'high': highs[i],
                        'low': lows[i],
                        'close': closes[i]
                    })
            else:
                self.data = raw_data
                
            self.pointer = 0
        except Exception as e:
            await self.send_json({"status": "error", "message": str(e)})
            raise

    async def stream_loop(self):
        try:
            while self.is_running and self.pointer < len(self.data):
                candle = self.data[self.pointer]
                self.current_time = candle['time']
                self.current_price = candle['close']
                
                # Check if any positions hit TP or SL
                await self.check_positions(candle)
                
                await self.channel_layer.group_send(
                    "backtest.group",
                    {"type": "send.candle", "candle": candle}
                )
                self.pointer += 1
                await asyncio.sleep(1 / self.speed)
            
            # Mark as not running when loop ends
            self.is_running = False
            
            # Save closed positions to file when stream ends
            if self.pointer >= len(self.data):
                await self.save_closed_positions()
        except asyncio.CancelledError:
            # Task was cancelled, clean up
            self.is_running = False
            raise
        except Exception as e:
            self.is_running = False
            await self.send_json({"status": "error", "message": str(e)})

    async def send_candle(self, event):
        await self.send_json({"type": "candle", "data": event["candle"]})
    
    async def place_order(self, side, quantity, price, tp=None, sl=None):
        position = {
            "id": self.next_position_id,
            "side": side,
            "quantity": float(quantity),
            "entry_price": float(price),
            "tp": float(tp) if tp else None,
            "sl": float(sl) if sl else None,
            "time": self.current_time
        }
        self.positions.append(position)
        self.next_position_id += 1
        
        await self.send_json({
            "type": "order_placed",
            "position": position
        })
    
    async def close_position(self, position_id):
        # Find the position before removing
        pos = next((p for p in self.positions if p["id"] == position_id), None)
        
        if pos:
            # Calculate P&L at current price
            entry = float(pos['entry_price'])
            exit_price = self.current_price
            side = pos['side']
            pnl = (exit_price - entry) * float(pos['quantity']) * (1 if side == 'buy' else -1)
            
            # Save to closed positions
            closed_pos = {
                **pos,
                'exit_price': exit_price,
                'exit_time': self.current_time,
                'exit_reason': 'Manual',
                'pnl': pnl
            }
            self.closed_positions.append(closed_pos)
            
            # Notify client about manual close
            await self.send_json({
                "type": "position_closed_manual",
                "position_id": position_id,
                "exit_price": exit_price,
                "pnl": pnl
            })
        
        # Remove from active positions
        self.positions = [p for p in self.positions if p["id"] != position_id]
        
        await self.send_json({
            "type": "position_closed",
            "position_id": position_id
        })
    
    async def check_positions(self, candle):
        """Check if any position hits TP or SL"""
        high = float(candle['high'])
        low = float(candle['low'])
        close = float(candle['close'])
        
        positions_to_close = []
        
        for pos in self.positions:
            tp = float(pos.get('tp')) if pos.get('tp') else None
            sl = float(pos.get('sl')) if pos.get('sl') else None
            side = pos['side']
            entry = float(pos['entry_price'])
            
            hit_tp = False
            hit_sl = False
            exit_price = close
            
            if side == 'buy':
                # Long position
                if tp and high >= tp:
                    hit_tp = True
                    exit_price = tp
                elif sl and low <= sl:
                    hit_sl = True
                    exit_price = sl
            else:
                # Short position
                if tp and low <= tp:
                    hit_tp = True
                    exit_price = tp
                elif sl and high >= sl:
                    hit_sl = True
                    exit_price = sl
            
            if hit_tp or hit_sl:
                # Calculate P&L
                pnl = (exit_price - entry) * pos['quantity'] * (1 if side == 'buy' else -1)
                
                # Save closed position
                closed_pos = {
                    **pos,
                    'exit_price': exit_price,
                    'exit_time': candle['time'],
                    'exit_reason': 'TP' if hit_tp else 'SL',
                    'pnl': pnl
                }
                self.closed_positions.append(closed_pos)
                positions_to_close.append(pos['id'])
                
                # Notify client
                await self.send_json({
                    "type": "position_hit",
                    "position_id": pos['id'],
                    "reason": 'TP' if hit_tp else 'SL',
                    "exit_price": exit_price,
                    "pnl": pnl
                })
        
        # Remove closed positions
        for pos_id in positions_to_close:
            self.positions = [p for p in self.positions if p['id'] != pos_id]
    
    async def save_closed_positions(self):
        """Save closed positions to file for statistics"""
        try:
            filepath = BASE_DIR / 'data' / 'temp_position.json'
            filepath.parent.mkdir(exist_ok=True)
            
            with open(filepath, 'w') as f:
                json.dump(self.closed_positions, f, indent=2)
            
            # Calculate statistics
            total_trades = len(self.closed_positions)
            if total_trades > 0:
                total_pnl = sum(p['pnl'] for p in self.closed_positions)
                wins = len([p for p in self.closed_positions if p['pnl'] > 0])
                losses = len([p for p in self.closed_positions if p['pnl'] < 0])
                win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
                
                stats = {
                    'total_trades': total_trades,
                    'wins': wins,
                    'losses': losses,
                    'win_rate': win_rate,
                    'total_pnl': total_pnl
                }
                
                await self.send_json({
                    "type": "backtest_stats",
                    "stats": stats
                })
        except Exception as e:
            print(f"Error saving positions: {e}")
