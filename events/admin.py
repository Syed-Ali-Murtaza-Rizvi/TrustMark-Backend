from django.contrib import admin
from .models import Event, Registration, Attendance


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'organiser', 'start_time', 'end_time')
    search_fields = ('title', 'description')


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ('user', 'event', 'registered_at', 'attended')
    list_filter = ('attended',)


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('registration', 'timestamp', 'present')
