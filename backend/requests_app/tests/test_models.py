from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase
from django.utils import timezone
from requests_app.models import Category, ServiceRequest, WorkOrder


class ServiceRequestModelTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.requester = user_model.objects.create_user(username="requester")
        self.technician = user_model.objects.create_user(username="technician")
        self.category = Category.objects.create(name="Electrical")

    def make_request(self, **overrides):
        values = {
            "requester": self.requester,
            "category": self.category,
            "title": "Faulty socket",
            "description": "Socket does not supply power.",
            "location": "Software Engineering Lab",
            "priority": 2,
        }
        values.update(overrides)
        return ServiceRequest.objects.create(**values)

    def test_default_status_is_open(self):
        item = self.make_request()
        self.assertEqual(item.status, ServiceRequest.Status.OPEN)

    def test_priority_validator_rejects_zero(self):
        item = ServiceRequest(
            requester=self.requester,
            category=self.category,
            title="Invalid",
            description="Invalid priority.",
            location="Lab",
            priority=0,
        )
        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_database_constraint_rejects_priority_six(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.make_request(priority=6)

    def test_category_in_use_is_protected(self):
        self.make_request()
        with self.assertRaises(ProtectedError):
            self.category.delete()

    def test_request_accepts_only_one_work_order(self):
        item = self.make_request()
        WorkOrder.objects.create(
            service_request=item,
            technician=self.technician,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                WorkOrder.objects.create(
                    service_request=item,
                    technician=self.technician,
                )

    def test_resolved_and_closed_status_require_resolution_fields(self):
        item = self.make_request()
        item.status = ServiceRequest.Status.RESOLVED

        # Missing both resolved_at and resolution_summary -> fails
        with self.assertRaises(ValidationError) as ctx:
            item.full_clean()
        self.assertIn("resolved_at", ctx.exception.message_dict)
        self.assertIn("resolution_summary", ctx.exception.message_dict)

        # Missing only resolution_summary -> fails
        item.resolved_at = timezone.now()
        item.resolution_summary = ""
        with self.assertRaises(ValidationError):
            item.full_clean()

        # Both present -> succeeds
        item.resolution_summary = "Replaced faulty socket faceplate and verified 230V line."
        item.full_clean()
        item.save()
        self.assertEqual(item.status, ServiceRequest.Status.RESOLVED)

        # Same requirement holds for CLOSED status
        item.status = ServiceRequest.Status.CLOSED
        item.full_clean()
        item.save()
        self.assertEqual(item.status, ServiceRequest.Status.CLOSED)

    def test_due_date_query_filter(self):
        """
        Task 1 item 5: Create two requests with different due dates
        and query those due before a chosen time.
        """
        now = timezone.now()
        early_due = now + timedelta(hours=2)
        late_due = now + timedelta(days=5)
        cutoff = now + timedelta(days=1)

        req1 = self.make_request(title="Urgent switch repair", due_at=early_due)
        req2 = self.make_request(title="Scheduled bulb replacement", due_at=late_due)

        due_before_cutoff = ServiceRequest.objects.filter(due_at__lt=cutoff)
        self.assertIn(req1, due_before_cutoff)
        self.assertNotIn(req2, due_before_cutoff)
