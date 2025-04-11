from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.forms import (
    AuthenticationForm,
    UserCreationForm,
    PasswordChangeForm,
)
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from .forms import EmailChangeForm


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
        verification_file = request.FILES.get("verification_file")

        # Optional: Validate that the file is a PDF if a file was uploaded
        if verification_file and not verification_file.name.lower().endswith(".pdf"):
            context["error_message"] = "Only PDF files are allowed."
            return render(request, "accounts/verify.html", context)

        # The verification remains based on the answer for now
        if answer == "ParkEasy":
            request.user.profile.is_verified = True
            if verification_file:
                request.user.profile.verification_file = verification_file
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

    return render(request, "accounts/verify.html", context)


@login_required
def profile_view(request):
    # Get messages from session if present
    success_message = request.session.pop("success_message", None)
    error_message = request.session.pop("error_message", None)

    # Render the user's profile page with message context
    return render(
        request,
        "accounts/profile.html",
        {
            "user": request.user,
            "success_message": success_message,
            "error_message": error_message,
        },
    )


@login_required
def change_password(request):
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            # Important: prevents user from being logged out
            update_session_auth_hash(request, user)
            return redirect("password_change_done")
    else:
        form = PasswordChangeForm(request.user)
    return render(request, "accounts/password_change.html", {"form": form})


@login_required
def password_change_done(request):
    request.session["success_message"] = "Password changed successfully!"
    return redirect("profile")


@login_required
def change_email(request):
    # Fix the logic to correctly detect empty emails
    is_adding_email = request.user.email == "" or request.user.email is None

    if request.method == "POST":
        # Pass user to form for validation
        form = EmailChangeForm(request.POST, user=request.user)
        if form.is_valid():
            request.user.email = form.cleaned_data["email"]
            request.user.save()

            # Store message in session for retrieval after redirect
            if is_adding_email:
                request.session["success_message"] = "Email added successfully!"
            else:
                request.session["success_message"] = "Email updated successfully!"

            return redirect("profile")
    else:
        # Also pass user to form when initially rendering
        form = EmailChangeForm(user=request.user)

    # Pass context to differentiate between add/change
    return render(
        request,
        "accounts/change_email.html",
        {"form": form, "is_adding_email": is_adding_email},
    )
