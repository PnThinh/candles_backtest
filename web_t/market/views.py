from django.shortcuts import render

def chart_page(request):
    return render(request, "market/chart.html")
