from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
import base64
import io
import qrcode
from django.utils import timezone
from rest_framework import serializers
from .models import Event, Registration, Attendance, EventParticipant


class EventSerializer(serializers.ModelSerializer):
    """
    Event serializer with frontend-compatible field names matching EventData.js / EventCard /
    EventModal / CreateEventModal in the React frontend.
    """
    organiser = serializers.ReadOnlyField(source='organiser.username')

    # ── Frontend-compatible field aliases ───────────────────────────────────────
    # 'date'  ← event_date (DateField → "YYYY-MM-DD")
    date = serializers.DateField(source='event_date', required=False, allow_null=True)

    # 'regStart' / 'regEnd' ← registration_start / registration_end
    # DateTimeField with format='%Y-%m-%d' outputs a plain date string matching EventData.js
    regStart = serializers.DateTimeField(
        source='registration_start', required=False, allow_null=True, format='%Y-%m-%d',
    )
    regEnd = serializers.DateTimeField(
        source='registration_end', required=False, allow_null=True, format='%Y-%m-%d',
    )

    # 'registrationLink' ← registration_link
    registrationLink = serializers.URLField(
        source='registration_link', required=False, allow_blank=True, default='',
    )

    # 'qrImage' ← attendance_qr_code_url
    qrImage = serializers.SerializerMethodField()
    isUpcoming = serializers.SerializerMethodField()

    # ── Computed / nested fields ─────────────────────────────────────────────────
    registeredCount = serializers.SerializerMethodField()
    participants = serializers.SerializerMethodField()
    attendance = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            'id',
            'title',
            'description',
            'venue',
            'geo',
            'organiser',
            'date',
            'regStart',
            'regEnd',
            'registrationLink',
            'qrImage',
            'isUpcoming',
            'registeredCount',
            'participants',
            'attendance',
            'capacity',
            'created_at',
        ]

    # ── SerializerMethodField implementations ────────────────────────────────────

    def get_registeredCount(self, obj):
        return obj.registrations.count()

    def get_isUpcoming(self, obj):
        now = timezone.now()
        today = now.date()
        if obj.event_date:
            return obj.event_date >= today
        if obj.start_time:
            return obj.start_time >= now
        return False

    def get_participants(self, obj):
        result = []
        for reg in obj.registrations.select_related('user').all():
            user = reg.user
            phone = ''
            age = None
            display_name = user.get_full_name() or user.username
            try:
                ep = user.event_participant
                display_name = ep.display_name or display_name
                phone = ep.phone or ''
                age = ep.age
            except EventParticipant.DoesNotExist:
                pass
            result.append({
                'id': str(user.id),
                'name': display_name,
                'email': user.email,
                'phone': phone,
                'age': age,
            })
        return result

    def get_qrImage(self, obj):
        """Return a scannable QR image as base64 data URL for this event."""
        qr_payload = obj.attendance_qr_code_url or obj.registration_link or f"event:{obj.id}"
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_payload)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return f'data:image/png;base64,{img_base64}'

    def get_attendance(self, obj):
        result = []
        for reg in obj.registrations.select_related('user', 'attendance').all():
            try:
                att = reg.attendance
                result.append({
                    'id': str(reg.user.id),
                    'status': 'present' if att.present else 'absent',
                    'time': timezone.localtime(att.timestamp).strftime('%I:%M %p') if att.timestamp else '',
                })
            except Attendance.DoesNotExist:
                pass
        return result


class EventParticipantRegistrationSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, required=True)
    display_name = serializers.CharField(required=False, allow_blank=True, default='')
    phone = serializers.CharField(required=False, allow_blank=True, default='')
    age = serializers.IntegerField(required=False, allow_null=True, default=None)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('Username already exists.')
        return value

    def validate_password(self, value):
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(e.messages)
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
        )
        return EventParticipant.objects.create(
            user=user,
            display_name=validated_data.get('display_name', ''),
            phone=validated_data.get('phone', ''),
            age=validated_data.get('age'),
        )


class EventParticipantLoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, required=True)
    login_as = serializers.CharField(required=False, default='event_participant')


class RegistrationSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')

    class Meta:
        model = Registration
        fields = '__all__'


class AttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = '__all__'

