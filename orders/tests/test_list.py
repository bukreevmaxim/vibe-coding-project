from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from orders.models import Order


class OrderListTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="owner@example.com",
            password="safe-pass-123",
        )
        other_user = User.objects.create_user(
            username="other@example.com",
            password="safe-pass-123",
        )
        self.new_order = Order.objects.create(
            owner=self.user,
            title="Новый заказ",
            status=Order.Status.NEW,
            total=Decimal("100.00"),
        )
        self.paid_order = Order.objects.create(
            owner=self.user,
            title="Оплаченный заказ",
            status=Order.Status.PAID,
            total=Decimal("250.50"),
        )
        Order.objects.create(
            owner=other_user,
            title="Чужой заказ",
            status=Order.Status.NEW,
            total=Decimal("999.00"),
        )
        self.client.force_login(self.user)
        self.url = reverse("orders:list")

    def test_list_contains_only_own_orders(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        order_ids = [item["id"] for item in response.json()["orders"]]
        self.assertEqual(order_ids, [self.paid_order.id, self.new_order.id])

    def test_list_filters_by_status(self):
        response = self.client.get(self.url, {"status": Order.Status.PAID})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.json()["orders"]],
            [self.paid_order.id],
        )

    def test_invalid_status_returns_400(self):
        response = self.client.get(self.url, {"status": "unknown"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "invalid_status"})

    def test_list_without_min_total_unchanged(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.json()["orders"]],
            [self.paid_order.id, self.new_order.id],
        )

    def test_list_filters_by_min_total(self):
        response = self.client.get(self.url, {"min_total": "200.00"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.json()["orders"]],
            [self.paid_order.id],
        )

    def test_min_total_boundary_is_inclusive(self):
        response = self.client.get(self.url, {"min_total": "100.00"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.json()["orders"]],
            [self.paid_order.id, self.new_order.id],
        )

    def test_min_total_zero_returns_all_own_orders(self):
        response = self.client.get(self.url, {"min_total": "0"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.json()["orders"]],
            [self.paid_order.id, self.new_order.id],
        )

    def test_min_total_above_all_returns_empty_list(self):
        response = self.client.get(self.url, {"min_total": "1000.00"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"orders": []})

    def test_min_total_does_not_leak_other_users_orders(self):
        response = self.client.get(self.url, {"min_total": "900.00"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"orders": []})

    def test_min_total_combined_with_status(self):
        response = self.client.get(
            self.url,
            {"status": Order.Status.PAID, "min_total": "150.00"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.json()["orders"]],
            [self.paid_order.id],
        )

    def test_min_total_non_numeric_returns_400(self):
        response = self.client.get(self.url, {"min_total": "abc"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "invalid_min_total"})

    def test_min_total_empty_value_returns_400(self):
        response = self.client.get(self.url, {"min_total": ""})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "invalid_min_total"})

    def test_min_total_negative_returns_400(self):
        response = self.client.get(self.url, {"min_total": "-1"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "invalid_min_total"})

    def test_min_total_nan_returns_400(self):
        response = self.client.get(self.url, {"min_total": "NaN"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "invalid_min_total"})

    def test_min_total_infinity_returns_400(self):
        response = self.client.get(self.url, {"min_total": "Infinity"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "invalid_min_total"})

    def test_list_without_max_total_unchanged(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.json()["orders"]],
            [self.paid_order.id, self.new_order.id],
        )

    def test_list_filters_by_max_total(self):
        response = self.client.get(self.url, {"max_total": "150.00"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.json()["orders"]],
            [self.new_order.id],
        )

    def test_max_total_boundary_is_inclusive(self):
        response = self.client.get(self.url, {"max_total": "100.00"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.json()["orders"]],
            [self.new_order.id],
        )

    def test_max_total_zero_returns_empty_list(self):
        response = self.client.get(self.url, {"max_total": "0"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"orders": []})

    def test_max_total_above_all_returns_all_own_orders(self):
        response = self.client.get(self.url, {"max_total": "1000.00"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.json()["orders"]],
            [self.paid_order.id, self.new_order.id],
        )

    def test_max_total_does_not_leak_other_users_orders(self):
        response = self.client.get(self.url, {"max_total": "999.00"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.json()["orders"]],
            [self.paid_order.id, self.new_order.id],
        )

    def test_min_total_and_max_total_combined(self):
        response = self.client.get(
            self.url,
            {"min_total": "100.00", "max_total": "200.00"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.json()["orders"]],
            [self.new_order.id],
        )

    def test_max_total_combined_with_status(self):
        response = self.client.get(
            self.url,
            {"status": Order.Status.PAID, "max_total": "300.00"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.json()["orders"]],
            [self.paid_order.id],
        )

    def test_max_total_invalid_values_return_400(self):
        for value in ("abc", "", "NaN", "Infinity", "-1"):
            with self.subTest(value=value):
                response = self.client.get(self.url, {"max_total": value})

                self.assertEqual(response.status_code, 400)
                self.assertEqual(
                    response.json(), {"error": "invalid_max_total"}
                )

    def test_max_total_error_precedence(self):
        bad_status = self.client.get(
            self.url, {"status": "unknown", "max_total": "abc"}
        )
        self.assertEqual(bad_status.status_code, 400)
        self.assertEqual(bad_status.json(), {"error": "invalid_status"})

        bad_min_total = self.client.get(
            self.url, {"min_total": "abc", "max_total": "abc"}
        )
        self.assertEqual(bad_min_total.status_code, 400)
        self.assertEqual(bad_min_total.json(), {"error": "invalid_min_total"})