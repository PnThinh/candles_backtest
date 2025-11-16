# Backtest Trading System

Hệ thống backtest và mô phỏng giao dịch theo thời gian thực sử dụng Django + Channels + WebSocket và lightweight-charts.

## 📋 Tổng quan

Dự án này là một ứng dụng web cho phép:
- Tải dữ liệu lịch sử từ TwelveData API
- Phát lại dữ liệu nến (candlestick) theo thời gian thực
- Mô phỏng giao dịch với Take Profit (TP) và Stop Loss (SL)
- Theo dõi P&L và thống kê backtest
- Giao diện giống TradingView với markers, price lines và zones

## 🛠️ Công nghệ sử dụng

### Backend
- **Django 5.2.8**: Web framework chính
- **Django Channels 4.3.1**: WebSocket support
- **Redis 7.0.1**: Channel layer backend
- **Daphne 4.2.1**: ASGI server
- **Requests**: Gọi TwelveData API

### Frontend
- **lightweight-charts 4.1.3**: Hiển thị biểu đồ nến
- **WebSocket**: Real-time communication
- **Vanilla JavaScript**: UI logic và trading interactions
- **HTML5 Canvas**: Vẽ zones (profit/risk areas)

## 📁 Cấu trúc dự án

```
web_t/
├── manage.py
├── requirements.txt
├── market/                      # App chính
│   ├── consumers.py            # WebSocket consumer (backtest logic)
│   ├── views.py                # HTTP views (chart page, API)
│   ├── urls.py                 # URL routing
│   ├── routing.py              # WebSocket routing
│   ├── models.py               # Database models (chưa sử dụng)
│   ├── function/
│   │   └── load_data.py        # TwelveData API helper
│   ├── data/
│   │   ├── temp.json           # Dữ liệu nến hiện tại
│   │   └── temp_position.json  # Lịch sử positions đã đóng
│   └── templates/
│       └── market/
│           └── chart.html      # Frontend chart UI
└── web_t/
    ├── settings.py             # Django settings (Redis, logging)
    ├── urls.py                 # Root URL config
    ├── asgi.py                 # ASGI application
    └── wsgi.py                 # WSGI application
```

## 🚀 Chức năng chính

### 1. Load dữ liệu từ API
- Chọn symbol (EUR/USD, GBP/USD, etc.)
- Chọn interval (1min, 5min, 1h, 4h, 1day, etc.)
- Chọn khoảng thời gian (start date - end date)
- Fetch từ TwelveData API và lưu vào `market/data/temp.json`

**Endpoint**: `POST /api/load-data/`

**Format dữ liệu**:
```json
{
  "time": [1763190000000, 1763175600000, ...],
  "open": [1.16183, 1.16132, ...],
  "high": [1.16200, 1.16150, ...],
  "low": [1.16100, 1.16080, ...],
  "close": [1.16154, 1.16183, ...]
}
```

### 2. Streaming dữ liệu nến
- WebSocket endpoint: `ws://host/ws/socket`
- Phát lại candles theo tốc độ có thể điều chỉnh (0.1x - 10x)
- Actions: `load`, `start`, `stop`, `set_speed`, `jump`
- Auto-detect số chữ số thập phân từ dữ liệu
- Sắp xếp dữ liệu theo thứ tự thời gian (oldest first)

### 3. Đặt lệnh giao dịch
**Chế độ Setup Order**:
1. Click nút LONG/SHORT
2. Chart tạm dừng (nếu đang chạy)
3. Click vào chart để chọn giá entry
4. Tự động tính TP/SL với R:R ratio 1:2
5. Điều chỉnh TP/SL theo ý muốn
6. Xác nhận hoặc hủy lệnh
7. Chart tự động resume nếu đang chạy trước đó

**Features**:
- Entry price line (dashed)
- TP line (green, solid)
- SL line (red, solid)
- Profit zone (green transparent)
- Risk zone (red transparent)
- R:R ratio calculation
- Markers khi entry và exit

### 4. Quản lý Positions
- Hiển thị danh sách positions đang mở
- P&L real-time theo giá hiện tại
- Close position thủ công
- Close all positions
- Auto-close khi hit TP/SL

### 5. Backtest Logic
**Consumer xử lý**:
- Mỗi candle kiểm tra high/low so với TP/SL
- LONG: hit TP nếu high >= TP, hit SL nếu low <= SL
- SHORT: hit TP nếu low <= TP, hit SL nếu high >= SL
- Tính P&L: `(exit_price - entry_price) × quantity × (1 if buy else -1)`
- Lưu closed positions vào `temp_position.json`

**Statistics khi kết thúc stream**:
- Total trades
- Wins / Losses
- Win rate (%)
- Total P&L

### 6. Logging
- File logs: `django_debug.log`, `django_error.log`
- Console logging
- WebSocket errors tracking

## 🎯 Cài đặt và chạy

### Yêu cầu
- Python 3.10+
- Redis server (running on localhost:6379)

### Cài đặt
```bash
# Clone project
cd /opt/web_t

# Install dependencies
pip install -r requirements.txt

# Chạy Redis (nếu chưa chạy)
sudo systemctl start redis

# Apply migrations (nếu cần)
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput
```

### Chạy server
```bash
# Development mode (với Daphne)
daphne -b 0.0.0.0 -p 8000 web_t.asgi:application

# Hoặc với manage.py
python manage.py runserver 0.0.0.0:8000
```

### Sử dụng
1. Mở browser: `http://localhost:8000/`
2. Click **Load** → Nhập symbol/interval/dates → **Fetch & Save**
3. Click **Start** để phát dữ liệu
4. Click **LONG** hoặc **SHORT** để đặt lệnh
5. Click vào chart để chọn entry price
6. Điều chỉnh TP/SL và click **Confirm**
7. Theo dõi positions và P&L

## 🔧 Configuration

### TwelveData API Key
Trong `market/views.py`:
```python
api_key = apikey or 'c726713aef384812831e2716f1d914da'
```

### Redis Connection
Trong `web_t/settings.py`:
```python
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": { "hosts": [("127.0.0.1", 6379)], },
    }
}
```

### Chart Precision
Tự động phát hiện từ dữ liệu (mặc định: 5 chữ số cho forex)

## 📊 WebSocket Protocol

### Client → Server
```json
{"action": "load", "file": "data/temp.json"}
{"action": "start"}
{"action": "stop"}
{"action": "set_speed", "speed": 2.0}
{"action": "place_order", "side": "buy", "quantity": 1, "price": 1.16000, "tp": 1.16500, "sl": 1.15500}
{"action": "close_position", "position_id": 1}
```

### Server → Client
```json
{"type": "candle", "data": {"time": 1763190000, "open": 1.16183, "high": 1.16200, "low": 1.16100, "close": 1.16154}}
{"status": "loaded", "total": 100}
{"status": "started"}
{"status": "stopped"}
{"type": "order_placed", "position": {...}}
{"type": "position_hit", "position_id": 1, "reason": "TP", "pnl": 50.0}
{"type": "backtest_stats", "stats": {"total_trades": 10, "wins": 7, "losses": 3, "win_rate": 70.0, "total_pnl": 250.5}}
```

## 🐛 Đã sửa các lỗi

1. ✅ 404 error trên WebSocket route
2. ✅ lightweight-charts API mismatch
3. ✅ Data format conversion (dict-of-arrays → array-of-objects)
4. ✅ Time format (milliseconds → seconds)
5. ✅ Data ordering (newest first → oldest first)
6. ✅ Precision display (auto-detect decimal places)
7. ✅ Chart clear khi load symbol mới
8. ✅ Stream task lifecycle management
9. ✅ Type errors (string vs float)
10. ✅ Canvas overlay zones rendering

---

## 🚀 Hướng phát triển tiếp theo

### 1. **Multi-timeframe Analysis**
- [ ] Hiển thị multiple timeframes trên cùng một chart
- [ ] Sync giữa các timeframes
- [ ] MTF indicators (Support/Resistance, Trend)

### 2. **Technical Indicators**
- [ ] Thêm indicators: MA, EMA, RSI, MACD, Bollinger Bands
- [ ] Vẽ indicators trên chart hoặc panel riêng
- [ ] Tự động generate signals từ indicators
- [ ] Backtest dựa trên indicator strategies

### 3. **Advanced Order Types**
- [ ] Limit orders (pending orders)
- [ ] Stop orders
- [ ] Trailing stop
- [ ] Partial close positions
- [ ] Average down/up
- [ ] OCO orders (One-Cancels-Other)

### 4. **Risk Management**
- [ ] Position sizing calculator (% account, fixed lot)
- [ ] Risk per trade (% hoặc $ amount)
- [ ] Max daily loss/profit limits
- [ ] Correlation analysis giữa các positions
- [ ] Portfolio risk metrics

### 5. **Strategy Builder**
- [ ] Visual strategy builder (drag-and-drop rules)
- [ ] Code-based strategy (Python/JavaScript)
- [ ] Strategy templates (Breakout, Mean Reversion, Trend Following)
- [ ] Strategy parameters optimization
- [ ] Walk-forward analysis

### 6. **Performance Analytics**
- [ ] Equity curve visualization
- [ ] Drawdown chart
- [ ] Monthly/yearly performance heatmap
- [ ] Win/loss distribution
- [ ] Trade duration analysis
- [ ] Best/worst trades
- [ ] Sharpe ratio, Sortino ratio, Calmar ratio
- [ ] Export reports (PDF, Excel)

### 7. **Database & History**
- [ ] Lưu historical data vào database (PostgreSQL/SQLite)
- [ ] Lưu strategies và backtest results
- [ ] User accounts và authentication
- [ ] Share backtests với người khác
- [ ] Compare multiple backtests

### 8. **Real-time Market Data**
- [ ] Connect với broker APIs (MT4/MT5, Interactive Brokers)
- [ ] Live trading mode (paper trading)
- [ ] Real-time alerts (Telegram, Email, SMS)
- [ ] News feed integration
- [ ] Economic calendar

### 9. **UI/UX Improvements**
- [ ] Dark mode / Light mode toggle
- [ ] Responsive design (mobile-friendly)
- [ ] Keyboard shortcuts
- [ ] Chart templates (save layouts)
- [ ] Multiple charts view (grid layout)
- [ ] Chart annotations (drawing tools: lines, rectangles, text)

### 10. **Optimization & Performance**
- [ ] Cache dữ liệu đã tải
- [ ] Background jobs cho data fetching (Celery)
- [ ] Compress WebSocket messages
- [ ] Lazy loading cho large datasets
- [ ] Server-side rendering cho reports

### 11. **Machine Learning Integration**
- [ ] Price prediction models
- [ ] Pattern recognition (Head & Shoulders, Triangles)
- [ ] Sentiment analysis từ news
- [ ] Auto-generate strategies bằng ML
- [ ] Reinforcement learning agents

### 12. **Multi-asset Support**
- [ ] Stocks
- [ ] Crypto
- [ ] Commodities
- [ ] Indices
- [ ] Futures & Options
- [ ] Custom CSV import

### 13. **Collaboration Features**
- [ ] Share strategies với community
- [ ] Follow top performers
- [ ] Strategy marketplace
- [ ] Comments & ratings
- [ ] Leaderboard

### 14. **Testing & Quality**
- [ ] Unit tests cho consumer/views
- [ ] Integration tests cho WebSocket
- [ ] Frontend tests (Jest, Playwright)
- [ ] CI/CD pipeline
- [ ] Error monitoring (Sentry)

### 15. **Documentation**
- [ ] API documentation (Swagger/OpenAPI)
- [ ] User guide video tutorials
- [ ] Strategy writing tutorial
- [ ] FAQ section
- [ ] Developer documentation

---

## 📝 Priority Roadmap

### Phase 1 (Quick Wins - 2-3 weeks)
1. Technical Indicators (MA, EMA, RSI)
2. Performance Analytics (Equity curve, Drawdown)
3. Database integration (save backtests)
4. Dark mode UI

### Phase 2 (Core Features - 1-2 months)
1. Strategy Builder
2. Advanced Order Types
3. Risk Management Tools
4. Export Reports

### Phase 3 (Advanced - 2-3 months)
1. Real-time market data
2. Multi-asset support
3. Machine Learning integration
4. Live trading mode

### Phase 4 (Scale - 3+ months)
1. User accounts & authentication
2. Community features
3. Mobile app
4. Enterprise features

---

## 📞 Support & Contact

- **Issues**: Tạo issue trên GitHub
- **Email**: [your-email]
- **Documentation**: [link to docs]

## 📄 License

[Specify license here]

---

**Version**: 1.0.0  
**Last Updated**: November 16, 2025
