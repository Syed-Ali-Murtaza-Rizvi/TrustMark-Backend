from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.db.models import Sum
from .models import (
    Student, Teacher, Management, Course, Class, TaughtCourse, StudentCourse,
    UpdateAttendanceRequest, AttendanceSession, AttendanceRecord
)


# ============ Model Serializers for CRUD operations ============

class StudentCourseInlineSerializer(serializers.ModelSerializer):
    """Inline courses for StudentSerializer"""
    course_id = serializers.IntegerField(source='course.course_id', read_only=True)
    course_code = serializers.CharField(source='course.course_code', read_only=True)
    course_name = serializers.CharField(source='course.course_name', read_only=True)
    classes_taken_count = serializers.SerializerMethodField()

    def get_classes_taken_count(self, obj):
        student = getattr(obj, 'student', None)
        teacher = getattr(obj, 'teacher', None)

        if teacher and student:
            taught_course = TaughtCourse.objects.filter(
                teacher=teacher,
                course=obj.course,
                section=student.section,
                year=student.year,
            ).first()
            if taught_course:
                return taught_course.classes_taken_count or 0

        if not student:
            return 0

        session_qs = AttendanceSession.objects.filter(
            course=obj.course,
            section=student.section,
            year=student.year,
        )
        if student.management_id:
            session_qs = session_qs.filter(teacher__management=student.management)

        return session_qs.aggregate(total=Sum('slot_count')).get('total') or 0

    class Meta:
        model = StudentCourse
        fields = ['id', 'course_id', 'course_code', 'course_name', 'classes_attended_count', 'classes_taken_count']


class StudentSerializer(serializers.ModelSerializer):
    """Serializer for Student model CRUD operations"""
    # 'program' is a frontend-friendly alias for the 'dept' field
    program = serializers.CharField(source='dept', read_only=True)
    courses = StudentCourseInlineSerializer(source='student_courses', many=True, read_only=True)

    class Meta:
        model = Student
        fields = ['student_id', 'student_name', 'email', 'student_rollNo', 'overall_attendance', 'year', 'dept', 'program', 'section', 'management', 'courses']
        read_only_fields = ['student_id', 'program', 'courses']


class TaughtCourseInlineSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source='course.course_name', read_only=True)
    course_code = serializers.CharField(source='course.course_code', read_only=True)

    class Meta:
        model = TaughtCourse
        fields = ['id', 'course', 'course_code', 'course_name', 'section', 'year']


class TeacherSerializer(serializers.ModelSerializer):
    """Serializer for Teacher model CRUD operations"""
    courses = TaughtCourseInlineSerializer(source='taught_courses', many=True, read_only=True)

    class Meta:
        model = Teacher
        fields = ['teacher_id', 'teacher_name', 'email', 'teacher_rollNo', 'phone', 'years', 'programs', 'management', 'courses']
        read_only_fields = ['teacher_id', 'courses']


class ManagementSerializer(serializers.ModelSerializer):
    """Serializer for Management model CRUD operations"""
    class Meta:
        model = Management
        fields = ['Management_id', 'Management_name', 'email']
        read_only_fields = ['Management_id']


class CourseSerializer(serializers.ModelSerializer):
    """Serializer for Course model CRUD operations"""
    class Meta:
        model = Course
        fields = ['course_id', 'course_code', 'course_name']
        read_only_fields = ['course_id']


class ClassSerializer(serializers.ModelSerializer):
    """Serializer for Class model CRUD operations"""
    class Meta:
        model = Class
        fields = ['classroom_id', 'scanner_id']
        read_only_fields = ['classroom_id']


class TaughtCourseSerializer(serializers.ModelSerializer):
    """Serializer for TaughtCourse model CRUD operations"""
    course_name = serializers.CharField(source='course.course_name', read_only=True)
    teacher_name = serializers.CharField(source='teacher.teacher_name', read_only=True)

    class Meta:
        model = TaughtCourse
        fields = ['id', 'course', 'teacher', 'course_name', 'teacher_name', 'classes_taken_count', 'section', 'year']
        read_only_fields = ['id']


class StudentCourseSerializer(serializers.ModelSerializer):
    """Serializer for StudentCourse model CRUD operations"""
    student_name = serializers.CharField(source='student.student_name', read_only=True)
    course_name = serializers.CharField(source='course.course_name', read_only=True)
    teacher_name = serializers.CharField(source='teacher.teacher_name', read_only=True)

    class Meta:
        model = StudentCourse
        fields = ['id', 'student', 'course', 'teacher', 'student_name', 'course_name', 'teacher_name', 'classes_attended_count', 'classes_absent_count']
        read_only_fields = ['id']


class UpdateAttendanceRequestSerializer(serializers.ModelSerializer):
    """Serializer for UpdateAttendanceRequest model CRUD operations
    
    Supports two input modes:
    1. Standard: teacher_rollNo + course + classes_to_add
    2. Flexible: course_code + slot_count (infers teacher and student)
    """
    teacher = serializers.PrimaryKeyRelatedField(read_only=True)
    student = serializers.PrimaryKeyRelatedField(read_only=True)
    teacher_rollNo = serializers.SlugRelatedField(
        source='teacher',
        slug_field='teacher_rollNo',
        queryset=Teacher.objects.all(),
        required=False,  # Changed to False - will be set by perform_create
        allow_null=True,
    )
    student_rollNo = serializers.SlugRelatedField(
        source='student',
        slug_field='student_rollNo',
        queryset=Student.objects.all(),
    )
    
    # Make course and classes_to_add optional to support flexible input
    course = serializers.PrimaryKeyRelatedField(
        queryset=Course.objects.all(),
        required=False,
        allow_null=True,
    )
    classes_to_add = serializers.CharField(required=False, allow_blank=True)
    
    # Alternative input fields for flexible API
    course_code = serializers.CharField(required=False, write_only=True)
    slot_count = serializers.IntegerField(required=False, write_only=True)
    program = serializers.CharField(required=False, write_only=True)
    section = serializers.CharField(required=False, write_only=True)
    
    teacher_name = serializers.CharField(source='teacher.teacher_name', read_only=True)
    student_name = serializers.CharField(source='student.student_name', read_only=True)
    student_dept = serializers.CharField(source='student.dept', read_only=True)
    student_section = serializers.CharField(source='student.section', read_only=True)
    course_name = serializers.CharField(source='course.course_name', read_only=True)
    processed_by_name = serializers.CharField(source='processed_by.Management_name', read_only=True)
    management_name = serializers.CharField(source='management.Management_name', read_only=True)

    class Meta:
        model = UpdateAttendanceRequest
        fields = [
            'id', 'teacher', 'student', 'teacher_rollNo', 'student_rollNo',
            'course', 'management', 'classes_to_add', 'reason', 'attendanceType',
            'status', 'requested_at', 'processed_at', 'processed_by',
            'course_code', 'slot_count', 'program', 'section',
            'teacher_name', 'student_name', 'student_dept', 'student_section', 'course_name', 'processed_by_name', 'management_name'
        ]
        read_only_fields = [
            'id', 'teacher', 'student', 'status', 'requested_at', 'processed_at', 'processed_by', 'management'
        ]

    def validate(self, attrs):
        """Validate that either standard or flexible input is provided"""
        # Check if using flexible mode (course_code + slot_count)
        has_course_code = 'course_code' in self.initial_data
        has_slot_count = 'slot_count' in self.initial_data
        has_course = 'course' in self.initial_data and self.initial_data['course'] is not None
        has_classes = 'classes_to_add' in self.initial_data and self.initial_data['classes_to_add']
        
        if has_course_code or has_slot_count:
            # Flexible mode: require course_code and student_rollNo
            if not has_course_code:
                raise serializers.ValidationError("course_code is required when using flexible input mode")
            if 'student_rollNo' not in self.initial_data:
                raise serializers.ValidationError("student_rollNo is required")
                
            # Resolve course by course_code
            course_code = self.initial_data.get('course_code')
            course = Course.objects.filter(course_code=course_code).first()
            if not course:
                raise serializers.ValidationError(f"Course with code '{course_code}' not found")
            
            attrs['course'] = course
            
            # Generate classes_to_add from slot_count if provided
            if has_slot_count:
                slot_count = attrs.get('slot_count', 1)
                classes = [f"Slot {i+1}" for i in range(slot_count)]
                attrs['classes_to_add'] = ', '.join(classes)
            else:
                # If no slot_count, require classes_to_add
                if not has_classes:
                    attrs['classes_to_add'] = ''
        else:
            # Standard mode: require course (teacher_rollNo is optional - will be set by perform_create)
            if not has_course:
                raise serializers.ValidationError("course is required when not using course_code")
            if not has_classes:
                raise serializers.ValidationError("classes_to_add is required when not using slot_count")
        
        # Remove temporary fields that aren't part of the model
        attrs.pop('course_code', None)
        attrs.pop('slot_count', None)
        attrs.pop('program', None)
        attrs.pop('section', None)
        
        return attrs

    def create(self, validated_data):
        """Create instance with proper teacher assignment"""
        instance = super().create(validated_data)
        return instance


# ============ Registration Serializers ============

class StudentRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    email = serializers.EmailField(required=True)

    class Meta:
        model = Student
        fields = ('email', 'password', 'password2', 'student_name', 'student_rollNo', 'year', 'dept', 'section')

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        
        if User.objects.filter(email=attrs['email']).exists():
            raise serializers.ValidationError({"email": "Email already exists."})
        
        return attrs

    def create(self, validated_data):
        # Remove password2 as it's not needed for User creation
        validated_data.pop('password2')
        
        # Create User instance
        user = User.objects.create_user(
            username=validated_data['email'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        
        # Create Student instance
        student = Student.objects.create(
            user=user,
            email=validated_data['email'],
            student_name=validated_data['student_name'],
            student_rollNo=validated_data['student_rollNo'],
            year=validated_data['year'],
            dept=validated_data['dept'],
            section=validated_data['section']
        )
        
        return student


class TeacherRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    email = serializers.EmailField(required=True)

    class Meta:
        model = Teacher
        fields = ('email', 'password', 'password2', 'teacher_name', 'teacher_rollNo')

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        
        if User.objects.filter(email=attrs['email']).exists():
            raise serializers.ValidationError({"email": "Email already exists."})
        
        return attrs

    def create(self, validated_data):
        # Remove password2 as it's not needed for User creation
        validated_data.pop('password2')
        
        # Create User instance
        user = User.objects.create_user(
            username=validated_data['email'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        
        # Create Teacher instance
        teacher = Teacher.objects.create(
            user=user,
            email=validated_data['email'],
            teacher_name=validated_data['teacher_name'],
            teacher_rollNo=validated_data['teacher_rollNo']
        )
        
        return teacher


class ManagementRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    email = serializers.EmailField(required=True)

    class Meta:
        model = Management
        fields = ('email', 'password', 'password2', 'Management_name')

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        
        if User.objects.filter(email=attrs['email']).exists():
            raise serializers.ValidationError({"email": "Email already exists."})
        
        return attrs

    def create(self, validated_data):
        # Remove password2 as it's not needed for User creation
        validated_data.pop('password2')
        
        # Create User instance
        user = User.objects.create_user(
            username=validated_data['email'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        
        # Create Management instance
        management = Management.objects.create(
            user=user,
            email=validated_data['email'],
            Management_name=validated_data['Management_name']
        )
        
        return management


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)


class AttendanceSessionSerializer(serializers.ModelSerializer):
    """Serializer for AttendanceSession model"""
    teacher_name = serializers.CharField(source='teacher.teacher_name', read_only=True)
    course_name = serializers.CharField(source='course.course_name', read_only=True)

    class Meta:
        model = AttendanceSession
        fields = [
            'id', 'teacher', 'course', 'section', 'year', 'slot_count', 'status',
            'qr_code_token', 'started_at', 'stopped_at',
            'teacher_name', 'course_name'
        ]
        read_only_fields = ['id', 'qr_code_token', 'started_at', 'stopped_at']


class AttendanceRecordSerializer(serializers.ModelSerializer):
    """Serializer for AttendanceRecord model"""
    student_name = serializers.CharField(source='student.student_name', read_only=True)
    session_details = serializers.SerializerMethodField()

    class Meta:
        model = AttendanceRecord
        fields = [
            'id', 'session', 'student', 'rfid_scanned', 'rfid_scanned_at',
            'qr_scanned', 'qr_scanned_at', 'is_present', 'marked_present_at',
            'student_name', 'session_details'
        ]
        read_only_fields = [
            'id', 'rfid_scanned', 'rfid_scanned_at', 'qr_scanned', 'qr_scanned_at',
            'is_present', 'marked_present_at'
        ]

    def get_session_details(self, obj):
        return {
            'course': obj.session.course.course_name,
            'teacher': obj.session.teacher.teacher_name,
            'section': obj.session.section,
            'year': obj.session.year
        }


class RFIDScanSerializer(serializers.Serializer):
    """Serializer for RFID scan requests"""
    rfid = serializers.CharField(required=True)
    session_id = serializers.IntegerField(required=True)


class QRScanSerializer(serializers.Serializer):
    """Serializer for QR scan requests"""
    qr_token = serializers.CharField(required=True)
    student_id = serializers.IntegerField(required=True)


# ============ Admin Dashboard Attendance Serializers ============

class StudentCourseSummarySerializer(serializers.Serializer):
    """Per-course attendance summary for one student (used in student-wise view)."""
    course_id = serializers.IntegerField()
    course_code = serializers.CharField()
    course_name = serializers.CharField()
    teacher_name = serializers.CharField()
    attended = serializers.IntegerField()
    total_sessions = serializers.IntegerField()
    percent = serializers.FloatField()


class StudentAttendanceSummarySerializer(serializers.Serializer):
    """Full attendance summary for a single student across all enrolled courses."""
    student_id = serializers.IntegerField()
    name = serializers.CharField()
    student_rollNo = serializers.CharField()
    year = serializers.IntegerField()
    program = serializers.CharField()
    section = serializers.CharField()
    email = serializers.CharField()
    overall_attendance = serializers.FloatField()
    courses = StudentCourseSummarySerializer(many=True)


class StudentAttendanceSummaryListSerializer(serializers.Serializer):
    """Attendance summary response for multiple filtered students."""
    count = serializers.IntegerField()
    filters = serializers.DictField(required=False)
    students = StudentAttendanceSummarySerializer(many=True)


class CourseStudentAttendanceSerializer(serializers.Serializer):
    """Per-student attendance entry for a course (used in course-wise view)."""
    student_id = serializers.IntegerField()
    roll = serializers.CharField()
    name = serializers.CharField()
    year = serializers.IntegerField()
    program = serializers.CharField()    # dept
    section = serializers.CharField()
    attended = serializers.IntegerField()
    total_sessions = serializers.IntegerField()
    percent = serializers.FloatField()


class CourseAttendanceSummarySerializer(serializers.Serializer):
    """Attendance summary for all students enrolled in a given course."""
    course_id = serializers.IntegerField()
    course_code = serializers.CharField()
    course_name = serializers.CharField()
    students = CourseStudentAttendanceSerializer(many=True)
