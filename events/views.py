from django.contrib.auth import authenticate, login, logout
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings
from django.shortcuts import get_object_or_404, redirect
from django.db import models
from django.utils import timezone
import json
import requests

from .models import Event, Registration, Attendance, EventParticipant
from core.models import UserFaceEmbedding
from core.views import register_face_with_cv_module, FaceRegistrationServiceError
from .serializers import (
    EventSerializer,
    RegistrationSerializer,
    AttendanceSerializer,
    EventParticipantRegistrationSerializer,
    EventParticipantLoginSerializer,
)


class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return getattr(obj, 'organiser', None) == request.user


def _is_event_upcoming(event):
    now = timezone.now()
    today = now.date()
    if event.event_date:
        return event.event_date >= today
    if event.start_time:
        return event.start_time >= now
    return False


def _event_from_registration_token(token):
    if not token:
        return None
    return Event.objects.filter(registration_link__iendswith=f"/{token}").first()


def _event_from_attendance_token(token):
    if not token:
        return None
    return Event.objects.filter(attendance_qr_code_url__iendswith=f"/{token}").first()


def _verify_face_for_user(user, uploaded_file):
    if uploaded_file is None:
        return False, {'error': 'face_image file is required'}

    profile = UserFaceEmbedding.objects.filter(user=user).first()
    if not profile or not profile.embedding:
        return False, {'error': 'No registered face embedding found for this user'}

    verify_url = getattr(settings, 'CV_MODULE_VERIFY_URL', '').strip()
    timeout_seconds = float(getattr(settings, 'CV_MODULE_TIMEOUT_SECONDS', 15))
    if not verify_url:
        return False, {'error': 'CV_MODULE_VERIFY_URL is not configured'}

    uploaded_file.seek(0)
    content_type = getattr(uploaded_file, 'content_type', None) or 'application/octet-stream'
    files = {'file': (uploaded_file.name, uploaded_file.read(), content_type)}
    data = {'stored_embedding': json.dumps(profile.embedding)}

    try:
        cv_resp = requests.post(verify_url, files=files, data=data, timeout=timeout_seconds)
    except requests.RequestException as exc:
        return False, {'error': f'CV verification call failed: {exc}'}

    try:
        payload = cv_resp.json()
    except ValueError:
        return False, {'error': f'CV module returned non-JSON response ({cv_resp.status_code})'}

    if cv_resp.status_code >= 400:
        return False, {'error': payload.get('error', 'CV verification failed'), 'cv_response': payload}

    is_match = bool(payload.get('is_match'))
    return is_match, payload


class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]

    def get_queryset(self):
        # Event admins should manage only their own events.
        return Event.objects.filter(organiser=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(organiser=self.request.user)

    @action(detail=True, methods=['post'])
    def register(self, request, pk=None):
        event = self.get_object()
        if not _is_event_upcoming(event):
            return Response(
                {'error': 'Registration is closed for this event'},
                status=status.HTTP_400_BAD_REQUEST
            )
        reg, created = Registration.objects.get_or_create(user=request.user, event=event)
        serializer = RegistrationSerializer(reg)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class EventParticipantRegistrationView(APIView):
    """API endpoint for creating event participant user accounts."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = EventParticipantRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            participant = serializer.save()
            return Response({
                'message': 'Participant registered successfully',
                'username': participant.user.username,
                'display_name': participant.display_name,
                'phone': participant.phone,
                'age': participant.age,
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EventParticipantLoginView(APIView):
    """API endpoint for participant login."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = EventParticipantLoginSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data['username']
            password = serializer.validated_data['password']
            login_as = serializer.validated_data.get('login_as', '').lower()

            if login_as and login_as != 'event_participant':
                return Response({'error': 'Invalid login_as value'}, status=status.HTTP_400_BAD_REQUEST)

            user = authenticate(username=username, password=password)
            if user is None:
                return Response({'error': 'Invalid username or password'}, status=status.HTTP_401_UNAUTHORIZED)

            try:
                participant = user.event_participant
            except EventParticipant.DoesNotExist:
                return Response({'error': 'Event participant profile not found for this user'}, status=status.HTTP_404_NOT_FOUND)

            refresh = RefreshToken.for_user(user)
            return Response({
                'message': 'Login successful',
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user_type': 'event_participant',
                'id': user.id,
                'name': participant.display_name or user.username,
                'email': user.email,
                'username': user.username,
                'display_name': participant.display_name,
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EventParticipantLogoutView(APIView):
    """API endpoint to log out an event participant (session based)."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({'message': 'Logged out successfully'})


class RegistrationViewSet(viewsets.ModelViewSet):
    queryset = Registration.objects.select_related('event', 'user').all()
    serializer_class = RegistrationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # users see their registrations; organisers can see registrations for their events
        user = self.request.user
        return Registration.objects.filter(models.Q(user=user) | models.Q(event__organiser=user))

    @action(detail=True, methods=['post'])
    def mark_attendance(self, request, pk=None):
        reg = self.get_object()
        # only organiser of the event or the user themself can mark attendance
        if request.user != reg.user and request.user != reg.event.organiser:
            return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
        reg.attended = True
        reg.save()
        att, _ = Attendance.objects.get_or_create(registration=reg, defaults={'present': True})
        serializer = AttendanceSerializer(att)
        return Response(serializer.data)


class AttendanceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Attendance.objects.select_related('registration__user', 'registration__event').all()
    serializer_class = AttendanceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Attendance.objects.filter(models.Q(registration__user=user) | models.Q(registration__event__organiser=user))


class ParticipantDashboardView(APIView):
    """Participant dashboard: list upcoming events with registration/attendance status."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        now = timezone.now()
        today = now.date()
        user = request.user

        participant_profile = EventParticipant.objects.filter(user=user).first()
        registrations = (
            Registration.objects
            .filter(user=user)
            .select_related('event')
            .prefetch_related('attendance')
            .order_by('-registered_at')
        )

        def _format_date(event):
            if event.event_date:
                return event.event_date.strftime('%m/%d/%Y')
            if event.start_time:
                return timezone.localtime(event.start_time).strftime('%m/%d/%Y')
            return ''

        def _event_payload(reg):
            event = reg.event
            attended = None
            try:
                attendance = reg.attendance
                attended = bool(attendance.present)
            except Attendance.DoesNotExist:
                attended = bool(reg.attended) if reg.attended else None

            return {
                'id': f'evt-{event.id}',
                'title': event.title,
                'venue': event.venue or '',
                'date': _format_date(event),
                'description': event.description or '',
                'attended': attended,
            }

        upcoming_events = []
        past_events = []
        for reg in registrations:
            event = reg.event
            is_upcoming = False
            if event.event_date and event.event_date >= today:
                is_upcoming = True
            elif event.start_time and event.start_time >= now:
                is_upcoming = True

            payload = _event_payload(reg)
            if is_upcoming:
                upcoming_events.append(payload)
            else:
                past_events.append(payload)

        return Response({
            'profile': {
                'name': (participant_profile.display_name if participant_profile else '') or user.get_full_name() or user.username,
                'email': user.email or '',
                'phone': participant_profile.phone if participant_profile else '',
            },
            'upcomingEvents': upcoming_events,
            'pastEvents': past_events,
        })


class EventRegisterByLinkView(APIView):
    """Resolve registration links and register authenticated participants."""

    permission_classes = [permissions.AllowAny]

    def get(self, request, token):
        event = _event_from_registration_token(token)
        if not event:
            return Response({'error': 'Invalid registration link'}, status=status.HTTP_404_NOT_FOUND)
        return Response({
            'eventId': event.id,
            'title': event.title,
            'isUpcoming': _is_event_upcoming(event),
        })

    def post(self, request, token):
        event = _event_from_registration_token(token)
        if not event:
            return Response({'error': 'Invalid registration link'}, status=status.HTTP_404_NOT_FOUND)

        if not request.user or not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        participant = EventParticipant.objects.filter(user=request.user).first()
        if not participant:
            return Response(
                {'error': 'Only participant accounts can register via event links'},
                status=status.HTTP_403_FORBIDDEN
            )

        if not _is_event_upcoming(event):
            return Response(
                {'error': 'Registration is closed for this event'},
                status=status.HTTP_400_BAD_REQUEST
            )

        registration, created = Registration.objects.get_or_create(user=request.user, event=event)
        return Response({
            'message': 'Registered successfully' if created else 'Already registered for this event',
            'eventId': event.id,
            'registrationId': registration.id,
            'alreadyRegistered': not created,
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class EventAttendanceByLinkView(APIView):
    """Resolve attendance QR links and mark attendance for participants."""

    permission_classes = [permissions.AllowAny]

    def get(self, request, token):
        event = _event_from_attendance_token(token)
        if not event:
            return Response({'error': 'Invalid attendance QR link'}, status=status.HTTP_404_NOT_FOUND)
        return Response({
            'eventId': event.id,
            'title': event.title,
            'isUpcoming': _is_event_upcoming(event),
        })

    def post(self, request, token):
        event = _event_from_attendance_token(token)
        if not event:
            return Response({'error': 'Invalid attendance QR link'}, status=status.HTTP_404_NOT_FOUND)

        if not request.user or not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        participant = EventParticipant.objects.filter(user=request.user).first()
        if not participant:
            return Response(
                {'error': 'Only participant accounts can mark attendance via QR'},
                status=status.HTTP_403_FORBIDDEN
            )

        registration = Registration.objects.filter(user=request.user, event=event).first()
        if not registration:
            return Response(
                {'error': 'You must register for this event before marking attendance'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not _is_event_upcoming(event):
            return Response(
                {'error': 'Attendance is closed for this event'},
                status=status.HTTP_400_BAD_REQUEST
            )

        face_image = request.FILES.get('face_image') or request.FILES.get('file')
        is_match, verify_payload = _verify_face_for_user(request.user, face_image)
        if not is_match:
            message = verify_payload.get('error') or 'Face does not match, please try again.'
            return Response(
                {
                    'error': message,
                    'is_match': False,
                    'verify': verify_payload,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        registration.attended = True
        registration.save(update_fields=['attended'])
        attendance, created = Attendance.objects.get_or_create(
            registration=registration,
            defaults={'present': True},
        )
        if not created and not attendance.present:
            attendance.present = True
            attendance.save(update_fields=['present'])

        return Response({
            'message': 'Attendance marked successfully',
            'eventId': event.id,
            'attendanceId': attendance.id,
            'is_match': True,
            'verify': verify_payload,
        }, status=status.HTTP_200_OK)


def event_register_redirect(request, token):
    """Handle clicked event registration links by redirecting to frontend login."""
    frontend_base = getattr(settings, 'FRONTEND_BASE_URL', 'http://localhost:5173').rstrip('/')
    return redirect(f"{frontend_base}/login?eventToken={token}")


def attendance_qr_redirect(request, token):
    """Handle attendance QR links by redirecting to frontend login."""
    frontend_base = getattr(settings, 'FRONTEND_BASE_URL', 'http://localhost:5173').rstrip('/')
    return redirect(f"{frontend_base}/login?attendanceToken={token}")


class RegisterFaceForEventView(APIView):
    """
    Endpoint to register face for a participant after event registration.
    
    POST /api/events/register-face/
    Request: { "registration_id": int, "face_image": file }
    OR: { "event_token": "token", "face_image": file }
    
    The user must be authenticated and be the participant who registered for the event.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        registration_id = request.data.get('registration_id')
        event_token = request.data.get('event_token')
        face_image = request.FILES.get('face_image') or request.FILES.get('file')

        if face_image is None:
            return Response(
                {'error': 'face_image file is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Find registration
        registration = None
        if registration_id:
            try:
                registration = Registration.objects.get(
                    id=registration_id,
                    user=request.user
                )
            except Registration.DoesNotExist:
                return Response(
                    {'error': 'Registration not found or you are not the participant'},
                    status=status.HTTP_404_NOT_FOUND
                )
        elif event_token:
            event = _event_from_registration_token(event_token)
            if not event:
                return Response(
                    {'error': 'Invalid event token'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            registration = Registration.objects.filter(
                user=request.user,
                event=event
            ).first()
            if not registration:
                return Response(
                    {'error': 'You are not registered for this event'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            return Response(
                {'error': 'registration_id or event_token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if already has face embedding
        if registration.face_embedding:
            return Response(
                {'error': 'Face already registered for this event'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Call CV module to register face
        try:
            cv_payload = register_face_with_cv_module(request.user.id, face_image)
        except FaceRegistrationServiceError as exc:
            return Response(
                {'error': f'Face registration failed: {exc}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as exc:
            return Response(
                {'error': f'Face registration failed: {exc}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        embedding = (
            cv_payload.get('embedding')
            or cv_payload.get('embeddings')
            or cv_payload.get('face_embedding')
        )

        if embedding is None:
            return Response(
                {'error': 'CV module did not return an embedding'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Save embedding to registration
        registration.face_embedding = embedding
        registration.save(update_fields=['face_embedding'])

        return Response(
            {
                'message': cv_payload.get('message', 'Face registered successfully for event'),
                'registration_id': registration.id,
                'event_id': registration.event.id,
                'event_title': registration.event.title,
            },
            status=status.HTTP_200_OK
        )
