import uuid

from django.db import models
from django.conf import settings


class Event(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    # Core scheduling fields
    event_date = models.DateField(null=True, blank=True)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)

    # Location / venue data
    venue = models.CharField(max_length=255, blank=True)
    geo_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    geo_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    # Registration window
    registration_start = models.DateTimeField(null=True, blank=True)
    registration_end = models.DateTimeField(null=True, blank=True)

    # QR Codes / Links
    attendance_qr_code_url = models.URLField(blank=True)
    event_qr_code_url = models.URLField(blank=True)
    registration_link = models.URLField(blank=True)

    # Free-text geo location string (e.g. "28.6139° N, 77.2090° E") as sent by the frontend
    geo = models.CharField(max_length=255, blank=True, default='')

    organiser = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='organised_events')
    capacity = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        """Generate unique URLs when the event is first created."""
        # Use a stable base URL; in production you may want to override this via settings.
        base_url = getattr(settings, 'DEFAULT_EVENT_BASE_URL', 'http://localhost:8000')

        def _make_url(path_prefix: str) -> str:
            token = uuid.uuid4().hex
            return f"{base_url}/{path_prefix}/{token}"

        if not self.registration_link:
            self.registration_link = _make_url('event-register')
        if not self.event_qr_code_url:
            self.event_qr_code_url = _make_url('event-qr')
        if not self.attendance_qr_code_url:
            self.attendance_qr_code_url = _make_url('attendance-qr')

        super().save(*args, **kwargs)


class EventParticipant(models.Model):
    """A lightweight profile for users who participate in events."""
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='event_participant',
    )
    display_name = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=30, blank=True, default='')
    age = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.display_name or self.user.username


class EventAdvisor(models.Model):
    """A lightweight profile for event admins/advisors."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='event_advisor',
    )
    name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Registration(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='registrations')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='registrations')
    registered_at = models.DateTimeField(auto_now_add=True)
    attended = models.BooleanField(default=False)
    face_embedding = models.JSONField(default=list, blank=True)

    class Meta:
        unique_together = ('user', 'event')


class Attendance(models.Model):
    registration = models.OneToOneField(Registration, on_delete=models.CASCADE, related_name='attendance')
    timestamp = models.DateTimeField(auto_now_add=True)
    present = models.BooleanField(default=True)

    def __str__(self):
        return f"Attendance for {self.registration.user} - {self.registration.event}"

#comment