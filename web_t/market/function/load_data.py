import requests
from datetime import datetime
import json

def timestamp_to_api_format(timestamp):
    """
    Chuyển đổi timestamp sang định dạng 'YYYY-MM-DD HH:MM:SS' cho API
    
    Args:
        timestamp (int/float): Unix timestamp (giây hoặc mili giây)
    
    Returns:
        str: Chuỗi thời gian định dạng 'YYYY-MM-DD HH:MM:SS'
    """
    # Kiểm tra nếu timestamp là mili giây (> 10^10)
    if timestamp > 10000000000:
        timestamp = timestamp / 1000
    
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime('%Y-%m-%d %H:%M:%S')

def datetime_to_timestamp_ms(datetime_str):
    """
    Chuyển đổi datetime string sang timestamp mili giây
    
    Args:
        datetime_str (str): Chuỗi thời gian định dạng 'YYYY-MM-DD HH:MM:SS'
    
    Returns:
        int: Unix timestamp tính bằng mili giây
    """
    dt = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
    timestamp_s = int(dt.timestamp())
    return timestamp_s * 1000

def get_time_series(api_key, symbol, interval, start_timestamp, end_timestamp):
    """
    Gọi API TwelveData để lấy time series data
    
    Args:
        api_key (str): API key
        symbol (str): Cặp tiền tệ (ví dụ: 'EUR/USD')
        interval (str): Khoảng thời gian (ví dụ: '5min', '1h', '1day')
        start_timestamp (int/float): Timestamp bắt đầu (giây hoặc mili giây)
        end_timestamp (int/float): Timestamp kết thúc (giây hoặc mili giây)
    
    Returns:
        dict: Response data từ API
    """
    start_date = timestamp_to_api_format(start_timestamp)
    end_date = timestamp_to_api_format(end_timestamp)
    
    url = "https://api.twelvedata.com/time_series"
    params = {
        'apikey': api_key,
        'interval': interval,
        'start_date': start_date,
        'end_date': end_date,
        'symbol': symbol
    }
    
    response = requests.get(url, params=params)
    return response.json()

def format_data_to_arrays(data):
    """
    Chuyển đổi dữ liệu API sang định dạng arrays
    
    Args:
        data (dict): Response data từ API
    
    Returns:
        dict: Dữ liệu định dạng {time:[], open:[], close:[], high:[], low:[], volume:[]}
    """
    result = {
        'time': [],
        'open': [],
        'close': [],
        'high': [],
        'low': [],
        'volume': []
    }
    
    if 'values' in data:
        for item in data['values']:
            # Chuyển datetime string sang timestamp ms
            datetime_str = item.get('datetime', '')
            if datetime_str:
                result['time'].append(datetime_to_timestamp_ms(datetime_str))
            
            result['open'].append(float(item.get('open', 0)))
            result['close'].append(float(item.get('close', 0)))
            result['high'].append(float(item.get('high', 0)))
            result['low'].append(float(item.get('low', 0)))
            
            # Thêm volume nếu có
            if 'volume' in item:
                result['volume'].append(float(item.get('volume', 0)))
        
        # Xóa volume nếu không có dữ liệu
        if not result['volume']:
            del result['volume']
    
    return result

def save_to_json(data, symbol, interval):
    """
    Lưu dữ liệu vào file JSON
    
    Args:
        data (dict): Dữ liệu cần lưu
        symbol (str): Symbol
        interval (str): Interval
    """
    filename = f"{symbol.replace('/', '_')}_{interval}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Đã lưu dữ liệu vào file: {filename}")


def fetch_and_save(api_key, symbol, interval, start_timestamp, end_timestamp, outpath=None):
    """Fetch from TwelveData and save formatted arrays to outpath (JSON).

    Args:
        api_key (str): API key
        symbol (str): symbol string
        interval (str): interval string
        start_timestamp (int): start timestamp (seconds or ms)
        end_timestamp (int): end timestamp (seconds or ms)
        outpath (str|Path): path to write JSON (if None, uses {symbol}_{interval}.json)
    Returns:
        dict: formatted data
    """
    data = get_time_series(api_key, symbol, interval, start_timestamp, end_timestamp)
    formatted = format_data_to_arrays(data)
    if outpath:
        with open(outpath, 'w', encoding='utf-8') as f:
            json.dump(formatted, f, indent=2, ensure_ascii=False)
    else:
        save_to_json(formatted, symbol, interval)
    return formatted

# Sử dụng
if __name__ == "__main__":
    api_key = "c726713aef384812831e2716f1d914da"
    symbol = "EUR/USD"
    interval = "4h"
    start_timestamp = 1762765758000
    end_timestamp = 1762852158
    
    # Lấy dữ liệu từ API
    data = get_time_series(api_key, symbol, interval, start_timestamp, end_timestamp)
    print("Response từ API:")
    print(data)
    
    # Chuyển đổi sang định dạng arrays
    formatted_data = format_data_to_arrays(data)
    print("\nDữ liệu đã format:")
    print(formatted_data)
    
    # Lưu vào file JSON
    save_to_json(formatted_data, symbol, interval)