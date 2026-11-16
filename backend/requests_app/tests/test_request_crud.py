from django.contrib.auth import get_user_model
from django.db import transaction
from django.test import TestCase
from django.urls import reverse
from requests_app.models import Category, Comment, ServiceRequest, WorkOrder
from requests_app.services import service_request_assign, service_request_resolve


class ServiceRequestCrudTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user("owner", password="pass12345")
        self.other = User.objects.create_user("other", password="pass12345")
        self.staff_technician = User.objects.create_user(
            "technician", password="pass12345", is_staff=True
        )
        self.category = Category.objects.create(name="Facilities")
        self.item = ServiceRequest.objects.create(
            requester=self.owner,
            category=self.category,
            title="Projector does not display",
            description="The projector reports no HDMI signal.",
            location="Room B12",
            priority=3,
        )

    def test_list_requires_login(self):
        response = self.client.get(reverse("requests:list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_owner_can_open_detail(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("requests:detail", args=[self.item.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.item.title)

    def test_other_requester_receives_404(self):
        self.client.force_login(self.other)
        response = self.client.get(reverse("requests:detail", args=[self.item.id]))
        self.assertEqual(response.status_code, 404)

    def test_valid_post_creates_request_for_logged_in_user(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("requests:create"),
            {
                "category": self.category.id,
                "title": "Air conditioner leaks water",
                "description": "Water drips near the laboratory entrance.",
                "location": "Software Laboratory",
                "priority": 2,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            ServiceRequest.objects.filter(
                requester=self.owner, title="Air conditioner leaks water"
            ).exists()
        )

    def test_invalid_post_does_not_create_request(self):
        self.client.force_login(self.owner)
        before = ServiceRequest.objects.count()
        response = self.client.post(
            reverse("requests:create"),
            {
                "category": self.category.id,
                "title": "Short",
                "description": "",
                "location": "",
                "priority": 1,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ServiceRequest.objects.count(), before)
        self.assertContains(response, "Use at least 8 characters.")

    # Lab 4 Part M: In-Lab Exercise Tests
    def test_non_staff_assignment_returns_403_and_creates_no_work_order(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("requests:assign", args=[self.item.id]),
            {"technician": self.staff_technician.id},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(WorkOrder.objects.count(), 0)

    def test_staff_assignment_creates_work_order_and_sets_assigned(self):
        self.client.force_login(self.staff_technician)
        response = self.client.post(
            reverse("requests:assign", args=[self.item.id]),
            {"technician": self.staff_technician.id},
        )
        self.assertEqual(response.status_code, 302)
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, ServiceRequest.Status.ASSIGNED)
        self.assertTrue(hasattr(self.item, "work_order"))
        self.assertEqual(self.item.work_order.technician, self.staff_technician)

    def test_resolution_without_assignment_fails(self):
        self.client.force_login(self.staff_technician)
        response = self.client.post(
            reverse("requests:resolve", args=[self.item.id]),
            {
                "work_notes": "Fixed cable connection.",
                "resolution_summary": "Replaced faulty HDMI cable.",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.item.refresh_from_db()
        self.assertNotEqual(self.item.status, ServiceRequest.Status.RESOLVED)

    def test_assigned_technician_resolution_changes_both_models(self):
        service_request_assign(
            item=self.item,
            technician=self.staff_technician,
            actor=self.staff_technician,
        )
        self.client.force_login(self.staff_technician)
        response = self.client.post(
            reverse("requests:resolve", args=[self.item.id]),
            {
                "work_notes": "Swapped projector HDMI input port and updated firmware.",
                "resolution_summary": "Projector display restored successfully.",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, ServiceRequest.Status.RESOLVED)
        self.assertIsNotNone(self.item.resolved_at)
        self.assertEqual(
            self.item.resolution_summary,
            "Projector display restored successfully.",
        )
        self.assertIsNotNone(self.item.work_order.completed_at)
        self.assertEqual(
            self.item.work_order.work_notes,
            "Swapped projector HDMI input port and updated firmware.",
        )

    def test_filtered_pagination_preserves_query_and_status(self):
        self.client.force_login(self.owner)
        # Create 12 requests so pagination is active
        for i in range(12):
            ServiceRequest.objects.create(
                requester=self.owner,
                category=self.category,
                title=f"Sample laboratory request {i}",
                description="Periodic maintenance required.",
                location="Lab A",
                priority=3,
                status=ServiceRequest.Status.OPEN,
            )
        response = self.client.get(
            reverse("requests:list"), {"q": "Sample", "status": "open", "page": "1"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "q=Sample")
        self.assertContains(response, "status=open")
        self.assertContains(response, "page=2")

    def test_rollback_ensures_atomicity(self):
        before_status = self.item.status
        before_count = WorkOrder.objects.count()
        try:
            with transaction.atomic():
                WorkOrder.objects.create(
                    service_request=self.item, technician=self.staff_technician
                )
                self.item.status = ServiceRequest.Status.ASSIGNED
                self.item.save(update_fields=["status", "updated_at"])
                raise RuntimeError("Deliberate failure to test rollback")
        except RuntimeError:
            pass

        self.item.refresh_from_db()
        self.assertEqual(self.item.status, before_status)
        self.assertEqual(WorkOrder.objects.count(), before_count)
