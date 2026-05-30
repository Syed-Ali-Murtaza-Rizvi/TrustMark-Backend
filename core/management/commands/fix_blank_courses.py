from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from django.db.models.functions import Trim

from core.models import Course


class Command(BaseCommand):
    help = "Fix blank course_code/course_name values for existing Course rows."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would change without writing to database.",
        )

    @staticmethod
    def _is_blank(value):
        return not (value or "").strip()

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        queryset = Course.objects.annotate(
            code_trim=Trim("course_code"),
            name_trim=Trim("course_name"),
        ).filter(Q(code_trim="") | Q(name_trim=""))

        total = queryset.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS("No blank course rows found."))
            return

        self.stdout.write(f"Found {total} course rows with blank code or name.")

        updated = 0

        with transaction.atomic():
            for course in queryset:
                original_code = course.course_code or ""
                original_name = course.course_name or ""

                new_code = original_code
                new_name = original_name

                if self._is_blank(new_code):
                    new_code = f"COURSE-{course.course_id}"

                if self._is_blank(new_name):
                    new_name = new_code if not self._is_blank(new_code) else f"Course {course.course_id}"

                if new_code == original_code and new_name == original_name:
                    continue

                related_taught = course.taught_courses.count()
                related_students = course.student_courses.count()

                self.stdout.write(
                    f"Course {course.course_id}: code {original_code!r} -> {new_code!r}, "
                    f"name {original_name!r} -> {new_name!r} "
                    f"(taught_courses={related_taught}, student_courses={related_students})"
                )

                if not dry_run:
                    course.course_code = new_code
                    course.course_name = new_name
                    course.save(update_fields=["course_code", "course_name"])

                updated += 1

            if dry_run:
                transaction.set_rollback(True)

        if dry_run:
            self.stdout.write(self.style.WARNING(f"Dry-run complete. {updated} row(s) would be updated."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Done. Updated {updated} row(s)."))
