from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.shortcuts import redirect, render


def home(request):
    return redirect("view_listings")


def register(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # Log in the user after registration
            return redirect("home")  # Redirect to homepage (update as needed)
    else:
        form = UserCreationForm()
    return render(request, "accounts/register.html", {"form": form})


def user_login(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect("home")  # Redirect to homepage (update as needed)
    else:
        form = AuthenticationForm()
    return render(request, "accounts/login.html", {"form": form})


def user_logout(request):
    logout(request)
    return redirect("login")  # Redirect to login page after logout


def verify(request):
    # If the user is already verified, show success message
    if request.user.profile.is_verified:
        return render(request, "accounts/verify.html", {"success": True})

    context = {}
    if request.method == "POST":
        answer = request.POST.get("answer")
        if answer == "ParkEasy":
            request.user.profile.is_verified = True
            request.user.profile.save()
            return render(
                request,
                "accounts/verify.html",
                {
                    "success": True,
                    "success_message": "Congratulations, you are verified and can now post spots!",
                },
            )
        else:
            context["error_message"] = (
                "Incorrect answer, verification failed. Please try again."
            )

    # If GET or POST with errors, render the form as normal
    return render(request, "accounts/verify.html", context)
