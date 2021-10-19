import json
import uuid
import datetime
from collections import defaultdict
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.shortcuts import redirect, render
from django.http import JsonResponse, HttpResponseBadRequest
from .models import Subscription, Profile, Notification, WEEKLY


class PermissionException(Exception):
    pass


def _ensure_feature_flag(user, perm="feature_subscriptions"):
    try:
        if getattr(user.profile, perm):
            return True
    except Profile.DoesNotExist:
        pass
    raise PermissionException(f"{user} does not have {perm}")


@login_required
def profile(request):
    if request.method == "POST":
        # not using forms due to variability of included fields
        request.user.profile.organization_name = request.POST["organization"]
        request.user.profile.about = request.POST["about"]
        request.user.profile.subscription_frequency = request.POST.get(
            "subscription_frequency", WEEKLY
        )
        request.user.profile.subscription_emails_html = (
            "subscription_emails_html" in request.POST
        )
        request.user.profile.save()
        messages.success(request, "Updated profile settings.")

    primary = request.user.emailaddress_set.get(primary=True)
    subscriptions = request.user.subscriptions.filter(active=True).order_by(
        "-created_at"
    )
    recent_usage = defaultdict(lambda: {"v2": 0, "v3": 0})
    for r in request.user.profile.usage_reports.filter(
        date__gt=datetime.date.today() - datetime.timedelta(days=7)
    ):
        if r.endpoint == "graphql":
            recent_usage[r.date]["v2"] += r.calls
        elif r.endpoint == "v3":
            recent_usage[r.date]["v3"] += r.calls

    return render(
        request,
        "account/profile.html",
        {
            "primary_email": primary,
            "subscriptions": subscriptions,
            "recent_usage": sorted(dict(recent_usage).items(), reverse=True),
        },
    )


def unsubscribe(request):
    """
    Will used logged in user if there is one, otherwise will try to figure out user
    from email parameter to make unsubscribing easier on people.
    """
    user = None
    if request.user.is_authenticated:
        user = request.user
    elif "email" in request.GET:
        try:
            notification = Notification.objects.get(pk=request.GET["email"])
            user = User.objects.get(email=notification.email)
        except (Notification.DoesNotExist, User.DoesNotExist):
            pass

    if not user:
        return redirect("/accounts/login/?next=/accounts/profile/unsubscribe/")

    subscriptions = user.subscriptions.filter(active=True).order_by("-created_at")
    if request.method == "POST":
        count = subscriptions.update(active=False)
        messages.success(request, f"Successfully deactivated {count} subscriptions.")
        return redirect("/accounts/profile/")
    else:
        return render(
            request, "account/unsubscribe.html", {"subscriptions": subscriptions}
        )


@login_required
@require_POST
def deactivate_subscription(request):
    try:
        sub = Subscription.objects.get(
            user=request.user, pk=request.POST["subscription_id"], active=True
        )
        sub.active = False
        sub.save()
        messages.success(request, f"Deactivated subscription: {sub.pretty}")
    except Subscription.DoesNotExist:
        pass
    return redirect("/accounts/profile/")


def activate_subscription(**kwargs):
    """returns True iff a subscription was created or activated"""
    sub, created = Subscription.objects.get_or_create(**kwargs)
    # check if it already existed and was deactivated
    if not created and not sub.active:
        sub.active = True
        sub.save()
        created = True
    return sub, created


@login_required
@require_POST
def add_search_subscription(request):
    _ensure_feature_flag(request.user)

    if not request.POST.get("query"):
        return HttpResponseBadRequest(
            "Invalid subscription request, must include query."
        )

    sub, created = activate_subscription(
        user=request.user,
        query=request.POST["query"],
        state=request.POST["state"],
        chamber=request.POST.get("chamber", ""),
        classification=request.POST.get("classification", ""),
        subjects=request.POST.getlist("subjects"),
        status=request.POST.getlist("status"),
        sponsor_id=request.POST.get("sponsor_id"),
    )
    if created:
        messages.success(request, f"Created new subscription: {sub.pretty}")
    return redirect("/accounts/profile/")


@login_required
@require_POST
def add_sponsor_subscription(request):
    _ensure_feature_flag(request.user)
    sub, created = activate_subscription(
        user=request.user,
        sponsor_id=request.POST["sponsor_id"],
        query="",
        subjects=[],
        status=[],
    )
    if created:
        messages.success(request, f"Created new subscription: {sub.pretty}")
    return redirect("/accounts/profile/")


@login_required
def bill_subscription(request):
    _ensure_feature_flag(request.user)

    error = ""
    active = False

    if request.method == "POST":
        bill_id = json.loads(request.body)["bill_id"]
        sub, created = activate_subscription(
            user=request.user, bill_id=bill_id, query="", subjects=[], status=[]
        )
        active = True
    elif request.method == "GET":
        bill_id = request.GET["bill_id"]
        active = Subscription.objects.filter(
            user=request.user, active=True, bill_id=bill_id
        ).exists()
    elif request.method == "DELETE":
        bill_id = json.loads(request.body)["bill_id"]
        try:
            sub = Subscription.objects.get(
                user=request.user, bill_id=bill_id, active=True
            )
            sub.active = False
            sub.save()
        except Subscription.DoesNotExist:
            error = "no such subscription"

    return JsonResponse({"active": active, "bill_id": bill_id, "error": error})


@login_required
@require_POST
def request_key(request):
    primary_email = request.user.emailaddress_set.filter(primary=True, verified=True)
    if not primary_email:
        messages.warning(request, "Must verify your email address to obtain API Key.")
    elif (
        request.user.profile.api_tier == "inactive" or not request.user.profile.api_key
    ):
        if not request.user.profile.api_key:
            request.user.profile.api_key = uuid.uuid4()
        request.user.profile.api_tier = "default"
        request.user.profile.save()
        messages.success(request, "Your API Key is ready to use!")
    else:
        messages.warning(request, "Could not change status of key.")
    return redirect("/accounts/profile/")
