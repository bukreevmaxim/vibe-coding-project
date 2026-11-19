from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from orders.models import Order
from orders.services import OrderCannotBeCancelled, cancel_order


@require_GET
@login_required
def order_list(request):
    status = request.GET.get("status")
    valid_statuses = set(Order.Status.values)
    if status is not None and status not in valid_statuses:
        return JsonResponse({"error": "invalid_status"}, status=400)

    raw_min_total = request.GET.get("min_total")
    min_total = None
    if raw_min_total is not None:
        try:
            min_total = Decimal(raw_min_total)
        except (InvalidOperation, ValueError):
            return JsonResponse({"error": "invalid_min_total"}, status=400)
        if not min_total.is_finite() or min_total < 0:
            return JsonResponse({"error": "invalid_min_total"}, status=400)

    raw_max_total = request.GET.get("max_total")
    max_total = None
    if raw_max_total is not None:
        try:
            max_total = Decimal(raw_max_total)
        except (InvalidOperation, ValueError):
            return JsonResponse({"error": "invalid_max_total"}, status=400)
        if not max_total.is_finite() or max_total < 0:
            return JsonResponse({"error": "invalid_max_total"}, status=400)

    orders = Order.objects.filter(owner=request.user)
    if status is not None:
        orders = orders.filter(status=status)
    if min_total is not None:
        orders = orders.filter(total__gte=min_total)
    if max_total is not None:
        orders = orders.filter(total__lte=max_total)
    orders = orders.order_by("-created_at", "-id")

    data = [
        {
            "id": order.id,
            "title": order.title,
            "status": order.status,
            "total": str(order.total),
            "created_at": order.created_at.isoformat(),
        }
        for order in orders
    ]
    return JsonResponse({"orders": data})


@require_POST
@login_required
def cancel(request, order_id):
    try:
        order = Order.objects.get(pk=order_id)
    except Order.DoesNotExist:
        return JsonResponse({"error": "not_found"}, status=404)

    if order.owner_id != request.user.id:
        return JsonResponse({"error": "forbidden"}, status=403)

    try:
        cancel_order(order)
    except OrderCannotBeCancelled:
        return JsonResponse({"error": "cannot_cancel"}, status=400)

    return JsonResponse({"id": order.id, "status": order.status})
