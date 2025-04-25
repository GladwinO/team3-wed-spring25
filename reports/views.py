from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseForbidden
from .forms import ReportForm
from messaging.models import Message
from listings.models import Listing, Review
from .models import Report
from accounts.models import Notification
from django.contrib.auth.models import User


@login_required
def report_item(request, content_type_str, object_id):
    # Map string identifiers to actual models
    content_type_map = {
        "listing": Listing,
        "review": Review,
        "message": Message,
    }

    if content_type_str not in content_type_map:
        return redirect("home")

    model = content_type_map[content_type_str]
    content_type = ContentType.objects.get_for_model(model)

    # Check if the object exists
    try:
        reported_object = model.objects.get(pk=object_id)

        # Permission check for messages - only sender or recipient can report
        if content_type_str == "message":
            if (
                request.user != reported_object.sender
                and request.user != reported_object.recipient
            ):
                return redirect("inbox")

        # Permission check for reviews - prevent users from reporting their own reviews
        elif content_type_str == "review":
            if request.user == reported_object.user:
                request.session["error_message"] = "You cannot report your own review."
                return redirect(
                    "listing_reviews", listing_id=reported_object.listing.id
                )

    except model.DoesNotExist:
        if content_type_str == "message":
            return redirect("inbox")
        elif content_type_str == "review":
            return redirect("view_listings")
        else:
            return redirect("home")

    if request.method == "POST":
        form = ReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.reporter = request.user
            report.content_type = content_type
            report.object_id = object_id
            report.save()

            # Store the success message in the session
            request.session["success_message"] = (
                "Thank you for your report. Our team will review it shortly."
            )

            # Notify admins about the new report
            admins = User.objects.filter(is_staff=True)
            for admin in admins:
                Notification.objects.create(
                    sender=request.user,
                    recipient=admin,
                    subject=f"New Report: {report.get_report_type_display()}",
                    content=f"""A new {report.get_report_type_display().lower()} report has been submitted for a
                            {content_type_str}. Please review it.""",
                    notification_type="ADMIN_ALERT",
                )

            # Redirect based on content type
            if content_type_str == "message":
                return redirect("inbox")
            elif content_type_str == "listing":
                return redirect("view_listings")
            elif content_type_str == "review":
                return redirect(
                    "listing_reviews", listing_id=reported_object.listing.id
                )
    else:
        form = ReportForm()

    context = {
        "form": form,
        "reported_object": reported_object,
        "content_type_str": content_type_str,
    }

    return render(request, "reports/report_form.html", context)


@login_required
def admin_reports(request):
    """View for administrators to see all reports."""
    # Check if the current user is an admin
    if not request.user.is_staff:
        return HttpResponseForbidden("You do not have permission to view reports.")

    # Get filter options from request
    status_filter = request.GET.get("status", "PENDING")  # Default to pending
    report_type = request.GET.get("type", None)

    # Base query
    reports_query = Report.objects.all()

    # Apply filters
    if status_filter and status_filter != "ALL":
        reports_query = reports_query.filter(status=status_filter)

    if report_type:
        reports_query = reports_query.filter(report_type=report_type)

    # Order by creation date (newest first)
    reports = reports_query.order_by("-created_at")

    # Count by status for filter UI
    status_counts = {
        "PENDING": Report.objects.filter(status="PENDING").count(),
        "REVIEWING": Report.objects.filter(status="REVIEWING").count(),
        "RESOLVED": Report.objects.filter(status="RESOLVED").count(),
        "DISMISSED": Report.objects.filter(status="DISMISSED").count(),
        "ALL": Report.objects.count(),
    }

    return render(
        request,
        "reports/admin_reports.html",
        {
            "reports": reports,
            "current_status": status_filter,
            "current_type": report_type or "ALL",
            "status_counts": status_counts,
            "report_types": Report.REPORT_TYPES,
        },
    )


@login_required
def admin_report_detail(request, report_id):
    """View for administrators to handle individual reports."""
    # Check if the current user is an admin
    if not request.user.is_staff:
        return HttpResponseForbidden("You do not have permission to handle reports.")

    # Get the report
    report = get_object_or_404(Report, pk=report_id)

    if report.content_type.model == "message":
        reported_object = Message.objects.get(id=report.object_id)
        object_type = "message"
    elif report.content_type.model == "listing":
        reported_object = Listing.objects.get(id=report.object_id)
        object_type = "listing"
    elif report.content_type.model == "review":
        reported_object = Review.objects.get(id=report.object_id)
        object_type = "review"
    else:
        reported_object = None
        object_type = "unknown"

    if request.method == "POST":
        # Handle status changes
        if "update_status" in request.POST:
            new_status = request.POST.get("status")
            admin_notes = request.POST.get("admin_notes", "")

            if new_status in [s[0] for s in Report.STATUS_CHOICES]:
                report.status = new_status
                report.admin_notes = admin_notes
                report.resolved_by = request.user
                report.save()

                # Optionally notify the reporter about status change
                if new_status in ["RESOLVED", "DISMISSED"]:
                    # Create notification with new format
                    notification_content = f"""Your report about a {report.get_report_type_display().lower()}
                                {report.content_type.model} has been {new_status.lower()}."""

                    # Add admin notes if provided
                    if admin_notes:
                        notification_content += f"\n\nAdmin note: {admin_notes}"

                    Notification.objects.create(
                        sender=request.user,
                        recipient=report.reporter,
                        subject=f"Report #{report.id} {new_status.lower()}",
                        content=notification_content,
                        notification_type="REPORT",
                    )

                return redirect("admin_reports")

    return render(
        request,
        "reports/admin_report_detail.html",
        {
            "report": report,
            "reported_object": reported_object,
            "object_type": object_type,
        },
    )
