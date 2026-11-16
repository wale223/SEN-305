from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST
from .forms import AssignmentForm, CommentForm, ResolutionForm, ServiceRequestForm
from .models import ServiceRequest
from .selectors import (
    service_request_counts,
    service_request_filter,
    service_request_get,
)
from .services import (
    comment_create,
    service_request_assign,
    service_request_create,
    service_request_resolve,
    service_request_update,
)


@login_required
def request_list(request):
    status = request.GET.get("status", "").strip()
    query = request.GET.get("q", "").strip()
    queryset = service_request_filter(user=request.user, status=status, query=query)
    page_obj = Paginator(queryset, 10).get_page(request.GET.get("page"))
    counts = service_request_counts(user=request.user)

    return render(
        request,
        "requests_app/request_list.html",
        {
            "page_obj": page_obj,
            "status_choices": ServiceRequest.Status.choices,
            "selected_status": status,
            "query": query,
            "counts": counts,
        },
    )


@login_required
def request_detail(request, request_id):
    try:
        item = service_request_get(user=request.user, request_id=request_id)
    except ServiceRequest.DoesNotExist as exc:
        raise Http404("Service request not found.") from exc

    can_assign = request.user.is_staff
    can_resolve = request.user.is_staff or (
        hasattr(item, "work_order") and item.work_order.technician == request.user
    )

    assignment_form = AssignmentForm() if can_assign else None
    resolution_form = (
        ResolutionForm(
            initial={
                "work_notes": item.work_order.work_notes if hasattr(item, "work_order") else "",
                "resolution_summary": item.resolution_summary,
            }
        )
        if can_resolve
        else None
    )

    return render(
        request,
        "requests_app/request_detail.html",
        {
            "item": item,
            "comments": item.comments.select_related("author").order_by("created_at"),
            "comment_form": CommentForm(),
            "assignment_form": assignment_form,
            "resolution_form": resolution_form,
            "can_assign": can_assign,
            "can_resolve": can_resolve,
        },
    )


@login_required
def request_create(request):
    form = ServiceRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        item = service_request_create(requester=request.user, **form.cleaned_data)
        messages.success(request, "Service request created.")
        return redirect("requests:detail", request_id=item.id)
    return render(
        request,
        "requests_app/request_form.html",
        {"form": form, "mode": "Create"},
    )


@login_required
def request_update(request, request_id):
    try:
        item = service_request_get(user=request.user, request_id=request_id)
    except ServiceRequest.DoesNotExist as exc:
        raise Http404("Service request not found.") from exc

    form = ServiceRequestForm(request.POST or None, instance=item)
    if request.method == "POST" and form.is_valid():
        try:
            item = service_request_update(
                item=item, actor=request.user, **form.cleaned_data
            )
        except (ValidationError, PermissionDenied) as exc:
            form.add_error(None, exc)
        else:
            messages.success(request, "Service request updated.")
            return redirect("requests:detail", request_id=item.id)
    return render(
        request,
        "requests_app/request_form.html",
        {"form": form, "mode": "Update", "item": item},
    )


@require_POST
@login_required
def comment_add(request, request_id):
    try:
        item = service_request_get(user=request.user, request_id=request_id)
    except ServiceRequest.DoesNotExist as exc:
        raise Http404("Service request not found.") from exc

    form = CommentForm(request.POST)
    if form.is_valid():
        comment_create(item=item, author=request.user, **form.cleaned_data)
        messages.success(request, "Comment added.")
    else:
        messages.error(request, "Enter at least 3 characters.")
    return redirect("requests:detail", request_id=item.id)


@require_POST
@login_required
def request_assign(request, request_id):
    if not request.user.is_staff:
        return HttpResponseForbidden("Staff access is required to assign requests.")

    try:
        item = service_request_get(user=request.user, request_id=request_id)
    except ServiceRequest.DoesNotExist as exc:
        raise Http404("Service request not found.") from exc

    form = AssignmentForm(request.POST)
    if form.is_valid():
        try:
            service_request_assign(
                item=item,
                technician=form.cleaned_data["technician"],
                actor=request.user,
            )
            messages.success(
                request,
                f"Assigned technician {form.cleaned_data['technician'].username}.",
            )
        except (ValidationError, PermissionDenied) as exc:
            messages.error(request, str(exc))
    else:
        messages.error(request, "Invalid technician selection.")
    return redirect("requests:detail", request_id=item.id)


@require_POST
@login_required
def request_resolve(request, request_id):
    try:
        item = service_request_get(user=request.user, request_id=request_id)
    except ServiceRequest.DoesNotExist as exc:
        raise Http404("Service request not found.") from exc

    form = ResolutionForm(request.POST)
    if form.is_valid():
        try:
            service_request_resolve(
                item=item,
                actor=request.user,
                work_notes=form.cleaned_data["work_notes"],
                resolution_summary=form.cleaned_data["resolution_summary"],
            )
            messages.success(request, "Service request resolved successfully.")
        except (ValidationError, PermissionDenied) as exc:
            messages.error(request, str(exc))
    else:
        messages.error(
            request, "Please provide complete work notes and resolution summary."
        )
    return redirect("requests:detail", request_id=item.id)
