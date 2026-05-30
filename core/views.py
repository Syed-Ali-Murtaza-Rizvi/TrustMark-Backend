from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import transaction
from django.db.models import Q, Sum
from django.http import HttpResponse
from rest_framework import status, generics, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
import qrcode
import io
import base64
import secrets
import json
import requests
from .serializers import (
    StudentRegistrationSerializer,
    TeacherRegistrationSerializer,
    ManagementRegistrationSerializer,
    LoginSerializer,
    StudentSerializer,
    TeacherSerializer,
    ManagementSerializer,
    CourseSerializer,
    ClassSerializer,
    TaughtCourseSerializer,
    StudentCourseSerializer,
    UpdateAttendanceRequestSerializer,
    AttendanceSessionSerializer,
    AttendanceRecordSerializer,
    RFIDScanSerializer,
    QRScanSerializer,
    StudentAttendanceSummarySerializer,
    StudentAttendanceSummaryListSerializer,
    CourseAttendanceSummarySerializer,
)
from .models import (
    Student, Teacher, Management, StudentCourse, TaughtCourse, Course, Class,
    UpdateAttendanceRequest, AttendanceSession, AttendanceRecord, UserFaceEmbedding,
)
from events.models import EventParticipant, EventAdvisor

# ============ Unified Frontend-Compatible Endpoints ============


class FaceRegistrationServiceError(Exception):
    pass


def register_face_with_cv_module(user_id, uploaded_file):
    """
    Forward the uploaded image and user_id to the external CV service.
    Returns parsed JSON payload from the CV module.
    """
    if uploaded_file is None:
        raise FaceRegistrationServiceError("Face image file is required")

    content_type = getattr(uploaded_file, 'content_type', None) or 'application/octet-stream'
    register_url = getattr(settings, 'CV_MODULE_REGISTER_URL', '').strip()
    timeout_seconds = float(getattr(settings, 'CV_MODULE_TIMEOUT_SECONDS', 10))
    if not register_url:
        raise FaceRegistrationServiceError("CV_MODULE_REGISTER_URL is not configured")

    uploaded_file.seek(0)
    files = {'file': (uploaded_file.name, uploaded_file.read(), content_type)}
    data = {'user_id': str(user_id)}

    try:
        cv_response = requests.post(
            register_url,
            files=files,
            data=data,
            timeout=timeout_seconds,
        )
    except requests.RequestException as exc:
        raise FaceRegistrationServiceError(f"CV module call failed: {exc}") from exc

    try:
        payload = cv_response.json()
    except ValueError as exc:
        raise FaceRegistrationServiceError(
            f"CV module returned non-JSON response (status {cv_response.status_code})"
        ) from exc

    if cv_response.status_code >= 400:
        error_text = payload.get('error') if isinstance(payload, dict) else str(payload)
        raise FaceRegistrationServiceError(
            f"CV module registration failed ({cv_response.status_code}): {error_text}"
        )

    if not isinstance(payload, dict):
        raise FaceRegistrationServiceError("CV module response must be a JSON object")

    return payload


def persist_user_face_embedding(user, cv_payload):
    """
    Store face embedding returned by CV module against Django auth user.
    """
    embedding = (
        cv_payload.get('embedding')
        or cv_payload.get('embeddings')
        or cv_payload.get('face_embedding')
    )

    if embedding is None:
        raise FaceRegistrationServiceError(
            "CV module did not return an embedding payload"
        )

    profile, _ = UserFaceEmbedding.objects.update_or_create(
        user=user,
        defaults={
            'embedding': embedding,
            'cv_response': cv_payload,
        },
    )
    return profile


def verify_face_with_cv_module(uploaded_file, stored_embedding):
    """
    Call CV /verify endpoint with a live image and stored embedding.
    """
    if uploaded_file is None:
        raise FaceRegistrationServiceError("Face image file is required")
    if not stored_embedding:
        raise FaceRegistrationServiceError("No stored embedding found for user")

    verify_url = getattr(settings, 'CV_MODULE_VERIFY_URL', '').strip()
    timeout_seconds = float(getattr(settings, 'CV_MODULE_TIMEOUT_SECONDS', 10))
    if not verify_url:
        raise FaceRegistrationServiceError("CV_MODULE_VERIFY_URL is not configured")

    uploaded_file.seek(0)
    content_type = getattr(uploaded_file, 'content_type', None) or 'application/octet-stream'
    files = {'file': (uploaded_file.name, uploaded_file.read(), content_type)}
    data = {'stored_embedding': json.dumps(stored_embedding)}

    try:
        cv_response = requests.post(
            verify_url,
            files=files,
            data=data,
            timeout=timeout_seconds,
        )
    except requests.RequestException as exc:
        raise FaceRegistrationServiceError(f"CV verify call failed: {exc}") from exc

    try:
        payload = cv_response.json()
    except ValueError as exc:
        raise FaceRegistrationServiceError(
            f"CV module returned non-JSON response (status {cv_response.status_code})"
        ) from exc

    if cv_response.status_code >= 400:
        error_text = payload.get('error') if isinstance(payload, dict) else str(payload)
        raise FaceRegistrationServiceError(
            f"CV module verification failed ({cv_response.status_code}): {error_text}"
        )

    if not isinstance(payload, dict):
        raise FaceRegistrationServiceError("CV module verify response must be a JSON object")

    return payload

class UnifiedLoginView(APIView):
    """
    Unified login endpoint matching the frontend's expected format.

    POST /api/login
    Request body: { "email": "...", "password": "...", "role": "student|teacher|admin" }

    The frontend (Login.jsx) sends a single { email, password, role } payload.
    Role "admin" is mapped to the Management model.
    """
    permission_classes = [AllowAny]

    ROLE_MAP = {
        'student': (Student, 'student'),
        'teacher': (Teacher, 'teacher'),
        'admin': (Management, 'admin'),
        'management': (Management, 'admin'),
        'orgadmin': (Management, 'admin'),
        'advisor': (EventAdvisor, 'advisor'),
        'eventadmin': (EventAdvisor, 'advisor'),
        'event_admin': (EventAdvisor, 'advisor'),
        'participant': (EventParticipant, 'participant'),
    }

    def post(self, request):
        email = request.data.get('email', '').strip()
        password = request.data.get('password', '')
        role = request.data.get('role', 'student').strip().lower()

        if not email or not password:
            return Response(
                {'error': 'Email and password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if role not in self.ROLE_MAP:
            return Response(
                {'error': f'Invalid role. Must be one of: {", ".join(self.ROLE_MAP)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(username=email, password=password)
        if user is None:
            return Response(
                {'error': 'Invalid email or password'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        ModelClass, user_type = self.ROLE_MAP[role]
        try:
            profile = ModelClass.objects.get(user=user)
        except ModelClass.DoesNotExist:
            return Response(
                {'error': 'Invalid credentials or role'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        refresh = RefreshToken.for_user(user)

        if user_type == 'student':
            response_data = {
                'message': 'Login successful',
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user_type': 'student',
                'id': profile.student_id,
                'name': profile.student_name,
                'email': profile.email,
            }
        elif user_type == 'teacher':
            response_data = {
                'message': 'Login successful',
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user_type': 'teacher',
                'id': profile.teacher_id,
                'name': profile.teacher_name,
                'email': profile.email,
            }
        elif user_type == 'advisor':
            response_data = {
                'message': 'Login successful',
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user_type': 'advisor',
                'id': profile.id,
                'name': profile.name,
                'email': user.email,
            }
        elif user_type == 'participant':
            response_data = {
                'message': 'Login successful',
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user_type': 'participant',
                'id': profile.id,
                'name': profile.display_name or user.username,
                'email': user.email,
            }
        else:  # admin / management
            response_data = {
                'message': 'Login successful',
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user_type': 'admin',
                'id': profile.Management_id,
                'name': profile.Management_name,
                'email': profile.email,
            }

        return Response(response_data, status=status.HTTP_200_OK)


class UnifiedSignupView(APIView):
    """
    Unified signup endpoint matching the frontend's expected format.

    POST /api/signup
    Request body: {
      "role": "student|teacher|admin|management|advisor|eventadmin|participant",
      "name": "...",
      "email": "...",
      "password": "...",
            // Student extras: "id" (used as student_rollNo), "year", "program" (dept), "section"
            // Teacher extras: "id" (used as teacher_rollNo)
      // Event admin extras: "name"
    }

    The frontend (SignUp.jsx and admin ManageStudents/ManageTeacher) sends all
    registration data through this single endpoint.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        role = request.data.get('role', '').strip().lower()
        name = request.data.get('name', '').strip()
        email = request.data.get('email', '').strip()
        password = request.data.get('password', '')
        face_image = request.FILES.get('face_image') or request.FILES.get('file')

        if not role or not name or not email or not password:
            return Response(
                {'error': 'role, name, email and password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if role not in ('student', 'teacher', 'admin', 'management', 'orgadmin', 'advisor', 'eventadmin', 'event_admin', 'participant'):
            return Response(
                {'error': 'Invalid role. Must be one of: student, teacher, admin, management, advisor, eventadmin, participant'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Student/teacher accounts can only be created by authenticated management.
        management = None
        if role in ('student', 'teacher'):
            if not request.user or not request.user.is_authenticated:
                return Response(
                    {'error': 'Authentication required. Log in as management to register students/teachers.'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            management = Management.objects.filter(user=request.user).first()
            if not management:
                return Response(
                    {'error': 'Only management users can register students/teachers.'},
                    status=status.HTTP_403_FORBIDDEN
                )

        if User.objects.filter(email=email).exists():
            return Response(
                {'error': 'Email already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            validate_password(password)
        except ValidationError as exc:
            messages = list(exc.messages) if hasattr(exc, 'messages') else ['Password does not meet policy requirements']
            return Response(
                {'error': messages[0]},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = User.objects.create_user(username=email, email=email, password=password)

        try:
            registration_response = None
            if role == 'student':
                registration_response = self._register_student(request, user, name, email, management)
            elif role == 'teacher':
                registration_response = self._register_teacher(request, user, name, email, management)
            elif role in ('advisor', 'eventadmin', 'event_admin'):
                registration_response = self._register_event_advisor(request, user, name, email)
            elif role == 'participant':
                registration_response = self._register_participant(request, user, name, email)
            else:  # admin / management / orgadmin
                registration_response = self._register_management(request, user, name, email)

            if face_image is not None:
                cv_payload = register_face_with_cv_module(user.id, face_image)
                persist_user_face_embedding(user, cv_payload)

                if isinstance(registration_response.data, dict):
                    registration_response.data['face'] = {
                        'registered': True,
                        'message': cv_payload.get('message', 'Face registered successfully'),
                    }

            return registration_response
        except Exception as e:
            user.delete()
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @staticmethod
    def _parse_comma_list(value):
        return [v.strip() for v in (value or '').split(',') if v.strip()]

    @staticmethod
    def _parse_courses_input(courses_raw):
        """Parse courses from either string or array payloads."""
        parsed_courses = []
        if not courses_raw:
            return parsed_courses

        if isinstance(courses_raw, str):
            raw = courses_raw.strip()
            if raw.startswith('[') or raw.startswith('{'):
                try:
                    courses_raw = json.loads(raw)
                except (json.JSONDecodeError, TypeError, ValueError):
                    courses_raw = courses_raw

        if isinstance(courses_raw, list):
            for item in courses_raw:
                if isinstance(item, str):
                    code = item.strip()
                    if not code:
                        continue
                    parsed_courses.append({
                        'course_id': None,
                        'course_code': code,
                        'course_name': '',
                        'section': '',
                        'year': None,
                        'program': '',
                    })
                    continue
                if not isinstance(item, dict):
                    continue
                parsed_courses.append({
                    'course_id': item.get('course_id'),
                    'course_code': (item.get('course_code') or '').strip(),
                    'course_name': (item.get('course_name') or '').strip(),
                    'section': (item.get('section') or '').strip(),
                    'year': item.get('year'),
                    'program': (item.get('program') or '').strip(),
                })
            return parsed_courses

        for item in str(courses_raw).split(','):
            item = item.strip()
            if not item:
                continue
            if ':' in item:
                code, _, cname = item.partition(':')
                parsed_courses.append({'course_id': None, 'course_code': code.strip(), 'course_name': cname.strip(), 'section': '', 'year': None, 'program': ''})
            else:
                parsed_courses.append({'course_id': None, 'course_code': '', 'course_name': item, 'section': '', 'year': None, 'program': ''})
        return parsed_courses

    @staticmethod
    def _find_existing_course(course_id, course_code, course_name, management=None):
        if course_id:
            course_qs = Course.objects.filter(pk=course_id)
            if management:
                course_qs = course_qs.filter(
                    Q(taught_courses__teacher__management=management) |
                    Q(student_courses__student__management=management)
                ).distinct()
            return course_qs.first()

        if management:
            scoped_qs = Course.objects.filter(
                Q(taught_courses__teacher__management=management) |
                Q(student_courses__student__management=management)
            ).distinct()
            if course_code:
                course = scoped_qs.filter(course_code=course_code).first()
                if course:
                    return course
            if course_name:
                course = scoped_qs.filter(course_name=course_name).first()
                if course:
                    return course
            return None

        if course_code:
            return Course.objects.filter(course_code=course_code).first()
        if course_name:
            return Course.objects.filter(course_name=course_name).first()
        return None

    @staticmethod
    def _program_matches(teacher_programs_raw, student_program):
        if not student_program:
            return True
        teacher_programs = [p.lower() for p in UnifiedSignupView._parse_comma_list(teacher_programs_raw)]
        return student_program.lower() in teacher_programs

    def _register_student(self, request, user, name, email, management=None):
        student_roll_no = request.data.get('id', '').strip() or f'S{user.id}'
        if Student.objects.filter(student_rollNo=student_roll_no).exists():
            student_roll_no = f'{student_roll_no}_{user.id}'

        year_raw = request.data.get('year', '1')
        try:
            year_int = int(year_raw)
        except (ValueError, TypeError):
            year_int = 1

        dept = (
            request.data.get('program', '').strip() or
            request.data.get('dept', '').strip() or
            ''
        )
        section = request.data.get('section', '').strip() or 'A'

        student = Student.objects.create(
            user=user,
            email=email,
            student_name=name,
            student_rollNo=student_roll_no,
            year=year_int,
            dept=dept,
            section=section,
            management=management,
        )

        # Student registration must only attach courses already taught by a teacher
        # for the same section/year and compatible program (dept).
        assigned_courses = []
        skipped_courses = []
        course_inputs = self._parse_courses_input(request.data.get('courses', ''))

        for course_input in course_inputs:
            course = self._find_existing_course(
                course_id=course_input.get('course_id'),
                course_code=course_input['course_code'],
                course_name=course_input['course_name'],
                management=management,
            )

            if not course:
                skipped_courses.append({
                    'course_code': course_input['course_code'],
                    'course_name': course_input['course_name'],
                    'reason': 'course_not_found',
                })
                continue

            base_taught_qs = TaughtCourse.objects.filter(course=course).select_related('teacher')
            if management:
                base_taught_qs = base_taught_qs.filter(teacher__management=management)

            offered_years = sorted({
                y for y in base_taught_qs.values_list('year', flat=True) if y is not None
            })
            if offered_years and student.year not in offered_years:
                skipped_courses.append({
                    'course_id': course.course_id,
                    'course_code': course.course_code,
                    'course_name': course.course_name,
                    'reason': 'student_year_not_eligible_for_course',
                    'student_year': student.year,
                    'allowed_years': offered_years,
                })
                continue

            taught_qs = base_taught_qs.filter(
                section=student.section,
                year=student.year,
            )

            taught = None
            for tc in taught_qs:
                if tc.teacher and self._program_matches(tc.teacher.programs, student.dept):
                    taught = tc
                    break

            if not taught or not taught.teacher_id:
                skipped_courses.append({
                    'course_id': course.course_id,
                    'course_code': course.course_code,
                    'course_name': course.course_name,
                    'reason': 'no_teacher_mapping_for_student_section_year_program',
                })
                continue

            student_course, created = StudentCourse.objects.get_or_create(
                student=student,
                course=course,
                defaults={'teacher': taught.teacher, 'classes_attended_count': 0}
            )

            # Backfill missing teacher mapping on existing rows.
            if not created and not student_course.teacher_id:
                student_course.teacher = taught.teacher
                student_course.save(update_fields=['teacher'])

            assigned_courses.append({
                'course_id': course.course_id,
                'course_code': course.course_code,
                'course_name': course.course_name,
                'teacher_id': taught.teacher.teacher_id,
                'teacher_name': taught.teacher.teacher_name,
                'section': taught.section,
                'year': taught.year,
                'program': student.dept,
            })

        # If caller provided courses but none can be mapped, reject registration.
        if course_inputs and not assigned_courses:
            raise ValueError('No requested courses are mapped to a teacher for this student section/year/program')

        return Response({
            'message': 'Student registered successfully',
            'user_type': 'student',
            'student_id': student.student_id,
            'name': student.student_name,
            'email': student.email,
            'courses': assigned_courses,
            'skipped_courses': skipped_courses,
        }, status=status.HTTP_201_CREATED)

    def _register_teacher(self, request, user, name, email, management=None):
        teacher_roll_no = request.data.get('id', '').strip() or f'T{user.id}'
        if Teacher.objects.filter(teacher_rollNo=teacher_roll_no).exists():
            teacher_roll_no = f'{teacher_roll_no}_{user.id}'

        phone = request.data.get('phone', '').strip()
        years_raw = (request.data.get('years', '') or '').strip()
        programs_raw = (request.data.get('programs', '') or '').strip()
        course_inputs = self._parse_courses_input(request.data.get('courses', ''))

        # Allow courses payload to drive teacher profile metadata.
        derived_years = []
        derived_programs = []
        for ci in course_inputs:
            try:
                if ci.get('year') is not None and str(ci.get('year')).strip() != '':
                    derived_years.append(int(ci.get('year')))
            except (ValueError, TypeError):
                pass
            if ci.get('program'):
                derived_programs.append(ci.get('program').strip())

        if not years_raw and derived_years:
            years_raw = ','.join(str(y) for y in sorted(set(derived_years)))
        if not programs_raw and derived_programs:
            programs_raw = ','.join(sorted(set(derived_programs)))

        teacher = Teacher.objects.create(
            user=user,
            email=email,
            teacher_name=name,
            teacher_rollNo=teacher_roll_no,
            phone=phone,
            years=years_raw,
            programs=programs_raw,
            management=management,
        )

        # Course creation and taught-course mapping happen at teacher registration.
        created_courses = []
        years = []
        for y in self._parse_comma_list(years_raw):
            try:
                years.append(int(y))
            except (ValueError, TypeError):
                continue

        sections = self._parse_comma_list(
            request.data.get('sections', '').strip() or request.data.get('section', '').strip()
        )
        if not sections:
            sections = ['A']

        for course_input in course_inputs:
            input_code = (course_input.get('course_code') or '').strip()
            input_name = (course_input.get('course_name') or '').strip()

            course = self._find_existing_course(
                course_id=course_input.get('course_id'),
                course_code=input_code,
                course_name=input_name,
                management=management,
            )
            if not course:
                if not input_code and not input_name:
                    raise ValueError('Each course must provide course_id or course_code/course_name')
                course = Course.objects.create(
                    course_code=input_code,
                    course_name=input_name or input_code,
                )
            else:
                update_fields = []
                if input_code and not (course.course_code or '').strip():
                    course.course_code = input_code
                    update_fields.append('course_code')
                if input_name and not (course.course_name or '').strip():
                    course.course_name = input_name
                    update_fields.append('course_name')
                if update_fields:
                    course.save(update_fields=update_fields)

            per_course_sections = [course_input.get('section')] if course_input.get('section') else sections

            per_course_years = []
            try:
                if course_input.get('year') is not None and str(course_input.get('year')).strip() != '':
                    per_course_years = [int(course_input.get('year'))]
            except (ValueError, TypeError):
                per_course_years = []
            if not per_course_years:
                per_course_years = years

            if per_course_years:
                for year in per_course_years:
                    for section in per_course_sections:
                        taught_course, _ = TaughtCourse.objects.get_or_create(
                            teacher=teacher,
                            course=course,
                            section=section,
                            year=year,
                            defaults={'classes_taken_count': 0}
                        )
                        _auto_assign_teacher_to_student_courses(
                            teacher=teacher,
                            course=course,
                            section=taught_course.section,
                            year=taught_course.year,
                        )
            else:
                for section in per_course_sections:
                    taught_course, _ = TaughtCourse.objects.get_or_create(
                        teacher=teacher,
                        course=course,
                        section=section,
                        year=None,
                        defaults={'classes_taken_count': 0}
                    )
                    _auto_assign_teacher_to_student_courses(
                        teacher=teacher,
                        course=course,
                        section=taught_course.section,
                        year=taught_course.year,
                    )

            created_courses.append({
                'course_id': course.course_id,
                'course_code': course.course_code,
                'course_name': course.course_name,
                'sections': per_course_sections,
                'years': per_course_years,
                'programs': self._parse_comma_list(course_input.get('program') or programs_raw),
            })

        return Response({
            'message': 'Teacher registered successfully',
            'user_type': 'teacher',
            'teacher_id': teacher.teacher_id,
            'name': teacher.teacher_name,
            'email': teacher.email,
            'phone': teacher.phone,
            'years': teacher.years,
            'programs': teacher.programs,
            'courses': created_courses,
        }, status=status.HTTP_201_CREATED)

    def _register_management(self, request, user, name, email):
        management = Management.objects.create(
            user=user,
            email=email,
            Management_name=name,
        )
        return Response({
            'message': 'Management user registered successfully',
            'user_type': 'admin',
            'management_id': management.Management_id,
            'name': management.Management_name,
            'email': management.email,
        }, status=status.HTTP_201_CREATED)

    def _register_event_advisor(self, request, user, name, email):
        advisor_name = name or email.split('@')[0]

        advisor = EventAdvisor.objects.create(
            user=user,
            name=advisor_name,
        )
        return Response({
            'message': 'Event admin registered successfully',
            'user_type': 'advisor',
            'advisor_id': advisor.id,
            'name': advisor.name,
            'email': email,
        }, status=status.HTTP_201_CREATED)

    def _register_participant(self, request, user, name, email):
        participant_name = name or email.split('@')[0]
        participant = EventParticipant.objects.create(
            user=user,
            display_name=participant_name,
            phone=(request.data.get('phone') or '').strip(),
            age=request.data.get('age') if request.data.get('age') is not None else None,
        )
        return Response({
            'message': 'Participant registered successfully',
            'user_type': 'participant',
            'participant_id': participant.id,
            'name': participant.display_name,
            'email': email,
        }, status=status.HTTP_201_CREATED)


class FaceRegisterView(APIView):
    """
    Proxy endpoint to register one face with the external CV module and
    persist embedding against a local auth user.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        user_id = request.data.get('user_id')
        face_image = request.FILES.get('face_image') or request.FILES.get('file')

        if not user_id:
            return Response({'error': 'user_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        if face_image is None:
            return Response({'error': 'face_image file is required'}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(id=user_id).first()
        if user is None:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        try:
            cv_payload = register_face_with_cv_module(user.id, face_image)
            profile = persist_user_face_embedding(user, cv_payload)
        except FaceRegistrationServiceError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({'error': f'Face registration failed: {exc}'}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                'message': cv_payload.get('message', 'Face registered successfully'),
                'embedding_saved': True,
                'user_id': user.id,
                'embedding_profile_id': profile.id,
                'cv_response': cv_payload,
            },
            status=status.HTTP_200_OK,
        )


class FaceVerifyView(APIView):
    """
    Proxy endpoint to verify a live face image against stored embedding.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        user_id = request.data.get('user_id')
        face_image = request.FILES.get('face_image') or request.FILES.get('file')

        if not user_id:
            return Response({'error': 'user_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        if face_image is None:
            return Response({'error': 'face_image file is required'}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(id=user_id).first()
        if user is None:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        profile = UserFaceEmbedding.objects.filter(user=user).first()
        if profile is None or not profile.embedding:
            return Response({'error': 'No stored embedding found for this user'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            cv_payload = verify_face_with_cv_module(face_image, profile.embedding)
        except FaceRegistrationServiceError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({'error': f'Face verification failed: {exc}'}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                'message': 'Face verified' if cv_payload.get('is_match') else 'Face does not match',
                'user_id': user.id,
                'is_match': bool(cv_payload.get('is_match')),
                'similarity_score': cv_payload.get('similarity_score'),
                'cv_response': cv_payload,
            },
            status=status.HTTP_200_OK,
        )


class UserDetailsView(APIView):
    """
    Returns the current authenticated user's profile details.

    GET /api/user-details
    Authorization: Bearer <access_token>
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        try:
            student = Student.objects.get(user=user)
            return Response({
                'role': 'student',
                'id': student.student_id,
                'name': student.student_name,
                'email': student.email,
                'year': student.year,
                'dept': student.dept,
                'section': student.section,
            })
        except Student.DoesNotExist:
            pass

        try:
            teacher = Teacher.objects.get(user=user)
            return Response({
                'role': 'teacher',
                'id': teacher.teacher_id,
                'name': teacher.teacher_name,
                'email': teacher.email,
            })
        except Teacher.DoesNotExist:
            pass

        try:
            mgmt = Management.objects.get(user=user)
            return Response({
                'role': 'admin',
                'id': mgmt.Management_id,
                'name': mgmt.Management_name,
                'email': mgmt.email,
            })
        except Management.DoesNotExist:
            pass

        return Response(
            {'error': 'User profile not found'},
            status=status.HTTP_404_NOT_FOUND
        )


class UserLogoutView(APIView):
    """
    Logout endpoint.

    GET /api/user-logout
    Authorization: Bearer <access_token>

    Acknowledges logout. The client should discard stored tokens.
    For full token invalidation, include the refresh token in the request body
    and add 'rest_framework_simplejwt.token_blacklist' to INSTALLED_APPS.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({'message': 'Logged out successfully'}, status=status.HTTP_200_OK)

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except TokenError:
                return Response(
                    {'error': 'Invalid refresh token'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            except Exception:
                # Token blacklist app may not be enabled; keep logout idempotent.
                pass
        return Response({'message': 'Logged out successfully'}, status=status.HTTP_200_OK)


def _get_management_for_user(user):
    return Management.objects.filter(user=user).first()


def _get_teacher_for_user(user):
    return Teacher.objects.filter(user=user).first()


def _get_student_for_user(user):
    return Student.objects.filter(user=user).first()


def _parse_programs(programs_raw):
    return [p.strip() for p in (programs_raw or '').split(',') if p.strip()]


def _auto_assign_teacher_to_student_courses(teacher, course, section=None, year=None):
    """
    Auto-map teacher to matching student-course rows for the same management,
    course, section/year, and program.
    """
    if not teacher or not teacher.management_id or not course:
        return 0

    queryset = StudentCourse.objects.filter(
        student__management=teacher.management,
        course=course,
    )

    if section:
        queryset = queryset.filter(student__section=section)
    if year is not None:
        queryset = queryset.filter(student__year=year)

    programs = _parse_programs(teacher.programs)
    if programs:
        queryset = queryset.filter(student__dept__in=programs)

    return queryset.update(teacher=teacher)


def _count_csv_entries(value):
    return len([item.strip() for item in (value or '').split(',') if item.strip()])


# ============ CRUD ViewSets for all models ============

class StudentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Student model providing CRUD operations.
    - GET /students/ - List all students
    - POST /students/ - Create a student (use registration for new users)
    - GET /students/{id}/ - Retrieve a student
    - PUT /students/{id}/ - Update a student
    - PATCH /students/{id}/ - Partial update a student
    - DELETE /students/{id}/ - Delete a student
    - PATCH /students/{id}/update-courses/ - Replace all courses for a student
    """
    queryset = Student.objects.prefetch_related('student_courses__course', 'student_courses__teacher').all()
    serializer_class = StudentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = self.queryset.all()

        if not self.request.user.is_superuser:
            management = _get_management_for_user(self.request.user)
            if not management:
                student = _get_student_for_user(self.request.user)
                if student:
                    return queryset.filter(student_id=student.student_id)
                return queryset.none()

        # Optional filters – accept both 'dept' and 'program' (frontend uses 'program')
        year = self.request.query_params.get('year')
        dept = (
            self.request.query_params.get('dept') or
            self.request.query_params.get('program')
        )
        section = self.request.query_params.get('section')
        if year:
            queryset = queryset.filter(year=year)
        if dept:
            queryset = queryset.filter(dept=dept)
        if section:
            queryset = queryset.filter(section=section)
        return queryset

    def perform_create(self, serializer):
        management = _get_management_for_user(self.request.user)
        if not management and not self.request.user.is_superuser:
            raise DRFValidationError({'error': 'Only management users can create students'})
        if self.request.user.is_superuser and not management:
            serializer.save()
            return
        serializer.save(management=management)

    def perform_update(self, serializer):
        if self.request.user.is_superuser:
            serializer.save()
            return
        management = _get_management_for_user(self.request.user)
        if not management:
            raise DRFValidationError({'error': 'Only management users can update students'})
        serializer.save(management=management)

    @action(detail=True, methods=['patch'], url_path='update-courses')
    def update_courses(self, request, pk=None):
        """
        Replace all courses for a student.
        Accepts the same comma-separated format as signup:
          { "courses": "CS301: Database Systems, CS401: Algorithms" }
        All existing StudentCourse records for this student are removed and
        new ones are created from the provided list.
        """
        student = self.get_object()
        courses_input = request.data.get('courses', '')
        course_inputs = UnifiedSignupView._parse_courses_input(courses_input)

        if not course_inputs:
            return Response({'error': 'courses field is required'}, status=status.HTTP_400_BAD_REQUEST)

        management = student.management
        created_courses = []
        skipped_courses = []
        assignments = []

        for course_input in course_inputs:
            course = UnifiedSignupView._find_existing_course(
                course_id=course_input.get('course_id'),
                course_code=course_input.get('course_code', ''),
                course_name=course_input.get('course_name', ''),
                management=management,
            )
            if not course:
                skipped_courses.append({
                    'course_code': course_input.get('course_code', ''),
                    'course_name': course_input.get('course_name', ''),
                    'reason': 'course_not_found',
                })
                continue

            base_taught_qs = TaughtCourse.objects.filter(
                course=course,
                teacher__management=management,
            ).select_related('teacher')

            offered_years = sorted({
                y for y in base_taught_qs.values_list('year', flat=True) if y is not None
            })
            if offered_years and student.year not in offered_years:
                skipped_courses.append({
                    'course_id': course.course_id,
                    'course_code': course.course_code,
                    'course_name': course.course_name,
                    'reason': 'student_year_not_eligible_for_course',
                    'student_year': student.year,
                    'allowed_years': offered_years,
                })
                continue

            taught_qs = base_taught_qs.filter(
                section=student.section,
                year=student.year,
            )

            taught = None
            for tc in taught_qs:
                if tc.teacher and UnifiedSignupView._program_matches(tc.teacher.programs, student.dept):
                    taught = tc
                    break

            if not taught or not taught.teacher_id:
                skipped_courses.append({
                    'course_id': course.course_id,
                    'course_code': course.course_code,
                    'course_name': course.course_name,
                    'reason': 'no_teacher_mapping_for_student_section_year_program',
                })
                continue

            assignments.append((course, taught.teacher))
            created_courses.append({
                'course_id': course.course_id,
                'course_code': course.course_code,
                'course_name': course.course_name,
                'teacher_id': taught.teacher.teacher_id,
                'teacher_name': taught.teacher.teacher_name,
                'section': taught.section,
                'year': taught.year,
                'program': student.dept,
            })

        if not assignments:
            return Response({
                'error': 'No requested courses are mapped to a teacher for this student section/year/program',
                'skipped_courses': skipped_courses,
            }, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            # Replace only after validation succeeds.
            student.student_courses.all().delete()
            for course, teacher in assignments:
                StudentCourse.objects.create(
                    student=student,
                    course=course,
                    teacher=teacher,
                    classes_attended_count=0
                )

        return Response({
            'message': 'Courses updated successfully',
            'student_id': student.student_id,
            'courses': created_courses,
            'skipped_courses': skipped_courses,
        }, status=status.HTTP_200_OK)


class StudentFilterOptionsView(APIView):
    """
    Returns unique student years and departments within the current management.

    GET /api/students/filter-options/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.is_superuser:
            student_qs = Student.objects.all()
        else:
            management = _get_management_for_user(request.user)
            if not management:
                return Response(
                    {'error': 'Only management users can access student filter options'},
                    status=status.HTTP_403_FORBIDDEN
                )
            student_qs = Student.objects.filter(management=management)

        years = sorted({year for year in student_qs.values_list('year', flat=True) if year is not None})
        departments = sorted({dept for dept in student_qs.values_list('dept', flat=True) if dept})

        return Response({
            'years': years,
            'departments': departments,
            'programs': departments,
        }, status=status.HTTP_200_OK)


class TeacherFilterOptionsView(APIView):
    """
    Returns unique teacher years and programs within the current management.

    GET /api/teachers/filter-options/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.is_superuser:
            teacher_qs = Teacher.objects.all()
        else:
            management = _get_management_for_user(request.user)
            if not management:
                return Response(
                    {'error': 'Only management users can access teacher filter options'},
                    status=status.HTTP_403_FORBIDDEN
                )
            teacher_qs = Teacher.objects.filter(management=management)

        years = sorted({
            int(year)
            for raw_years in teacher_qs.values_list('years', flat=True)
            for year in UnifiedSignupView._parse_comma_list(raw_years)
            if str(year).isdigit()
        })
        programs = sorted({
            program
            for raw_programs in teacher_qs.values_list('programs', flat=True)
            for program in UnifiedSignupView._parse_comma_list(raw_programs)
            if program
        })

        return Response({
            'years': years,
            'programs': programs,
        }, status=status.HTTP_200_OK)


class TeacherViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Teacher model providing CRUD operations.
    - GET /teachers/ - List all teachers
    - POST /teachers/ - Create a teacher (use registration for new users)
    - GET /teachers/{id}/ - Retrieve a teacher
    - PUT /teachers/{id}/ - Update a teacher
    - PATCH /teachers/{id}/ - Partial update a teacher
    - DELETE /teachers/{id}/ - Delete a teacher

    Optional filter query params: ?year=X&program=Y
    """
    queryset = Teacher.objects.prefetch_related('taught_courses__course').all()
    serializer_class = TeacherSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = self.queryset.all()

        if self.request.user.is_superuser:
            management = None
        else:
            management = _get_management_for_user(self.request.user)
            if not management:
                teacher = _get_teacher_for_user(self.request.user)
                if teacher:
                    return queryset.filter(teacher_id=teacher.teacher_id)
                return queryset.none()

        # Scope to the logged-in management's teachers
        if management:
            queryset = queryset.filter(management=management)

        # Filter by year or program – stored as comma-separated strings, match whole values only
        # Accept both singular (?year=) and plural (?years=) param names
        year = (self.request.query_params.get('year') or self.request.query_params.get('years') or '').strip()
        program = (self.request.query_params.get('program') or self.request.query_params.get('programs') or '').strip()
        if year:
            queryset = queryset.filter(
                Q(years=year) |
                Q(years__startswith=f'{year},') |
                Q(years__endswith=f',{year}') |
                Q(years__icontains=f',{year},')
            )
        if program:
            queryset = queryset.filter(
                Q(programs=program) |
                Q(programs__startswith=f'{program},') |
                Q(programs__endswith=f',{program}') |
                Q(programs__icontains=f',{program},')
            )
        return queryset

    def perform_create(self, serializer):
        management = _get_management_for_user(self.request.user)
        if not management and not self.request.user.is_superuser:
            raise DRFValidationError({'error': 'Only management users can create teachers'})
        if self.request.user.is_superuser and not management:
            serializer.save()
            return
        serializer.save(management=management)

    def perform_update(self, serializer):
        if self.request.user.is_superuser:
            serializer.save()
            return
        management = _get_management_for_user(self.request.user)
        if not management:
            raise DRFValidationError({'error': 'Only management users can update teachers'})
        serializer.save(management=management)

    def _sync_teacher_courses_payload(self, teacher, payload):
        management = teacher.management

        courses_raw = payload.get('courses', None)
        course_inputs = UnifiedSignupView._parse_courses_input(courses_raw)
        if not course_inputs:
            raise DRFValidationError({'error': 'courses field is required'})

        global_sections = UnifiedSignupView._parse_comma_list(
            (payload.get('sections', '') or '').strip() or (payload.get('section', '') or '').strip()
        )
        if not global_sections:
            global_sections = ['A']

        global_years = []
        raw_years = UnifiedSignupView._parse_comma_list(
            (payload.get('years', '') or '').strip() or (payload.get('year', '') or '').strip()
        )
        for y in raw_years:
            try:
                global_years.append(int(y))
            except (ValueError, TypeError):
                continue

        if not global_years:
            for y in UnifiedSignupView._parse_comma_list(teacher.years):
                try:
                    global_years.append(int(y))
                except (ValueError, TypeError):
                    continue

        desired_entries = []
        for course_input in course_inputs:
            input_code = (course_input.get('course_code') or '').strip()
            input_name = (course_input.get('course_name') or '').strip()

            course = UnifiedSignupView._find_existing_course(
                course_id=course_input.get('course_id'),
                course_code=input_code,
                course_name=input_name,
                management=management,
            )

            if not course:
                if not input_code and not input_name:
                    raise DRFValidationError({'error': 'Each course must provide course_id or course_code/course_name'})
                course = Course.objects.create(
                    course_code=input_code,
                    course_name=input_name or input_code,
                )
            else:
                # Align with registration behavior: backfill blank code/name when payload provides values.
                update_fields = []
                if input_code and not (course.course_code or '').strip():
                    course.course_code = input_code
                    update_fields.append('course_code')
                if input_name and not (course.course_name or '').strip():
                    course.course_name = input_name
                    update_fields.append('course_name')
                if update_fields:
                    course.save(update_fields=update_fields)

            per_sections = [course_input.get('section')] if course_input.get('section') else global_sections

            per_years = []
            try:
                if course_input.get('year') is not None and str(course_input.get('year')).strip() != '':
                    per_years = [int(course_input.get('year'))]
            except (ValueError, TypeError):
                per_years = []
            if not per_years:
                per_years = global_years
            if not per_years:
                per_years = [None]

            for section in per_sections:
                for year in per_years:
                    desired_entries.append((course, section, year))

        desired_keys = {(c.course_id, s, y) for c, s, y in desired_entries}

        existing_qs = teacher.taught_courses.select_related('course').all()
        existing_map = {(tc.course_id, tc.section, tc.year): tc for tc in existing_qs}

        added = []
        kept = []
        removed = []

        with transaction.atomic():
            # Remove mappings not listed in payload.
            for key, tc in existing_map.items():
                if key not in desired_keys:
                    removed.append({
                        'id': tc.id,
                        'course_id': tc.course_id,
                        'course_code': tc.course.course_code,
                        'course_name': tc.course.course_name,
                        'section': tc.section,
                        'year': tc.year,
                    })
                    tc.delete()

                    # If no teacher remains for this course in this management, clear teacher
                    # assignments from student-course rows but keep student-course records.
                    if not TaughtCourse.objects.filter(
                        course_id=tc.course_id,
                        teacher__management=management,
                    ).exists():
                        StudentCourse.objects.filter(
                            student__management=management,
                            course_id=tc.course_id,
                        ).update(teacher=None)

            # Add missing mappings and keep existing ones.
            for course, section, year in desired_entries:
                key = (course.course_id, section, year)
                if key in existing_map:
                    tc = existing_map[key]
                    kept.append({
                        'id': tc.id,
                        'course_id': course.course_id,
                        'course_code': course.course_code,
                        'course_name': course.course_name,
                        'section': section,
                        'year': year,
                    })
                else:
                    tc, _ = TaughtCourse.objects.get_or_create(
                        teacher=teacher,
                        course=course,
                        section=section,
                        year=year,
                        defaults={'classes_taken_count': 0}
                    )
                    added.append({
                        'id': tc.id,
                        'course_id': course.course_id,
                        'course_code': course.course_code,
                        'course_name': course.course_name,
                        'section': section,
                        'year': year,
                    })

                _auto_assign_teacher_to_student_courses(
                    teacher=teacher,
                    course=course,
                    section=section,
                    year=year,
                )

        return {
            'added': added,
            'kept': kept,
            'removed': removed,
        }

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        response_data = self.get_serializer(serializer.instance).data
        if 'courses' in request.data:
            sync_result = self._sync_teacher_courses_payload(serializer.instance, request.data)
            serializer.instance.refresh_from_db()
            response_data = self.get_serializer(serializer.instance).data
            response_data['courses_sync'] = sync_result

        return Response(response_data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['patch'], url_path='sync-courses')
    def sync_courses(self, request, pk=None):
        """
        Replace teacher taught-course mappings by request body:
        - keep mappings present in payload
        - add missing mappings from payload
        - remove mappings not present in payload
        """
        teacher = self.get_object()
        sync_result = self._sync_teacher_courses_payload(teacher, request.data)

        return Response({
            'message': 'Teacher courses synchronized successfully',
            'teacher_id': teacher.teacher_id,
            'added': sync_result['added'],
            'kept': sync_result['kept'],
            'removed': sync_result['removed'],
        }, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        teacher = self.get_object()
        management = teacher.management
        course_ids = list(teacher.taught_courses.values_list('course_id', flat=True).distinct())

        with transaction.atomic():
            response = super().destroy(request, *args, **kwargs)

            # If no teacher remains for a course inside this management,
            # keep student-course records but clear teacher assignment.
            for course_id in course_ids:
                other_exists = TaughtCourse.objects.filter(
                    course_id=course_id,
                    teacher__management=management,
                ).exists()
                if not other_exists:
                    StudentCourse.objects.filter(
                        student__management=management,
                        course_id=course_id,
                    ).update(teacher=None)

        return response


class ManagementViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Management model providing CRUD operations.
    - GET /management/ - List all management users
    - POST /management/ - Create a management user (use registration for new users)
    - GET /management/{id}/ - Retrieve a management user
    - PUT /management/{id}/ - Update a management user
    - PATCH /management/{id}/ - Partial update a management user
    - DELETE /management/{id}/ - Delete a management user
    """
    queryset = Management.objects.all()
    serializer_class = ManagementSerializer
    permission_classes = [IsAuthenticated]


class CourseViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Course model providing CRUD operations.
    - GET /courses/ - List all courses
    - POST /courses/ - Create a course
    - GET /courses/{id}/ - Retrieve a course
    - PUT /courses/{id}/ - Update a course
    - PATCH /courses/{id}/ - Partial update a course
    - DELETE /courses/{id}/ - Delete a course
    """
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = self.queryset.all()
        if self.request.user.is_superuser:
            return queryset

        management = _get_management_for_user(self.request.user)
        if not management:
            return queryset.none()

        return queryset.filter(
            Q(taught_courses__teacher__management=management) |
            Q(student_courses__student__management=management)
        ).distinct()


class ClassViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Class (Classroom) model providing CRUD operations.
    - GET /classes/ - List all classes
    - POST /classes/ - Create a class
    - GET /classes/{id}/ - Retrieve a class
    - PUT /classes/{id}/ - Update a class
    - PATCH /classes/{id}/ - Partial update a class
    - DELETE /classes/{id}/ - Delete a class
    """
    queryset = Class.objects.all()
    serializer_class = ClassSerializer
    permission_classes = [IsAuthenticated]


class TaughtCourseViewSet(viewsets.ModelViewSet):
    """
    ViewSet for TaughtCourse model providing CRUD operations.
    - GET /taught-courses/ - List all taught courses
    - POST /taught-courses/ - Create a taught course
    - GET /taught-courses/{id}/ - Retrieve a taught course
    - PUT /taught-courses/{id}/ - Update a taught course
    - PATCH /taught-courses/{id}/ - Partial update a taught course
    - DELETE /taught-courses/{id}/ - Delete a taught course
    """
    queryset = TaughtCourse.objects.all()
    serializer_class = TaughtCourseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = self.queryset.all()

        if not self.request.user.is_superuser:
            management = _get_management_for_user(self.request.user)
            if not management:
                return queryset.none()
            queryset = queryset.filter(teacher__management=management)

        # Optional filters
        course_id = self.request.query_params.get('course')
        teacher_id = self.request.query_params.get('teacher')
        if course_id:
            queryset = queryset.filter(course_id=course_id)
        if teacher_id:
            queryset = queryset.filter(teacher_id=teacher_id)
        return queryset

    def perform_create(self, serializer):
        if self.request.user.is_superuser:
            taught = serializer.save()
            _auto_assign_teacher_to_student_courses(
                teacher=taught.teacher,
                course=taught.course,
                section=taught.section,
                year=taught.year,
            )
            return
        management = _get_management_for_user(self.request.user)
        if not management:
            raise DRFValidationError({'error': 'Only management users can create taught courses'})
        teacher = serializer.validated_data.get('teacher')
        if not teacher or teacher.management_id != management.Management_id:
            raise DRFValidationError({'error': 'Teacher does not belong to your management'})
        taught = serializer.save()
        _auto_assign_teacher_to_student_courses(
            teacher=taught.teacher,
            course=taught.course,
            section=taught.section,
            year=taught.year,
        )

    def perform_update(self, serializer):
        if self.request.user.is_superuser:
            taught = serializer.save()
            _auto_assign_teacher_to_student_courses(
                teacher=taught.teacher,
                course=taught.course,
                section=taught.section,
                year=taught.year,
            )
            return
        management = _get_management_for_user(self.request.user)
        if not management:
            raise DRFValidationError({'error': 'Only management users can update taught courses'})
        teacher = serializer.validated_data.get('teacher', serializer.instance.teacher)
        if not teacher or teacher.management_id != management.Management_id:
            raise DRFValidationError({'error': 'Teacher does not belong to your management'})
        taught = serializer.save()
        _auto_assign_teacher_to_student_courses(
            teacher=taught.teacher,
            course=taught.course,
            section=taught.section,
            year=taught.year,
        )


class StudentCourseViewSet(viewsets.ModelViewSet):
    """
    ViewSet for StudentCourse model providing CRUD operations.
    - GET /student-courses/ - List all student courses
    - POST /student-courses/ - Create a student course
    - GET /student-courses/{id}/ - Retrieve a student course
    - PUT /student-courses/{id}/ - Update a student course
    - PATCH /student-courses/{id}/ - Partial update a student course
    - DELETE /student-courses/{id}/ - Delete a student course
    """
    queryset = StudentCourse.objects.all()
    serializer_class = StudentCourseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = self.queryset.all()

        if not self.request.user.is_superuser:
            management = _get_management_for_user(self.request.user)
            if not management:
                return queryset.none()
            queryset = queryset.filter(student__management=management)

        # Optional filters
        student_id = self.request.query_params.get('student')
        course_id = self.request.query_params.get('course')
        teacher_id = self.request.query_params.get('teacher')
        if student_id:
            queryset = queryset.filter(student_id=student_id)
        if course_id:
            queryset = queryset.filter(course_id=course_id)
        if teacher_id:
            queryset = queryset.filter(teacher_id=teacher_id)
        return queryset

    def perform_create(self, serializer):
        if self.request.user.is_superuser:
            serializer.save()
            return
        management = _get_management_for_user(self.request.user)
        if not management:
            raise DRFValidationError({'error': 'Only management users can create student-course mappings'})

        student = serializer.validated_data.get('student')
        teacher = serializer.validated_data.get('teacher')
        if not student or student.management_id != management.Management_id:
            raise DRFValidationError({'error': 'Student does not belong to your management'})
        if teacher and teacher.management_id != management.Management_id:
            raise DRFValidationError({'error': 'Teacher does not belong to your management'})
        serializer.save()

    def perform_update(self, serializer):
        if self.request.user.is_superuser:
            serializer.save()
            return
        management = _get_management_for_user(self.request.user)
        if not management:
            raise DRFValidationError({'error': 'Only management users can update student-course mappings'})

        student = serializer.validated_data.get('student', serializer.instance.student)
        teacher = serializer.validated_data.get('teacher', serializer.instance.teacher)
        if not student or student.management_id != management.Management_id:
            raise DRFValidationError({'error': 'Student does not belong to your management'})
        if teacher and teacher.management_id != management.Management_id:
            raise DRFValidationError({'error': 'Teacher does not belong to your management'})
        serializer.save()


class UpdateAttendanceRequestViewSet(viewsets.ModelViewSet):
    """
    ViewSet for UpdateAttendanceRequest model providing CRUD operations.
    - GET /update-attendance-requests/ - List all update attendance requests
    - POST /update-attendance-requests/ - Create an update attendance request (by teacher)
    - GET /update-attendance-requests/{id}/ - Retrieve an update attendance request
    - PUT /update-attendance-requests/{id}/ - Update an update attendance request
    - PATCH /update-attendance-requests/{id}/ - Partial update an update attendance request
    - DELETE /update-attendance-requests/{id}/ - Delete an update attendance request
    - POST /update-attendance-requests/{id}/approve/ - Approve the request (by management)
    - POST /update-attendance-requests/{id}/reject/ - Reject the request (by management)
    """
    queryset = UpdateAttendanceRequest.objects.all()
    serializer_class = UpdateAttendanceRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = self.queryset
        user = self.request.user
        requested_management_id = self.request.query_params.get('management_id') or self.request.query_params.get('management')

        # Restrict visibility to management-owned requests only.
        if user.is_superuser:
            if requested_management_id:
                queryset = queryset.filter(management_id=requested_management_id)
        else:
            management = Management.objects.filter(user=user).first()
            if management:
                # A management user can only query their own management_id.
                if requested_management_id and str(management.Management_id) != str(requested_management_id):
                    queryset = queryset.none()
                else:
                    queryset = queryset.filter(management=management)
            else:
                queryset = queryset.none()

        # Optional filters
        teacher_roll_no = self.request.query_params.get('teacher_rollNo') or self.request.query_params.get('teacher')
        student_roll_no = self.request.query_params.get('student_rollNo') or self.request.query_params.get('student')
        course_id = self.request.query_params.get('course')
        request_status = self.request.query_params.get('status')
        if teacher_roll_no:
            queryset = queryset.filter(teacher__teacher_rollNo=teacher_roll_no)
        if student_roll_no:
            queryset = queryset.filter(student__student_rollNo=student_roll_no)
        if course_id:
            queryset = queryset.filter(course_id=course_id)
        if request_status:
            queryset = queryset.filter(status=request_status)
        return queryset

    def perform_create(self, serializer):
        """Auto-set teacher and management on create"""
        teacher = serializer.validated_data.get('teacher')
        
        if not self.request.user.is_superuser:
            current_management = _get_management_for_user(self.request.user)
            current_teacher = _get_teacher_for_user(self.request.user)
            
            # User must be either management or teacher
            if not current_management and not current_teacher:
                raise DRFValidationError({'error': 'Only management or teacher users can create attendance requests'})
            
            # If teacher user: always set teacher to current user, no inference needed
            if current_teacher:
                if teacher and teacher.teacher_id != current_teacher.teacher_id:
                    raise DRFValidationError({'error': 'You can only create requests as yourself, not as another teacher'})
                teacher = current_teacher
                management = teacher.management
            
            # If management user: infer teacher from flexible mode if needed
            elif current_management:
                # Try to infer teacher from course_code + section if not provided
                if not teacher and 'course' in serializer.validated_data:
                    course_code = self.request.data.get('course_code')
                    section = self.request.data.get('section')
                    
                    if course_code and section:
                        course = serializer.validated_data.get('course')
                        taught_course = TaughtCourse.objects.filter(
                            course=course,
                            section=section
                        ).first()
                        if taught_course:
                            teacher = taught_course.teacher
                
                if not teacher:
                    raise DRFValidationError({'error': 'teacher_rollNo is required for management users'})
                management = teacher.management
                if management.Management_id != current_management.Management_id:
                    raise DRFValidationError({'error': 'Teacher does not belong to your management'})
        else:
            # Superuser: no permission checks
            management = teacher.management if teacher else None
        
        # Pass both teacher and management to save
        serializer.save(teacher=teacher, management=management)

    def _process_request(self, request, pk, approve):
        """Helper method to approve or reject a request"""
        from django.utils import timezone
        from django.http import Http404

        # Ensure non-management users get an explicit authorization error.
        try:
            management = Management.objects.get(user=request.user)
        except Management.DoesNotExist:
            return Response(
                {'error': 'Only management users can process attendance requests'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            attendance_request = self.get_object()
        except Http404:
            return Response(
                {'error': 'Update attendance request not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        if attendance_request.status != 'pending':
            return Response(
                {'error': f'Request has already been {attendance_request.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if approve:
            # Approve: Update the student's attendance in the StudentCourse
            added_count = len([c.strip() for c in (attendance_request.classes_to_add or '').split(',') if c.strip()])
            request_id = attendance_request.id
            
            try:
                student_course = StudentCourse.objects.get(
                    student=attendance_request.student,
                    course=attendance_request.course,
                    teacher=attendance_request.teacher
                )
                
                # Get the TaughtCourse to check total classes taken
                taught_course = TaughtCourse.objects.filter(
                    teacher=attendance_request.teacher,
                    course=attendance_request.course
                ).first()
                
                total_classes_taken = taught_course.classes_taken_count if taught_course else 0
                new_attended_count = (student_course.classes_attended_count or 0) + added_count
                
                # Validate: attended count should not exceed total classes taken
                if new_attended_count > total_classes_taken:
                    # Delete the request and return error
                    attendance_request.delete()
                    return Response(
                        {
                            'error': f'Cannot approve: Adding {added_count} classes would result in {new_attended_count} classes attended, '
                                   f'but only {total_classes_taken} total classes were taken by this teacher in this course',
                            'current_attended': student_course.classes_attended_count,
                            'attempting_to_add': added_count,
                            'total_classes': total_classes_taken,
                            'request_id': request_id
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                student_course.classes_attended_count = new_attended_count
                student_course.save(update_fields=['classes_attended_count'])
            except StudentCourse.DoesNotExist:
                # Create new StudentCourse record if it doesn't exist
                taught_course = TaughtCourse.objects.filter(
                    teacher=attendance_request.teacher,
                    course=attendance_request.course
                ).first()
                
                total_classes_taken = taught_course.classes_taken_count if taught_course else 0
                
                # Validate: attended count should not exceed total classes taken
                if added_count > total_classes_taken:
                    # Delete the request and return error
                    attendance_request.delete()
                    return Response(
                        {
                            'error': f'Cannot approve: Adding {added_count} classes exceeds total {total_classes_taken} classes '
                                   f'taken by this teacher in this course',
                            'total_classes': total_classes_taken,
                            'attempting_to_add': added_count,
                            'request_id': request_id
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                StudentCourse.objects.create(
                    student=attendance_request.student,
                    course=attendance_request.course,
                    teacher=attendance_request.teacher,
                    classes_attended_count=added_count,
                )
            
            attendance_request.status = 'approved'
            message = 'Attendance request approved and attendance updated'
        else:
            attendance_request.status = 'rejected'
            message = 'Attendance request rejected'
            request_id = attendance_request.id

        attendance_request.processed_at = timezone.now()
        attendance_request.processed_by = management
        attendance_request.save()

        # Delete the request after processing (both approval and rejection)
        attendance_request.delete()
        
        return Response({
            'message': message,
            'request_id': request_id
        }, status=status.HTTP_200_OK)

    def approve(self, request, pk=None):
        """Approve the attendance update request"""
        return self._process_request(request, pk, approve=True)

    def reject(self, request, pk=None):
        """Reject the attendance update request"""
        return self._process_request(request, pk, approve=False)


class AttendanceSessionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for AttendanceSession model providing CRUD operations and session management.
    - GET /attendance-sessions/ - List all attendance sessions
    - POST /attendance-sessions/ - Create/start an attendance session
    - GET /attendance-sessions/{id}/ - Retrieve an attendance session
    - PUT /attendance-sessions/{id}/ - Update an attendance session
    - PATCH /attendance-sessions/{id}/ - Partial update an attendance session
    - DELETE /attendance-sessions/{id}/ - Delete an attendance session
    - POST /attendance-sessions/{id}/stop/ - Stop an active session
    - GET /attendance-sessions/{id}/qr/ - Get QR code for the session
    - GET /attendance-sessions/{id}/attendance/ - Get attendance records for the session
    """
    queryset = AttendanceSession.objects.all()
    serializer_class = AttendanceSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = self.queryset.all()

        if not self.request.user.is_superuser:
            management = _get_management_for_user(self.request.user)
            teacher_user = _get_teacher_for_user(self.request.user)
            if management:
                queryset = queryset.filter(teacher__management=management)
            elif teacher_user:
                queryset = queryset.filter(teacher=teacher_user)
            else:
                return queryset.none()

        # Optional filters
        teacher_id = self.request.query_params.get('teacher')
        course_id = self.request.query_params.get('course')
        session_status = self.request.query_params.get('status')
        section = self.request.query_params.get('section')
        year = self.request.query_params.get('year')
        
        if teacher_id:
            queryset = queryset.filter(teacher_id=teacher_id)
        if course_id:
            queryset = queryset.filter(course_id=course_id)
        if session_status:
            queryset = queryset.filter(status=session_status)
        if section:
            queryset = queryset.filter(section=section)
        if year:
            queryset = queryset.filter(year=year)
        
        return queryset

    def create(self, request, *args, **kwargs):
        """Start a new attendance session"""
        # Generate a unique QR code token
        qr_token = secrets.token_urlsafe(32)
        
        # Create the session without the token first
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            teacher = serializer.validated_data.get('teacher')

            if not request.user.is_superuser:
                management = _get_management_for_user(request.user)
                teacher_user = _get_teacher_for_user(request.user)

                if management:
                    if not teacher or teacher.management_id != management.Management_id:
                        return Response({'error': 'Teacher does not belong to your management'}, status=status.HTTP_403_FORBIDDEN)
                elif teacher_user:
                    if not teacher or teacher.teacher_id != teacher_user.teacher_id:
                        return Response({'error': 'Teachers can only start their own sessions'}, status=status.HTTP_403_FORBIDDEN)
                else:
                    return Response({'error': 'Only management/teacher can create attendance sessions'}, status=status.HTTP_403_FORBIDDEN)

            # Save the session and set the token
            session = serializer.save(qr_code_token=qr_token, status='active')

            slot_count = max(1, int(session.slot_count or 1))
            taught_courses = TaughtCourse.objects.filter(
                teacher=session.teacher,
                course=session.course,
                section=session.section,
                year=session.year,
            )
            for taught_course in taught_courses:
                taught_course.classes_taken_count = (taught_course.classes_taken_count or 0) + slot_count
                taught_course.save(update_fields=['classes_taken_count'])
            
            # Return the updated serializer data
            response_serializer = self.get_serializer(session)
            return Response({
                'message': 'Attendance session started successfully',
                'session': response_serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def _mark_absent_students_for_session(self, session):
        """Increment absent counts for enrolled students who did not mark present."""
        present_student_ids = set(
            AttendanceRecord.objects.filter(session=session, is_present=True)
            .values_list('student_id', flat=True)
        )

        student_courses = StudentCourse.objects.filter(course=session.course, teacher=session.teacher)
        if session.teacher.management_id:
            student_courses = student_courses.filter(student__management=session.teacher.management)

        absent_student_courses = [
            student_course
            for student_course in student_courses.select_related('student')
            if student_course.student_id not in present_student_ids
        ]

        if not absent_student_courses:
            return

        slot_count = max(1, int(getattr(session, 'slot_count', 1) or 1))
        for student_course in absent_student_courses:
            student_course.classes_absent_count = (student_course.classes_absent_count or 0) + slot_count

        StudentCourse.objects.bulk_update(absent_student_courses, ['classes_absent_count'])

    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        """Stop an active attendance session"""
        try:
            session = self.get_object()
        except AttendanceSession.DoesNotExist:
            return Response(
                {'error': 'Attendance session not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        if session.status != 'active':
            return Response(
                {'error': 'Session is already stopped'},
                status=status.HTTP_400_BAD_REQUEST
            )

        session.status = 'stopped'
        session.stopped_at = timezone.now()
        session.save()
        self._mark_absent_students_for_session(session)

        serializer = self.get_serializer(session)
        return Response({
            'message': 'Attendance session stopped successfully',
            'session': serializer.data
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def qr(self, request, pk=None):
        """Generate and return QR code for the session"""
        try:
            session = self.get_object()
        except AttendanceSession.DoesNotExist:
            return Response(
                {'error': 'Attendance session not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        if session.status != 'active':
            return Response(
                {'error': 'Session is not active'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(session.qr_code_token)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return Response({
            'qr_code': f'data:image/png;base64,{img_base64}',
            'qr_token': session.qr_code_token,
            'session_id': session.id
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def attendance(self, request, pk=None):
        """Get attendance records for the session"""
        try:
            session = self.get_object()
        except AttendanceSession.DoesNotExist:
            return Response(
                {'error': 'Attendance session not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        records = AttendanceRecord.objects.filter(session=session)
        serializer = AttendanceRecordSerializer(records, many=True)
        
        # Calculate statistics
        total_students = records.count()
        present_students = records.filter(is_present=True).count()
        rfid_only = records.filter(rfid_scanned=True, qr_scanned=False).count()
        qr_only = records.filter(rfid_scanned=False, qr_scanned=True).count()
        
        return Response({
            'records': serializer.data,
            'statistics': {
                'total_students': total_students,
                'present': present_students,
                'absent': total_students - present_students,
                'rfid_only': rfid_only,
                'qr_only': qr_only
            }
        }, status=status.HTTP_200_OK)


class AttendanceRecordViewSet(viewsets.ModelViewSet):
    """
    ViewSet for AttendanceRecord model providing CRUD operations.
    - GET /attendance-records/ - List all attendance records
    - GET /attendance-records/{id}/ - Retrieve an attendance record
    """
    queryset = AttendanceRecord.objects.all()
    serializer_class = AttendanceRecordSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = self.queryset.all()

        if not self.request.user.is_superuser:
            management = _get_management_for_user(self.request.user)
            teacher_user = _get_teacher_for_user(self.request.user)
            student_user = _get_student_for_user(self.request.user)

            if management:
                queryset = queryset.filter(session__teacher__management=management)
            elif teacher_user:
                queryset = queryset.filter(session__teacher=teacher_user)
            elif student_user:
                queryset = queryset.filter(student=student_user)
            else:
                return queryset.none()

        # Optional filters
        session_id = self.request.query_params.get('session')
        student_id = self.request.query_params.get('student')
        is_present = self.request.query_params.get('is_present')
        
        if session_id:
            queryset = queryset.filter(session_id=session_id)
        if student_id:
            queryset = queryset.filter(student_id=student_id)
        if is_present is not None:
            queryset = queryset.filter(is_present=is_present.lower() == 'true')
        
        return queryset


class RFIDScanView(APIView):
    """
    API endpoint for RFID scanning
    POST /attendance/rfid-scan/
    """
    permission_classes = [AllowAny]  # Allow hardware to scan without auth

    def _mark_attendance_if_complete(self, record, session):
        """
        Helper method to mark attendance and update StudentCourse if both scans are complete.
        """
        require_rfid = getattr(settings, 'ATTENDANCE_REQUIRE_RFID', True)
        scans_complete = (
            record.rfid_scanned and record.qr_scanned
            if require_rfid
            else (record.rfid_scanned or record.qr_scanned)
        )
        if scans_complete and not record.is_present:
            record.is_present = True
            record.marked_present_at = timezone.now()
            
            # Update StudentCourse attendance
            student_course, _ = StudentCourse.objects.get_or_create(
                student=record.student,
                course=session.course,
                teacher=session.teacher,
                defaults={'classes_attended_count': 0}
            )
            
            slot_count = max(1, int(getattr(session, 'slot_count', 1) or 1))
            student_course.classes_attended_count = (student_course.classes_attended_count or 0) + slot_count
            if student_course.teacher_id is None:
                student_course.teacher = session.teacher
                student_course.save(update_fields=['teacher', 'classes_attended_count'])
            else:
                student_course.save(update_fields=['classes_attended_count'])

    def post(self, request):
        serializer = RFIDScanSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        rfid = serializer.validated_data['rfid']
        session_id = serializer.validated_data['session_id']

        # Get student by roll number encoded on the RFID card
        try:
            student = Student.objects.get(student_rollNo=rfid)
        except Student.DoesNotExist:
            return Response(
                {'error': 'Student not found with this roll number'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get session
        try:
            session = AttendanceSession.objects.get(id=session_id)
        except AttendanceSession.DoesNotExist:
            return Response(
                {'error': 'Attendance session not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check if session is active
        if session.status != 'active':
            return Response(
                {'error': 'Attendance session is not active'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if student is enrolled in this course/section/year
        if student.section != session.section or student.year != session.year:
            return Response(
                {'error': 'Student is not enrolled in this section/year'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if student.management_id != session.teacher.management_id:
            return Response(
                {'error': 'Student does not belong to this management'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get or create attendance record
        record, created = AttendanceRecord.objects.get_or_create(
            session=session,
            student=student
        )

        # Update RFID scan
        record.rfid_scanned = True
        record.rfid_scanned_at = timezone.now()

        # Check if both RFID and QR are scanned
        self._mark_attendance_if_complete(record, session)

        record.save()

        return Response({
            'message': 'RFID scanned successfully',
            'student': student.student_name,
            'rfid_scanned': True,
            'qr_scanned': record.qr_scanned,
            'is_present': record.is_present,
            'needs_qr': getattr(settings, 'ATTENDANCE_REQUIRE_RFID', True) and not record.qr_scanned
        }, status=status.HTTP_200_OK)


class QRScanView(APIView):
    """
    API endpoint for QR code scanning
    POST /attendance/qr-scan/
    """
    permission_classes = [IsAuthenticated]

    def _mark_attendance_if_complete(self, record, session):
        """
        Helper method to mark attendance and update StudentCourse if both scans are complete.
        """
        require_rfid = getattr(settings, 'ATTENDANCE_REQUIRE_RFID', True)
        scans_complete = (
            record.rfid_scanned and record.qr_scanned
            if require_rfid
            else (record.rfid_scanned or record.qr_scanned)
        )
        if scans_complete and not record.is_present:
            record.is_present = True
            record.marked_present_at = timezone.now()
            
            # Update StudentCourse attendance
            student_course, _ = StudentCourse.objects.get_or_create(
                student=record.student,
                course=session.course,
                teacher=session.teacher,
                defaults={'classes_attended_count': 0}
            )
            
            slot_count = max(1, int(getattr(session, 'slot_count', 1) or 1))
            student_course.classes_attended_count = (student_course.classes_attended_count or 0) + slot_count
            if student_course.teacher_id is None:
                student_course.teacher = session.teacher
                student_course.save(update_fields=['teacher', 'classes_attended_count'])
            else:
                student_course.save(update_fields=['classes_attended_count'])

    def post(self, request):
        serializer = QRScanSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        qr_token = serializer.validated_data['qr_token']
        student_id = serializer.validated_data['student_id']

        # Get student
        try:
            student = Student.objects.get(student_id=student_id)
        except Student.DoesNotExist:
            return Response(
                {'error': 'Student not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get session by QR token
        try:
            session = AttendanceSession.objects.get(qr_code_token=qr_token)
        except AttendanceSession.DoesNotExist:
            return Response(
                {'error': 'Invalid QR code or session not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check if session is active
        if session.status != 'active':
            return Response(
                {'error': 'Attendance session is not active'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if student is enrolled in this course/section/year
        if student.section != session.section or student.year != session.year:
            return Response(
                {'error': 'Student is not enrolled in this section/year'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if student.management_id != session.teacher.management_id:
            return Response(
                {'error': 'Student does not belong to this management'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get or create attendance record
        record, created = AttendanceRecord.objects.get_or_create(
            session=session,
            student=student
        )

        # Update QR scan
        record.qr_scanned = True
        record.qr_scanned_at = timezone.now()

        # Check if both RFID and QR are scanned
        self._mark_attendance_if_complete(record, session)

        record.save()

        return Response({
            'message': 'QR code scanned successfully',
            'student': student.student_name,
            'rfid_scanned': record.rfid_scanned,
            'qr_scanned': True,
            'is_present': record.is_present,
            'needs_rfid': getattr(settings, 'ATTENDANCE_REQUIRE_RFID', True) and not record.rfid_scanned
        }, status=status.HTTP_200_OK)


# ============ Registration Views ============


class StudentRegistrationView(generics.CreateAPIView):
    """
    API endpoint for student registration
    """
    serializer_class = StudentRegistrationSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        management = Management.objects.filter(user=request.user).first()
        if not management:
            return Response(
                {'error': 'Only management users can register students.'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            student = serializer.save()
            if student.management_id is None:
                student.management = management
                student.save(update_fields=['management'])
            return Response({
                'message': 'Student registered successfully',
                'student_id': student.student_id,
                'email': student.email,
                'student_name': student.student_name
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TeacherRegistrationView(generics.CreateAPIView):
    """
    API endpoint for teacher registration
    """
    serializer_class = TeacherRegistrationSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        management = Management.objects.filter(user=request.user).first()
        if not management:
            return Response(
                {'error': 'Only management users can register teachers.'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            teacher = serializer.save()
            if teacher.management_id is None:
                teacher.management = management
                teacher.save(update_fields=['management'])
            return Response({
                'message': 'Teacher registered successfully',
                'teacher_id': teacher.teacher_id,
                'email': teacher.email,
                'teacher_name': teacher.teacher_name
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ManagementRegistrationView(generics.CreateAPIView):
    """
    API endpoint for management registration
    """
    serializer_class = ManagementRegistrationSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            management = serializer.save()
            return Response({
                'message': 'Management registered successfully',
                'management_id': management.Management_id,
                'email': management.email,
                'management_name': management.Management_name
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StudentLoginView(APIView):
    """
    API endpoint for student login
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']
            
            # Authenticate user
            user = authenticate(username=email, password=password)
            
            if user is not None:
                # Check if user has a student profile
                try:
                    student = Student.objects.get(user=user)
                    # Generate JWT tokens
                    refresh = RefreshToken.for_user(user)
                    return Response({
                        'message': 'Login successful',
                        'refresh': str(refresh),
                        'access': str(refresh.access_token),
                        'user_type': 'student',
                        'student_id': student.student_id,
                        'student_name': student.student_name,
                        'email': student.email
                    }, status=status.HTTP_200_OK)
                except Student.DoesNotExist:
                    return Response({
                        'error': 'Student profile not found for this user'
                    }, status=status.HTTP_404_NOT_FOUND)
            else:
                return Response({
                    'error': 'Invalid email or password'
                }, status=status.HTTP_401_UNAUTHORIZED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TeacherLoginView(APIView):
    """
    API endpoint for teacher login
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']
            
            # Authenticate user
            user = authenticate(username=email, password=password)
            
            if user is not None:
                # Check if user has a teacher profile
                try:
                    teacher = Teacher.objects.get(user=user)
                    # Generate JWT tokens
                    refresh = RefreshToken.for_user(user)
                    return Response({
                        'message': 'Login successful',
                        'refresh': str(refresh),
                        'access': str(refresh.access_token),
                        'user_type': 'teacher',
                        'teacher_id': teacher.teacher_id,
                        'teacher_name': teacher.teacher_name,
                        'email': teacher.email
                    }, status=status.HTTP_200_OK)
                except Teacher.DoesNotExist:
                    return Response({
                        'error': 'Teacher profile not found for this user'
                    }, status=status.HTTP_404_NOT_FOUND)
            else:
                return Response({
                    'error': 'Invalid email or password'
                }, status=status.HTTP_401_UNAUTHORIZED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ManagementLoginView(APIView):
    """
    API endpoint for management login
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']
            
            # Authenticate user
            user = authenticate(username=email, password=password)
            
            if user is not None:
                # Check if user has a management profile
                try:
                    management = Management.objects.get(user=user)
                    # Generate JWT tokens
                    refresh = RefreshToken.for_user(user)
                    return Response({
                        'message': 'Login successful',
                        'refresh': str(refresh),
                        'access': str(refresh.access_token),
                        'user_type': 'management',
                        'management_id': management.Management_id,
                        'management_name': management.Management_name,
                        'email': management.email
                    }, status=status.HTTP_200_OK)
                except Management.DoesNotExist:
                    return Response({
                        'error': 'Management profile not found for this user'
                    }, status=status.HTTP_404_NOT_FOUND)
            else:
                return Response({
                    'error': 'Invalid email or password'
                }, status=status.HTTP_401_UNAUTHORIZED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ============ Admin Dashboard Attendance Summary Views ============

class StudentAttendanceSummaryView(APIView):
    """
    Returns attendance summary for one or more students across all enrolled courses.

    GET /api/attendance/student/?student_rollNo=<roll_no>
         /api/attendance/student/?student_id=<pk>
         /api/attendance/student/?program=<dept>&year=<year>
         /api/attendance/student/?student_rollNo=<roll_no>&program=<dept>&year=<year>

    Used by the admin dashboard → View Attendance → Individual Student Search tab.
    """
    permission_classes = [IsAuthenticated]

    def _build_student_summary(self, student):
        student_courses = StudentCourse.objects.filter(student=student).select_related('course', 'teacher')
        courses_data = []

        for sc in student_courses:
            attended = sc.classes_attended_count or 0

            session_qs = AttendanceSession.objects.filter(
                course=sc.course,
                section=student.section,
                year=student.year,
            )
            if sc.teacher_id:
                session_qs = session_qs.filter(teacher=sc.teacher)
            elif student.management_id:
                session_qs = session_qs.filter(teacher__management=student.management)

            # classes_attended_count stores slots, so total must also be slots.
            total_sessions = session_qs.aggregate(total=Sum('slot_count')).get('total') or 0
            percent = _attendance_percent(attended, total_sessions)

            courses_data.append({
                'course_id': sc.course.course_id,
                'course_code': sc.course.course_code,
                'course_name': sc.course.course_name,
                'teacher_name': sc.teacher.teacher_name if sc.teacher else '',
                'attended': attended,
                'total_sessions': total_sessions,
                'percent': percent,
            })

        return {
            'student_id': student.student_id,
            'name': student.student_name,
            'student_rollNo': student.student_rollNo,
            'year': student.year,
            'program': student.dept,
            'section': student.section,
            'email': student.email or '',
            'overall_attendance': student.overall_attendance,
            'courses': courses_data,
        }

    def get(self, request):
        management = _get_management_for_user(request.user)
        if not management and not request.user.is_superuser:
            return Response({'error': 'Only management users can access student attendance summary'}, status=status.HTTP_403_FORBIDDEN)

        student_roll_no = request.query_params.get('student_rollNo', '').strip() or request.query_params.get('rfid', '').strip()
        student_id = request.query_params.get('student_id', '').strip()
        program = (request.query_params.get('program', '') or request.query_params.get('dept', '')).strip()
        year = request.query_params.get('year', '').strip()

        if not student_roll_no and not student_id and not program and not year:
            return Response(
                {'error': 'Provide at least one of student_rollNo, student_id, program, or year as query param'},
                status=status.HTTP_400_BAD_REQUEST
            )

        student_qs = Student.objects.all()
        if management and not request.user.is_superuser:
            student_qs = student_qs.filter(management=management)

        if student_roll_no:
            student_qs = student_qs.filter(student_rollNo=student_roll_no)
        if student_id:
            student_qs = student_qs.filter(student_id=student_id)
        if program:
            student_qs = student_qs.filter(dept=program)
        if year:
            student_qs = student_qs.filter(year=year)

        students = list(student_qs.order_by('student_id'))
        if not students:
            return Response({'error': 'No students found for the provided filters'}, status=status.HTTP_404_NOT_FOUND)

        summaries = [self._build_student_summary(student) for student in students]

        is_legacy_single_lookup = bool(student_roll_no or student_id) and not program and not year and len(summaries) == 1
        if is_legacy_single_lookup:
            serializer = StudentAttendanceSummarySerializer(summaries[0])
            return Response(serializer.data, status=status.HTTP_200_OK)

        response_data = {
            'count': len(summaries),
            'filters': {
                key: value for key, value in {
                    'student_rollNo': student_roll_no,
                    'student_id': student_id,
                    'program': program,
                    'year': year,
                }.items() if value not in ('', None)
            },
            'students': summaries,
        }
        serializer = StudentAttendanceSummaryListSerializer(response_data)
        return Response(serializer.data, status=status.HTTP_200_OK)


def _attendance_percent(attended, total_sessions):
    """Return attendance percentage (0–100 rounded to 1 dp), avoiding division by zero."""
    return round(attended / total_sessions * 100, 1) if total_sessions > 0 else 0.0


class CourseAttendanceSummaryView(APIView):
    """
    Returns attendance summary for all students enrolled in a given course.

    GET /api/attendance/course/?course_code=<code>
         /api/attendance/course/?course_id=<pk>

    Used by the admin dashboard → View Attendance → Course-wise Attendance tab.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        management = _get_management_for_user(request.user)
        if not management and not request.user.is_superuser:
            return Response({'error': 'Only management users can access course attendance summary'}, status=status.HTTP_403_FORBIDDEN)

        course_code = request.query_params.get('course_code', '').strip()
        course_id = request.query_params.get('course_id', '').strip()

        if not course_code and not course_id:
            return Response(
                {'error': 'Provide course_code or course_id as query param'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            if course_code:
                course_qs = Course.objects.filter(course_code=course_code)
            else:
                course_qs = Course.objects.filter(course_id=course_id)

            if management and not request.user.is_superuser:
                course_qs = course_qs.filter(taught_courses__teacher__management=management).distinct()

            course = course_qs.get()
        except Course.DoesNotExist:
            return Response({'error': 'Course not found'}, status=status.HTTP_404_NOT_FOUND)

        # Total sessions held for this course
        sessions_qs = AttendanceSession.objects.filter(course=course)
        if management and not request.user.is_superuser:
            sessions_qs = sessions_qs.filter(teacher__management=management)
        # Keep response key name as total_sessions for frontend compatibility,
        # but value represents total slots taught.
        total_sessions = sessions_qs.aggregate(total=Sum('slot_count')).get('total') or 0

        # All students enrolled in this course via StudentCourse
        student_courses = StudentCourse.objects.filter(course=course).select_related('student')
        if management and not request.user.is_superuser:
            student_courses = student_courses.filter(student__management=management)
        students_data = []
        for sc in student_courses:
            attended = sc.classes_attended_count or 0
            percent = _attendance_percent(attended, total_sessions)

            students_data.append({
                'student_id': sc.student.student_id,
                'roll': sc.student.student_rollNo,
                'name': sc.student.student_name,
                'year': sc.student.year,
                'program': sc.student.dept,
                'section': sc.student.section,
                'attended': attended,
                'total_sessions': total_sessions,
                'percent': percent,
            })

        data = {
            'course_id': course.course_id,
            'course_code': course.course_code,
            'course_name': course.course_name,
            'students': students_data,
        }
        serializer = CourseAttendanceSummarySerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)


# Template-based views for login and register pages

def student_login_page(request):
    """
    Django template view for student login
    """
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        user = authenticate(request, username=email, password=password)
        
        if user is not None:
            try:
                student = Student.objects.get(user=user)
                login(request, user)
                messages.success(request, 'Login successful!')
                return redirect('student-dashboard')
            except Student.DoesNotExist:
                messages.error(request, 'Student profile not found for this user')
        else:
            messages.error(request, 'Invalid email or password')
    
    return render(request, 'core/student_login.html')


def teacher_login_page(request):
    """
    Django template view for teacher login
    """
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        user = authenticate(request, username=email, password=password)
        
        if user is not None:
            try:
                teacher = Teacher.objects.get(user=user)
                login(request, user)
                messages.success(request, 'Login successful!')
                return redirect('teacher-dashboard')
            except Teacher.DoesNotExist:
                messages.error(request, 'Teacher profile not found for this user')
        else:
            messages.error(request, 'Invalid email or password')
    
    return render(request, 'core/teacher_login.html')


def management_login_page(request):
    """
    Django template view for management login
    """
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        user = authenticate(request, username=email, password=password)
        
        if user is not None:
            try:
                management = Management.objects.get(user=user)
                login(request, user)
                messages.success(request, 'Login successful!')
                return redirect('management-dashboard')
            except Management.DoesNotExist:
                messages.error(request, 'Management profile not found for this user')
        else:
            messages.error(request, 'Invalid email or password')
    
    return render(request, 'core/management_login.html')


def student_register_page(request):
    """
    Django template view for student registration
    """
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        student_name = request.POST.get('student_name')
        student_roll_no = request.POST.get('student_rollNo')
        year = request.POST.get('year')
        dept = request.POST.get('dept')
        section = request.POST.get('section')
        
        errors = []
        
        # Validation
        if password != password2:
            errors.append("Passwords don't match")
        
        if User.objects.filter(email=email).exists():
            errors.append("Email already exists")
        
        try:
            validate_password(password)
        except ValidationError as e:
            errors.extend(e.messages)
        
        if not errors:
            try:
                # Create user
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    password=password
                )
                
                # Create student
                student = Student.objects.create(
                    user=user,
                    email=email,
                    student_name=student_name,
                    student_rollNo=student_roll_no,
                    year=int(year),
                    dept=dept,
                    section=section
                )
                
                messages.success(request, 'Registration successful! Please login.')
                return redirect('student-login-page')
            except Exception as e:
                errors.append(str(e))
        
        return render(request, 'core/student_register.html', {'errors': errors})
    
    return render(request, 'core/student_register.html')


def teacher_register_page(request):
    """
    Django template view for teacher registration
    """
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        teacher_name = request.POST.get('teacher_name')
        teacher_roll_no = request.POST.get('teacher_rollNo')
        
        errors = []
        
        # Validation
        if password != password2:
            errors.append("Passwords don't match")
        
        if User.objects.filter(email=email).exists():
            errors.append("Email already exists")
        
        try:
            validate_password(password)
        except ValidationError as e:
            errors.extend(e.messages)
        
        if not errors:
            try:
                # Create user
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    password=password
                )
                
                # Create teacher
                teacher = Teacher.objects.create(
                    user=user,
                    email=email,
                    teacher_name=teacher_name,
                    teacher_rollNo=teacher_roll_no
                )
                
                messages.success(request, 'Registration successful! Please login.')
                return redirect('teacher-login-page')
            except Exception as e:
                errors.append(str(e))
        
        return render(request, 'core/teacher_register.html', {'errors': errors})
    
    return render(request, 'core/teacher_register.html')


def management_register_page(request):
    """
    Django template view for management registration
    """
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        management_name = request.POST.get('Management_name')
        
        errors = []
        
        # Validation
        if password != password2:
            errors.append("Passwords don't match")
        
        if User.objects.filter(email=email).exists():
            errors.append("Email already exists")
        
        try:
            validate_password(password)
        except ValidationError as e:
            errors.extend(e.messages)
        
        if not errors:
            try:
                # Create user
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    password=password
                )
                
                # Create management
                management = Management.objects.create(
                    user=user,
                    email=email,
                    Management_name=management_name
                )
                
                messages.success(request, 'Registration successful! Please login.')
                return redirect('management-login-page')
            except Exception as e:
                errors.append(str(e))
        
        return render(request, 'core/management_register.html', {'errors': errors})
    
    return render(request, 'core/management_register.html')


@login_required
def student_dashboard(request):
    """
    Dashboard view for students with attendance information
    """
    try:
        student = Student.objects.get(user=request.user)
        
        # Get course-wise attendance
        student_courses = StudentCourse.objects.filter(student=student).select_related('course', 'teacher')
        
        course_attendance = []
        for sc in student_courses:
            # Calculate attendance percentage for this course
            taught_course = TaughtCourse.objects.filter(
                course=sc.course, 
                teacher=sc.teacher
            ).first()
            
            if taught_course:
                # Parse classes attended and classes taken
                classes_attended = sc.classes_attended_count or 0
                classes_taken = taught_course.classes_taken_count or 0
                
                attendance_percentage = (classes_attended / classes_taken * 100) if classes_taken > 0 else 0
            else:
                attendance_percentage = 0
            
            course_attendance.append({
                'course_name': sc.course.course_name,
                'teacher_name': sc.teacher.teacher_name,
                'attendance': round(attendance_percentage, 1)
            })
        
        context = {
            'student_name': student.student_name,
            'student_id': student.student_id,
            'overall_attendance': round(student.overall_attendance, 1),
            'total_courses': len(course_attendance),
            'course_attendance': course_attendance,
        }
        
        return render(request, 'core/student_dashboard.html', context)
    except Student.DoesNotExist:
        messages.error(request, 'Student profile not found')
        return redirect('student-login-page')


@login_required
def teacher_dashboard(request):
    """
    Dashboard view for teachers
    """
    try:
        teacher = Teacher.objects.get(user=request.user)
        
        # Get courses taught by this teacher
        taught_courses = TaughtCourse.objects.filter(teacher=teacher).select_related('course')
        
        courses = []
        for tc in taught_courses:
            courses.append({
                'course_name': tc.course.course_name,
                'classes_taken_count': tc.classes_taken_count or 0
            })
        
        context = {
            'teacher_name': teacher.teacher_name,
            'teacher_id': teacher.teacher_id,
            'email': teacher.email,
            'total_courses': len(courses),
            'courses': courses,
        }
        
        return render(request, 'core/teacher_dashboard.html', context)
    except Teacher.DoesNotExist:
        messages.error(request, 'Teacher profile not found')
        return redirect('teacher-login-page')


@login_required
def management_dashboard(request):
    """
    Dashboard view for management
    """
    try:
        management = Management.objects.get(user=request.user)
        
        context = {
            'management_name': management.Management_name,
            'management_id': management.Management_id,
            'email': management.email,
        }
        
        return render(request, 'core/management_dashboard.html', context)
    except Management.DoesNotExist:
        messages.error(request, 'Management profile not found')
        return redirect('management-login-page')


def logout_page(request):
    """
    Logout view
    """
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('student-login-page')


