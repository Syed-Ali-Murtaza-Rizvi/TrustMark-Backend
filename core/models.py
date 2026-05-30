from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Class(models.Model):
    classroom_id = models.AutoField(primary_key=True)
    scanner_id = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return f"Classroom {self.classroom_id}"


class Student(models.Model):
    student_id = models.AutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, related_name='student_profile')
    student_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True, null=True, blank=True)
    # image = models.ImageField(upload_to='student_images/', null=True, blank=True)  # for CV
    student_rollNo = models.CharField(max_length=100, unique=True)
    overall_attendance = models.FloatField(default=0.0)  # percentage
    year = models.IntegerField()  # e.g., 1, 2, 3, 4
    dept = models.CharField(max_length=100)  # e.g., CS, IT
    section = models.CharField(max_length=10)  # e.g., A, B, C
    management = models.ForeignKey('Management', on_delete=models.SET_NULL, null=True, blank=True, related_name='students')

    def __str__(self):
        return self.student_name

class Course(models.Model):
    course_id = models.AutoField(primary_key=True)
    course_code = models.CharField(max_length=20, blank=True, default='')  # e.g., CS301
    course_name = models.CharField(max_length=200)

    def __str__(self):
        if self.course_code:
            return f"{self.course_code} - {self.course_name}"
        return self.course_name

class Teacher(models.Model):
    teacher_id = models.AutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, related_name='teacher_profile')
    teacher_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True, null=True, blank=True)
    # image = models.ImageField(upload_to='teacher_images/', null=True, blank=True)
    teacher_rollNo = models.CharField(max_length=100, unique=True)
    phone = models.CharField(max_length=20, blank=True, default='')
    years = models.CharField(max_length=255, blank=True, default='')     # comma-separated, e.g. "1,2,3"
    programs = models.CharField(max_length=255, blank=True, default='')  # comma-separated, e.g. "CS,IT"
    management = models.ForeignKey('Management', on_delete=models.SET_NULL, null=True, blank=True, related_name='teachers')

    def __str__(self):
        return self.teacher_name

class Management(models.Model):
    Management_id = models.AutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, related_name='management_profile')
    Management_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True, null=True, blank=True)

    def __str__(self):
        return self.Management_name


class UserFaceEmbedding(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='face_embedding_profile',
    )
    embedding = models.JSONField(default=list, blank=True)
    cv_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"FaceEmbedding(user_id={self.user_id})"

class TaughtCourse(models.Model):
    course = models.ForeignKey('Course', on_delete=models.CASCADE, related_name='taught_courses')
    teacher = models.ForeignKey('Teacher', on_delete=models.CASCADE, related_name='taught_courses')
    classes_taken_count = models.PositiveIntegerField(default=0)
    section = models.CharField(max_length=10, blank=True)  # e.g., A, B, C
    year = models.IntegerField(null=True, blank=True)  # e.g., 1, 2, 3, 4

    def __str__(self):
        return f"{self.teacher} teaches {self.course}"

class StudentCourse(models.Model):
    student = models.ForeignKey('Student', on_delete=models.CASCADE, related_name='student_courses')
    course = models.ForeignKey('Course', on_delete=models.CASCADE, related_name='student_courses')
    teacher = models.ForeignKey('Teacher', on_delete=models.SET_NULL, null=True, blank=True, related_name='student_courses')
    classes_attended_count = models.PositiveIntegerField(default=0)
    classes_absent_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.student} - {self.course} - {self.teacher}"


class UpdateAttendanceRequest(models.Model):
    """
    Model for attendance update requests sent by teachers.
    Teachers can request attendance updates for specific students in specific courses.
    Management can approve or reject these requests.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    ATTENDANCE_TYPE_CHOICES = [
        ('regular', 'Regular'),
        ('compensatory', 'Compensatory'),
    ]

    teacher = models.ForeignKey('Teacher', on_delete=models.CASCADE, related_name='attendance_update_requests')
    student = models.ForeignKey('Student', on_delete=models.CASCADE, related_name='attendance_update_requests')
    course = models.ForeignKey('Course', on_delete=models.CASCADE, related_name='attendance_update_requests')
    management = models.ForeignKey('Management', on_delete=models.SET_NULL, null=True, blank=True, related_name='attendance_requests')
    classes_to_add = models.CharField(max_length=255)  # e.g., "Class A, Class B" - classes to add to attendance
    reason = models.TextField(blank=True)  # Optional reason for the request
    attendanceType = models.CharField(max_length=20, choices=ATTENDANCE_TYPE_CHOICES, default='regular')  # regular or compensatory
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey('Management', on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_attendance_requests')

    def __str__(self):
        return f"Request by {self.teacher} for {self.student} in {self.course} - {self.status}"

    class Meta:
        ordering = ['-requested_at']


class AttendanceSession(models.Model):
    """
    Model for attendance sessions started by teachers.
    Teachers can start/stop sessions for a specific course, section, and year.
    """
    ATTENDANCE_TYPE_CHOICES = [
        ('regular', 'Regular'),
        ('compensatory', 'Compensatory'),
    ]
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('stopped', 'Stopped'),
    ]

    teacher = models.ForeignKey('Teacher', on_delete=models.CASCADE, related_name='attendance_sessions')
    course = models.ForeignKey('Course', on_delete=models.CASCADE, related_name='attendance_sessions')
    section = models.CharField(max_length=10)  # e.g., A, B, C
    year = models.IntegerField()  # e.g., 1, 2, 3, 4
    slot_count = models.PositiveIntegerField(default=1)
    attendance_type = models.CharField(max_length=20, choices=ATTENDANCE_TYPE_CHOICES, default='regular')
    program = models.CharField(max_length=100, blank=True, default='')
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    radius_meters = models.PositiveIntegerField(default=50)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    qr_code_token = models.CharField(max_length=255, unique=True)  # Token for QR code validation
    started_at = models.DateTimeField(auto_now_add=True)
    stopped_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.teacher} - {self.course} - {self.section} - Year {self.year} - {self.status}"

    class Meta:
        ordering = ['-started_at']


class AttendanceRecord(models.Model):
    """
    Model for tracking 2FA attendance (RFID + QR code).
    Students must scan both RFID and QR code to mark attendance.
    """
    session = models.ForeignKey('AttendanceSession', on_delete=models.CASCADE, related_name='attendance_records')
    student = models.ForeignKey('Student', on_delete=models.CASCADE, related_name='attendance_records')
    rfid_scanned = models.BooleanField(default=False)
    rfid_scanned_at = models.DateTimeField(null=True, blank=True)
    qr_scanned = models.BooleanField(default=False)
    qr_scanned_at = models.DateTimeField(null=True, blank=True)
    is_present = models.BooleanField(default=False)  # True only when both RFID and QR are scanned
    marked_present_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.student} - {self.session} - Present: {self.is_present}"

    class Meta:
        unique_together = ['session', 'student']
        ordering = ['-marked_present_at']
