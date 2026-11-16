from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone
from requests_app.models import Category, ServiceRequest


class Command(BaseCommand):
    help = "Lab Session 3 Part N Task 3: Analyse query and print query and explain plan."

    def handle(self, *args, **options):
        User = get_user_model()
        user, _ = User.objects.get_or_create(username="synthetic_student")

        cat_electrical, _ = Category.objects.get_or_create(
            name="Electrical", defaults={"description": "Electrical maintenance"}
        )
        cat_ict, _ = Category.objects.get_or_create(
            name="ICT Support", defaults={"description": "Computers and networking"}
        )

        now = timezone.now()
        synthetic_data = [
            ("Lab 1 Circuit Breaker Tripped", cat_electrical, ServiceRequest.Status.OPEN, 1, now - timedelta(hours=5)),
            ("Server Rack Cooling Fan Noisy", cat_ict, ServiceRequest.Status.ASSIGNED, 2, now - timedelta(hours=4)),
            ("Room 102 Light Flickering", cat_electrical, ServiceRequest.Status.OPEN, 4, now - timedelta(hours=3)),
            ("Switch Port 12 Down", cat_ict, ServiceRequest.Status.OPEN, 2, now - timedelta(hours=3)),
            ("Projector Power Socket Dead", cat_electrical, ServiceRequest.Status.ASSIGNED, 2, now - timedelta(hours=2)),
            ("Network Printer Offline", cat_ict, ServiceRequest.Status.IN_PROGRESS, 3, now - timedelta(hours=2)),
            ("Main Hall AC Thermostat Error", cat_electrical, ServiceRequest.Status.IN_PROGRESS, 1, now - timedelta(hours=1)),
            ("DNS Resolution Failing in Lab 3", cat_ict, ServiceRequest.Status.OPEN, 1, now - timedelta(minutes=45)),
            ("Corridor Emergency Light Broken", cat_electrical, ServiceRequest.Status.OPEN, 5, now - timedelta(minutes=30)),
            ("Faculty Router Firmware Outdated", cat_ict, ServiceRequest.Status.ASSIGNED, 3, now - timedelta(minutes=15)),
            ("Library Socket Sparking", cat_electrical, ServiceRequest.Status.OPEN, 1, now - timedelta(minutes=5)),
        ]

        created_count = 0
        for title, cat, status, priority, created in synthetic_data:
            req, created_flag = ServiceRequest.objects.get_or_create(
                title=title,
                defaults={
                    "requester": user,
                    "category": cat,
                    "status": status,
                    "priority": priority,
                    "location": "Veritas Campus",
                    "description": f"Synthetic test request for {title}",
                    "due_at": now + timedelta(days=2),
                },
            )
            if created_flag:
                created_count += 1

        self.stdout.write(self.style.SUCCESS(f"Ensured {len(synthetic_data)} synthetic service requests exist ({created_count} newly created)."))

        # Query: Open or assigned requests in Electrical ordered by priority and created date
        queryset = ServiceRequest.objects.filter(
            category=cat_electrical,
            status__in=[ServiceRequest.Status.OPEN, ServiceRequest.Status.ASSIGNED],
        ).order_by("priority", "created_at")

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("1. GENERATED SQL QUERY (queryset.query):")
        self.stdout.write("=" * 80)
        self.stdout.write(str(queryset.query))

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("2. QUERY EXECUTION PLAN (queryset.explain()):")
        self.stdout.write("=" * 80)
        explain_output = queryset.explain()
        self.stdout.write(explain_output)

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("3. INDEX USAGE ANALYSIS & EXPLANATION:")
        self.stdout.write("=" * 80)
        self.stdout.write(
            "Relevant Indexes Defined on ServiceRequest:\n"
            "  - req_cat_status_idx: (category_id, status)\n"
            "  - req_priority_date_idx: (priority, created_at)\n"
            "  - req_status_due_idx: (status, due_at)\n\n"
            "Index Selection Behavior:\n"
            "  - Filter Condition: WHERE category_id = ... AND status IN ('open', 'assigned')\n"
            "    This condition directly matches the leading columns of 'req_cat_status_idx'.\n"
            "  - Order Condition: ORDER BY priority, created_at\n"
            "    This matches 'req_priority_date_idx'.\n\n"
            "Cost-Based Optimizer Evaluation:\n"
            "  - In MySQL / SQLite, the optimizer evaluates whether to use 'req_cat_status_idx' to prune rows\n"
            "    and then perform filesort in memory, or use 'req_priority_date_idx' to satisfy ordering.\n"
            "  - For small datasets (e.g. <= a few dozen rows across minimal data pages), the query planner\n"
            "    frequently opts for a full scan or simple index scan because fetching entire data pages into cache\n"
            "    incurs lower disk/CPU overhead than performing secondary index lookups followed by row dereferencing.\n"
            "  - In production volume with thousands of requests, MySQL's cost optimizer prefers 'req_cat_status_idx'\n"
            "    due to high selectivity on the category and status predicates.\n"
        )
        self.stdout.write("=" * 80)
