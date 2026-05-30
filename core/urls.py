from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    StudentRegistrationView,
    TeacherRegistrationView,
    ManagementRegistrationView,
    StudentLoginView,
    TeacherLoginView,
    ManagementLoginView,
    student_login_page,
    teacher_login_page,
    management_login_page,
    student_register_page,
    teacher_register_page,
    management_register_page,
    student_dashboard,
    teacher_dashboard,
    management_dashboard,
    logout_page,
    StudentViewSet,
    TeacherViewSet,
    ManagementViewSet,
    CourseViewSet,
    ClassViewSet,
    TaughtCourseViewSet,
    StudentCourseViewSet,
    UpdateAttendanceRequestViewSet,
    AttendanceSessionViewSet,
    AttendanceRecordViewSet,
    RFIDScanView,
    QRScanView,
    UnifiedLoginView,
    UnifiedSignupView,
    FaceRegisterView,
    FaceVerifyView,
    UserDetailsView,
    UserLogoutView,
    StudentFilterOptionsView,
    TeacherFilterOptionsView,
    StudentAttendanceSummaryView,
    CourseAttendanceSummaryView,
)

# Create a router for CRUD ViewSets
router = DefaultRouter()
router.register(r'students', StudentViewSet, basename='student')
router.register(r'teachers', TeacherViewSet, basename='teacher')
router.register(r'management', ManagementViewSet, basename='management')
router.register(r'courses', CourseViewSet, basename='course')
router.register(r'classes', ClassViewSet, basename='class')
router.register(r'taught-courses', TaughtCourseViewSet, basename='taughtcourse')
router.register(r'student-courses', StudentCourseViewSet, basename='studentcourse')
router.register(r'update-attendance-requests', UpdateAttendanceRequestViewSet, basename='updateattendancerequest')
router.register(r'attendance-sessions', AttendanceSessionViewSet, basename='attendancesession')
router.register(r'attendance-records', AttendanceRecordViewSet, basename='attendancerecord')

urlpatterns = [
    # ── Frontend-compatible unified endpoints ──────────────────────────────
    # These match the URLs defined in the frontend's common/index.js
    path('login', UnifiedLoginView.as_view(), name='unified-login'),
    path('signup', UnifiedSignupView.as_view(), name='unified-signup'),
    path('face/register/', FaceRegisterView.as_view(), name='face-register'),
    path('face/verify/', FaceVerifyView.as_view(), name='face-verify'),
    path('user-details', UserDetailsView.as_view(), name='user-details'),
    path('user-logout', UserLogoutView.as_view(), name='user-logout'),

    # Explicit filter option endpoints must appear before router detail routes.
    path('students/filter-options/', StudentFilterOptionsView.as_view(), name='student-filter-options'),
    path('teachers/filter-options/', TeacherFilterOptionsView.as_view(), name='teacher-filter-options'),

    # CRUD API endpoints (from router)
    path('', include(router.urls)),
    
    # Custom actions for UpdateAttendanceRequest
    path('update-attendance-requests/<int:pk>/approve/', 
         UpdateAttendanceRequestViewSet.as_view({'post': 'approve'}), 
         name='updateattendancerequest-approve'),
    path('update-attendance-requests/<int:pk>/reject/', 
         UpdateAttendanceRequestViewSet.as_view({'post': 'reject'}), 
         name='updateattendancerequest-reject'),
    
    # Attendance scanning endpoints
    path('attendance/rfid-scan/', RFIDScanView.as_view(), name='rfid-scan'),
    path('attendance/qr-scan/', QRScanView.as_view(), name='qr-scan'),

    # Admin dashboard attendance summary endpoints
    path('attendance/student/', StudentAttendanceSummaryView.as_view(), name='attendance-student-summary'),
    path('attendance/course/', CourseAttendanceSummaryView.as_view(), name='attendance-course-summary'),
    
    # API Registration endpoints
    path('auth/register/student/', StudentRegistrationView.as_view(), name='student-register'),
    path('auth/register/teacher/', TeacherRegistrationView.as_view(), name='teacher-register'),
    path('auth/register/management/', ManagementRegistrationView.as_view(), name='management-register'),
    
    # API Login endpoints
    path('auth/login/student/', StudentLoginView.as_view(), name='student-login'),
    path('auth/login/teacher/', TeacherLoginView.as_view(), name='teacher-login'),
    path('auth/login/management/', ManagementLoginView.as_view(), name='management-login'),
    
    # Template-based login pages
    path('login/student/', student_login_page, name='student-login-page'),
    path('login/teacher/', teacher_login_page, name='teacher-login-page'),
    path('login/management/', management_login_page, name='management-login-page'),
    
    # Template-based register pages
    path('register/student/', student_register_page, name='student-register-page'),
    path('register/teacher/', teacher_register_page, name='teacher-register-page'),
    path('register/management/', management_register_page, name='management-register-page'),
    
    # Dashboard pages
    path('dashboard/student/', student_dashboard, name='student-dashboard'),
    path('dashboard/teacher/', teacher_dashboard, name='teacher-dashboard'),
    path('dashboard/management/', management_dashboard, name='management-dashboard'),
    
    # Logout
    path('logout/', logout_page, name='logout-page'),
]
