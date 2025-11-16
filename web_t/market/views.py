from django.shortcuts import render
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from pathlib import Path
from .function import load_data as ld
import json


def chart_page(request):
    return render(request, "market/chart.html")


@csrf_exempt
def load_data_api(request):
    if request.method != 'POST':
        return HttpResponseBadRequest('POST required')

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        return HttpResponseBadRequest('invalid json')

    symbol = payload.get('symbol')
    interval = payload.get('interval')
    start = payload.get('start')
    end = payload.get('end')
    apikey = payload.get('apikey')

    if not symbol or not interval or not start or not end:
        return HttpResponseBadRequest('missing fields')

    # convert dates (YYYY-MM-DD) to timestamps in seconds
    try:
        # accept either milliseconds or dates
        # if start/end are numeric use as timestamps, otherwise parse date
        def parse_date(v):
            try:
                return int(v)
            except Exception:
                from datetime import datetime
                dt = datetime.strptime(v, '%Y-%m-%d')
                return int(dt.timestamp())

        start_ts = parse_date(start)
        end_ts = parse_date(end)
    except Exception as e:
        return HttpResponseBadRequest(f'invalid date: {e}')

    # write to market/data/temp.json
    outpath = Path(__file__).resolve().parent / 'data' / 'temp.json'
    try:
        # use default API key from module if none provided
        api_key = apikey or getattr(ld, '__default_apikey__', None)
        # If default api is not defined in module, try the hardcoded one inside load_data (fallback)
        if not api_key:
            api_key = 'c726713aef384812831e2716f1d914da'

        ld.fetch_and_save(api_key, symbol, interval, start_ts, end_ts, outpath=str(outpath))
        return JsonResponse({'status': 'ok', 'file': str(outpath)})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
