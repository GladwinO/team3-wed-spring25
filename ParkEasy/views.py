from django.shortcuts import render


def custom_404_handler(request, exception=None):
    return render(request, "404.html", status=404)
