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

    # Tokens (UUID hex strings) — full URLs are built dynamically in the serializer
    # so they always reflect the current ngrok / deployment URL from settings.
    attendance_token = models.CharField(max_length=64, blank=True)
    event_qr_token = models.CharField(max_length=64, blank=True)
    registration_token = models.CharField(max_length=64, blank=True)

    # Legacy URL fields kept for backwards-compatible token lookups on old rows.
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
        """Generate unique tokens when the event is first created."""
        if not self.registration_token:
            self.registration_token = uuid.uuid4().hex
        if not self.event_qr_token:
            self.event_qr_token = uuid.uuid4().hex
        if not self.attendance_token:
            self.attendance_token = uuid.uuid4().hex

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