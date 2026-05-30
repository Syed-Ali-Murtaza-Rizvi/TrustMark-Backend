from django.test import TestCase
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth.models import User
from .models import (
    Student, Teacher, Management, Course, Class, TaughtCourse, StudentCourse,
    UpdateAttendanceRequest, AttendanceSession, AttendanceRecord
)


class StudentRegistrationTestCase(APITestCase):
    def setUp(self):
        self.url = reverse('student-register')
        self.valid_data = {
            'email': 'student@test.com',
            'password': 'TestPass123!',
            'password2': 'TestPass123!',
            'student_name': 'Test Student',
            'student_rollNo': 'RFID001',
            'year': 1,
            'dept': 'CS',
            'section': 'A'
        }

    def test_student_registration_success(self):
        """Test successful student registration"""
        response = self.client.post(self.url, self.valid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('student_id', response.data)
        self.assertEqual(response.data['email'], 'student@test.com')
        
        # Verify user and student were created
        self.assertTrue(User.objects.filter(email='student@test.com').exists())
        self.assertTrue(Student.objects.filter(email='student@test.com').exists())

    def test_student_registration_password_mismatch(self):
        """Test registration fails when passwords don't match"""
        data = self.valid_data.copy()
        data['password2'] = 'DifferentPass123!'
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_student_registration_duplicate_email(self):
        """Test registration fails with duplicate email"""
        self.client.post(self.url, self.valid_data, format='json')
        response = self.client.post(self.url, self.valid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class StudentLoginTestCase(APITestCase):
    def setUp(self):
        self.register_url = reverse('student-register')
        self.login_url = reverse('student-login')
        self.credentials = {
            'email': 'student@test.com',
            'password': 'TestPass123!',
            'password2': 'TestPass123!',
            'student_name': 'Test Student',
            'student_rollNo': 'RFID001',
            'year': 1,
            'dept': 'CS',
            'section': 'A'
        }
        # Register a student
        self.client.post(self.register_url, self.credentials, format='json')

    def test_student_login_success(self):
        """Test successful student login"""
        response = self.client.post(self.login_url, {
            'email': 'student@test.com',
            'password': 'TestPass123!'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data['user_type'], 'student')

    def test_student_login_invalid_password(self):
        """Test login fails with invalid password"""
        response = self.client.post(self.login_url, {
            'email': 'student@test.com',
            'password': 'WrongPassword123!'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_student_login_nonexistent_user(self):
        """Test login fails with nonexistent user"""
        response = self.client.post(self.login_url, {
            'email': 'nonexistent@test.com',
            'password': 'TestPass123!'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TeacherRegistrationTestCase(APITestCase):
    def setUp(self):
        self.url = reverse('teacher-register')
        self.valid_data = {
            'email': 'teacher@test.com',
            'password': 'TestPass123!',
            'password2': 'TestPass123!',
            'teacher_name': 'Test Teacher',
            'teacher_rollNo': 'RFID002'
        }

    def test_teacher_registration_success(self):
        """Test successful teacher registration"""
        response = self.client.post(self.url, self.valid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('teacher_id', response.data)
        self.assertEqual(response.data['email'], 'teacher@test.com')
        
        # Verify user and teacher were created
        self.assertTrue(User.objects.filter(email='teacher@test.com').exists())
        self.assertTrue(Teacher.objects.filter(email='teacher@test.com').exists())


class TeacherLoginTestCase(APITestCase):
    def setUp(self):
        self.register_url = reverse('teacher-register')
        self.login_url = reverse('teacher-login')
        self.credentials = {
            'email': 'teacher@test.com',
            'password': 'TestPass123!',
            'password2': 'TestPass123!',
            'teacher_name': 'Test Teacher',
            'teacher_rollNo': 'RFID002'
        }
        # Register a teacher
        self.client.post(self.register_url, self.credentials, format='json')

    def test_teacher_login_success(self):
        """Test successful teacher login"""
        response = self.client.post(self.login_url, {
            'email': 'teacher@test.com',
            'password': 'TestPass123!'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data['user_type'], 'teacher')


class ManagementRegistrationTestCase(APITestCase):
    def setUp(self):
        self.url = reverse('management-register')
        self.valid_data = {
            'email': 'management@test.com',
            'password': 'TestPass123!',
            'password2': 'TestPass123!',
            'Management_name': 'Test Management'
        }

    def test_management_registration_success(self):
        """Test successful management registration"""
        response = self.client.post(self.url, self.valid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('management_id', response.data)
        self.assertEqual(response.data['email'], 'management@test.com')
        
        # Verify user and management were created
        self.assertTrue(User.objects.filter(email='management@test.com').exists())
        self.assertTrue(Management.objects.filter(email='management@test.com').exists())


class ManagementLoginTestCase(APITestCase):
    def setUp(self):
        self.register_url = reverse('management-register')
        self.login_url = reverse('management-login')
        self.credentials = {
            'email': 'management@test.com',
            'password': 'TestPass123!',
            'password2': 'TestPass123!',
            'Management_name': 'Test Management'
        }
        # Register a management user
        self.client.post(self.register_url, self.credentials, format='json')

    def test_management_login_success(self):
        """Test successful management login"""
        response = self.client.post(self.login_url, {
            'email': 'management@test.com',
            'password': 'TestPass123!'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data['user_type'], 'management')


class UserTypeSeparationTestCase(APITestCase):
    """Test that users can only login through their correct user type endpoint"""
    
    def test_student_cannot_login_as_teacher(self):
        """Test that a student cannot login through teacher endpoint"""
        # Register a student
        student_register_url = reverse('student-register')
        student_data = {
            'email': 'student@test.com',
            'password': 'TestPass123!',
            'password2': 'TestPass123!',
            'student_name': 'Test Student',
            'student_rollNo': 'RFID001',
            'year': 1,
            'dept': 'CS',
            'section': 'A'
        }
        self.client.post(student_register_url, student_data, format='json')
        
        # Try to login as teacher
        teacher_login_url = reverse('teacher-login')
        response = self.client.post(teacher_login_url, {
            'email': 'student@test.com',
            'password': 'TestPass123!'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# ============ CRUD Tests for Models ============

class AuthenticatedAPITestCase(APITestCase):
    """Base class for authenticated API tests"""
    
    def setUp(self):
        # Create a user for authentication
        self.user = User.objects.create_user(
            username='testuser@test.com',
            email='testuser@test.com',
            password='TestPass123!'
        )
        self.client.force_authenticate(user=self.user)


class StudentCRUDTestCase(AuthenticatedAPITestCase):
    """Test CRUD operations for Student model"""
    
    def setUp(self):
        super().setUp()
        # Create a student for testing
        self.student = Student.objects.create(
            student_name='Test Student',
            email='student@test.com',
            student_rollNo='RFID001',
            year=1,
            dept='CS',
            section='A'
        )
        self.list_url = reverse('student-list')
        self.detail_url = reverse('student-detail', args=[self.student.student_id])
    
    def test_list_students(self):
        """Test listing all students"""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
    
    def test_retrieve_student(self):
        """Test retrieving a single student"""
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['student_name'], 'Test Student')
    
    def test_update_student(self):
        """Test updating a student"""
        data = {'student_name': 'Updated Student', 'email': 'updated@test.com', 'student_rollNo': 'RFID001', 'year': 2, 'dept': 'IT', 'section': 'B'}
        response = self.client.put(self.detail_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['student_name'], 'Updated Student')
    
    def test_partial_update_student(self):
        """Test partially updating a student"""
        data = {'student_name': 'Partially Updated'}
        response = self.client.patch(self.detail_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['student_name'], 'Partially Updated')
    
    def test_delete_student(self):
        """Test deleting a student"""
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Student.objects.filter(student_id=self.student.student_id).exists())
    
    def test_filter_students_by_year(self):
        """Test filtering students by year"""
        Student.objects.create(student_name='Year 2 Student', email='year2@test.com', student_rollNo='RFID002', year=2, dept='CS', section='A')
        response = self.client.get(self.list_url, {'year': 1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['year'], 1)


class TeacherCRUDTestCase(AuthenticatedAPITestCase):
    """Test CRUD operations for Teacher model"""
    
    def setUp(self):
        super().setUp()
        self.teacher = Teacher.objects.create(
            user=self.user,
            teacher_name='Test Teacher',
            email='teacher@test.com',
            teacher_rollNo='RFID001'
        )
        self.list_url = reverse('teacher-list')
        self.detail_url = reverse('teacher-detail', args=[self.teacher.teacher_id])
    
    def test_list_teachers(self):
        """Test listing all teachers"""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
    
    def test_retrieve_teacher(self):
        """Test retrieving a single teacher"""
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['teacher_name'], 'Test Teacher')
    
    def test_update_teacher(self):
        """Test updating a teacher"""
        data = {'teacher_name': 'Updated Teacher', 'email': 'updated@test.com', 'teacher_rollNo': 'RFID001'}
        response = self.client.put(self.detail_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['teacher_name'], 'Updated Teacher')
    
    def test_delete_teacher(self):
        """Test deleting a teacher"""
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class ManagementCRUDTestCase(AuthenticatedAPITestCase):
    """Test CRUD operations for Management model"""
    
    def setUp(self):
        super().setUp()
        self.management = Management.objects.create(
            Management_name='Test Management',
            email='management@test.com'
        )
        self.list_url = reverse('management-list')
        self.detail_url = reverse('management-detail', args=[self.management.Management_id])
    
    def test_list_management(self):
        """Test listing all management users"""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
    
    def test_retrieve_management(self):
        """Test retrieving a single management user"""
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['Management_name'], 'Test Management')
    
    def test_update_management(self):
        """Test updating a management user"""
        data = {'Management_name': 'Updated Management', 'email': 'updated@test.com'}
        response = self.client.put(self.detail_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['Management_name'], 'Updated Management')
    
    def test_delete_management(self):
        """Test deleting a management user"""
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class CourseCRUDTestCase(AuthenticatedAPITestCase):
    """Test CRUD operations for Course model"""
    
    def setUp(self):
        super().setUp()
        self.course = Course.objects.create(course_name='Test Course')
        self.list_url = reverse('course-list')
        self.detail_url = reverse('course-detail', args=[self.course.course_id])
    
    def test_list_courses(self):
        """Test listing all courses"""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
    
    def test_create_course(self):
        """Test creating a course"""
        data = {'course_name': 'New Course'}
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['course_name'], 'New Course')
    
    def test_retrieve_course(self):
        """Test retrieving a single course"""
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['course_name'], 'Test Course')
    
    def test_update_course(self):
        """Test updating a course"""
        data = {'course_name': 'Updated Course'}
        response = self.client.put(self.detail_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['course_name'], 'Updated Course')
    
    def test_delete_course(self):
        """Test deleting a course"""
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class ClassCRUDTestCase(AuthenticatedAPITestCase):
    """Test CRUD operations for Class model"""
    
    def setUp(self):
        super().setUp()
        self.classroom = Class.objects.create(scanner_id='SCANNER001')
        self.list_url = reverse('class-list')
        self.detail_url = reverse('class-detail', args=[self.classroom.classroom_id])
    
    def test_list_classes(self):
        """Test listing all classes"""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
    
    def test_create_class(self):
        """Test creating a class"""
        data = {'scanner_id': 'SCANNER002'}
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['scanner_id'], 'SCANNER002')
    
    def test_retrieve_class(self):
        """Test retrieving a single class"""
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['scanner_id'], 'SCANNER001')
    
    def test_update_class(self):
        """Test updating a class"""
        data = {'scanner_id': 'UPDATED_SCANNER'}
        response = self.client.put(self.detail_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['scanner_id'], 'UPDATED_SCANNER')
    
    def test_delete_class(self):
        """Test deleting a class"""
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class TaughtCourseCRUDTestCase(AuthenticatedAPITestCase):
    """Test CRUD operations for TaughtCourse model"""
    
    def setUp(self):
        super().setUp()
        self.management = Management.objects.create(
            user=self.user,
            Management_name='Scoped Management',
            email='scoped-management@test.com'
        )
        self.course = Course.objects.create(course_name='Test Course')
        self.teacher = Teacher.objects.create(
            teacher_name='Test Teacher',
            email='teacher@test.com',
            teacher_rollNo='RFID001',
            management=self.management,
        )
        self.taught_course = TaughtCourse.objects.create(
            course=self.course,
            teacher=self.teacher,
            classes_taken_count=2,
            section='A',
            year=1,
        )
        self.list_url = reverse('taughtcourse-list')
        self.detail_url = reverse('taughtcourse-detail', args=[self.taught_course.id])
    
    def test_list_taught_courses(self):
        """Test listing all taught courses"""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
    
    def test_create_taught_course(self):
        """Test creating a taught course"""
        new_teacher = Teacher.objects.create(
            teacher_name='New Teacher',
            email='new@test.com',
            teacher_rollNo='RFID002',
            management=self.management,
        )
        data = {
            'course': self.course.course_id,
            'teacher': new_teacher.teacher_id,
            'classes_taken_count': 1,
            'section': 'B',
            'year': 2,
        }
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
    def test_retrieve_taught_course(self):
        """Test retrieving a single taught course"""
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['course_name'], 'Test Course')
        self.assertEqual(response.data['teacher_name'], 'Test Teacher')
    
    def test_update_taught_course(self):
        """Test updating a taught course"""
        data = {
            'course': self.course.course_id,
            'teacher': self.teacher.teacher_id,
            'classes_taken_count': 2,
            'section': 'A',
            'year': 1,
        }
        response = self.client.put(self.detail_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['classes_taken_count'], 2)
    
    def test_delete_taught_course(self):
        """Test deleting a taught course"""
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
    
    def test_filter_by_teacher(self):
        """Test filtering taught courses by teacher"""
        response = self.client.get(self.list_url, {'teacher': self.teacher.teacher_id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)


class StudentCourseCRUDTestCase(AuthenticatedAPITestCase):
    """Test CRUD operations for StudentCourse model"""
    
    def setUp(self):
        super().setUp()
        self.management = Management.objects.create(
            user=self.user,
            Management_name='Student Course Management',
            email='student-course-management@test.com'
        )
        self.student = Student.objects.create(
            student_name='Test Student',
            email='student@test.com',
            student_rollNo='RFID001',
            year=1,
            dept='CS',
            section='A',
            management=self.management,
        )
        self.course = Course.objects.create(course_name='Test Course')
        self.teacher = Teacher.objects.create(
            teacher_name='Test Teacher',
            email='teacher@test.com',
            teacher_rollNo='RFID002',
            management=self.management,
        )
        self.student_course = StudentCourse.objects.create(
            student=self.student,
            course=self.course,
            teacher=self.teacher,
            classes_attended_count=1
        )
        self.list_url = reverse('studentcourse-list')
        self.detail_url = reverse('studentcourse-detail', args=[self.student_course.id])
    
    def test_list_student_courses(self):
        """Test listing all student courses"""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
    
    def test_create_student_course(self):
        """Test creating a student course"""
        new_student = Student.objects.create(
            student_name='New Student',
            email='new@test.com',
            student_rollNo='RFID003',
            year=2,
            dept='IT',
            section='B',
            management=self.management,
        )
        data = {'student': new_student.student_id, 'course': self.course.course_id, 'teacher': self.teacher.teacher_id, 'classes_attended_count': 1}
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
    def test_retrieve_student_course(self):
        """Test retrieving a single student course"""
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['student_name'], 'Test Student')
        self.assertEqual(response.data['course_name'], 'Test Course')
        self.assertEqual(response.data['teacher_name'], 'Test Teacher')
    
    def test_update_student_course(self):
        """Test updating a student course"""
        data = {'student': self.student.student_id, 'course': self.course.course_id, 'teacher': self.teacher.teacher_id, 'classes_attended_count': 2}
        response = self.client.put(self.detail_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['classes_attended_count'], 2)
    
    def test_delete_student_course(self):
        """Test deleting a student course"""
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
    
    def test_filter_by_student(self):
        """Test filtering student courses by student"""
        response = self.client.get(self.list_url, {'student': self.student.student_id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)


class UnauthenticatedAccessTestCase(APITestCase):
    """Test that CRUD endpoints require authentication"""
    
    def test_unauthenticated_access_denied(self):
        """Test that unauthenticated users cannot access CRUD endpoints"""
        endpoints = [
            reverse('student-list'),
            reverse('teacher-list'),
            reverse('management-list'),
            reverse('course-list'),
            reverse('class-list'),
            reverse('taughtcourse-list'),
            reverse('studentcourse-list'),
            reverse('updateattendancerequest-list'),
        ]
        for url in endpoints:
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class UpdateAttendanceRequestCRUDTestCase(AuthenticatedAPITestCase):
    """Test CRUD operations for UpdateAttendanceRequest model"""
    
    def setUp(self):
        super().setUp()
        self.management = Management.objects.create(
            user=self.user,
            email='mgmt@test.com',
            Management_name='Test Management'
        )
        # Create required related objects
        self.teacher = Teacher.objects.create(
            teacher_name='Test Teacher',
            email='teacher@test.com',
            teacher_rollNo='RFID001',
            management=self.management
        )
        self.student = Student.objects.create(
            student_name='Test Student',
            email='student@test.com',
            student_rollNo='RFID002',
            year=1,
            dept='CS',
            section='A',
            management=self.management
        )
        self.course = Course.objects.create(course_name='Test Course')
        
        # Create an update attendance request
        self.attendance_request = UpdateAttendanceRequest.objects.create(
            teacher=self.teacher,
            student=self.student,
            course=self.course,
            management=self.management,
            classes_to_add='Class A, Class B',
            reason='Student was marked absent by mistake'
        )
        
        self.list_url = reverse('updateattendancerequest-list')
        self.detail_url = reverse('updateattendancerequest-detail', args=[self.attendance_request.id])
    
    def test_list_update_attendance_requests(self):
        """Test listing all update attendance requests"""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
    
    def test_create_update_attendance_request(self):
        """Test creating an update attendance request"""
        new_student = Student.objects.create(
            student_name='New Student',
            email='new@test.com',
            student_rollNo='RFID003',
            year=2,
            dept='IT',
            section='B',
            management=self.management,
        )
        data = {
            'teacher_rollNo': self.teacher.teacher_rollNo,
            'student_rollNo': new_student.student_rollNo,
            'course': self.course.course_id,
            'classes_to_add': 'Class C',
            'reason': 'Late arrival registered'
        }
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['classes_to_add'], 'Class C')
        self.assertEqual(response.data['status'], 'pending')
        self.assertEqual(response.data['teacher_rollNo'], self.teacher.teacher_rollNo)
        self.assertEqual(response.data['student_rollNo'], new_student.student_rollNo)

    def test_create_update_attendance_request_accepts_course_code_and_slot_count(self):
        """Frontend can send course_code + slot_count (no classes_to_add, no teacher_rollNo)."""
        course = Course.objects.create(course_name='Algo', course_code='CS420')
        # Ensure there is a unique teacher assignment for inference.
        TaughtCourse.objects.create(
            teacher=self.teacher,
            course=course,
            section=self.student.section,
            year=self.student.year,
        )

        data = {
            'student_rollNo': self.student.student_rollNo,
            'course_code': 'CS420',
            'slot_count': 2,
            'attendanceType': 'regular',
            'reason': 'Late arrival',
            'program': self.student.dept,
            'section': self.student.section,
        }
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['teacher_rollNo'], self.teacher.teacher_rollNo)
        self.assertEqual(response.data['student_rollNo'], self.student.student_rollNo)
        self.assertEqual(response.data['course'], course.course_id)
        # classes_to_add should be synthesized from slot_count -> 2 entries.
        self.assertIn('Slot 1', response.data['classes_to_add'])
        self.assertIn('Slot 2', response.data['classes_to_add'])
    
    def test_retrieve_update_attendance_request(self):
        """Test retrieving a single update attendance request"""
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['teacher_name'], 'Test Teacher')
        self.assertEqual(response.data['student_name'], 'Test Student')
        self.assertEqual(response.data['course_name'], 'Test Course')
        self.assertEqual(response.data['status'], 'pending')
    
    def test_update_attendance_request(self):
        """Test updating an update attendance request"""
        data = {
            'teacher_rollNo': self.teacher.teacher_rollNo,
            'student_rollNo': self.student.student_rollNo,
            'course': self.course.course_id,
            'classes_to_add': 'Class D, Class E',
            'reason': 'Updated reason'
        }
        response = self.client.put(self.detail_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['classes_to_add'], 'Class D, Class E')
        self.assertEqual(response.data['reason'], 'Updated reason')
    
    def test_delete_update_attendance_request(self):
        """Test deleting an update attendance request"""
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(UpdateAttendanceRequest.objects.filter(id=self.attendance_request.id).exists())
    
    def test_filter_by_status(self):
        """Test filtering update attendance requests by status"""
        response = self.client.get(self.list_url, {'status': 'pending'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        
        response = self.client.get(self.list_url, {'status': 'approved'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)
    
    def test_filter_by_teacher(self):
        """Test filtering update attendance requests by teacher"""
        response = self.client.get(
            self.list_url,
            {'teacher_rollNo': self.teacher.teacher_rollNo, 'management_id': self.management.Management_id}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_filter_by_management_id_mismatch_returns_empty(self):
        """Management user cannot query another management's requests"""
        response = self.client.get(self.list_url, {'management_id': self.management.Management_id + 999})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_create_update_attendance_request_rejects_numeric_ids(self):
        """Test that roll number fields are required instead of numeric teacher/student ids"""
        data = {
            'teacher': self.teacher.teacher_id,
            'student': self.student.student_id,
            'course': self.course.course_id,
            'classes_to_add': 'Class Z',
            'reason': 'Should fail without roll number fields'
        }
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('student_rollNo', response.data)


class UpdateAttendanceRequestApproveRejectTestCase(APITestCase):
    """Test approve and reject functionality for UpdateAttendanceRequest"""
    
    def setUp(self):
        # Create management user for approving/rejecting
        self.management_user = User.objects.create_user(
            username='management@test.com',
            email='management@test.com',
            password='TestPass123!'
        )
        self.management = Management.objects.create(
            user=self.management_user,
            email='management@test.com',
            Management_name='Test Management'
        )
        
        # Create regular user (non-management)
        self.regular_user = User.objects.create_user(
            username='regular@test.com',
            email='regular@test.com',
            password='TestPass123!'
        )
        
        # Create required related objects
        self.teacher = Teacher.objects.create(
            teacher_name='Test Teacher',
            email='teacher@test.com',
            teacher_rollNo='RFID001',
            management=self.management,
        )
        self.student = Student.objects.create(
            student_name='Test Student',
            email='student@test.com',
            student_rollNo='RFID002',
            year=1,
            dept='CS',
            section='A',
            management=self.management,
        )
        self.course = Course.objects.create(course_name='Test Course')
        
        # Create an update attendance request
        self.attendance_request = UpdateAttendanceRequest.objects.create(
            teacher=self.teacher,
            student=self.student,
            course=self.course,
            management=self.management,
            classes_to_add='Class A, Class B',
            reason='Student was marked absent by mistake'
        )
        
        self.approve_url = reverse('updateattendancerequest-approve', args=[self.attendance_request.id])
        self.reject_url = reverse('updateattendancerequest-reject', args=[self.attendance_request.id])
    
    def test_approve_request_by_management(self):
        """Test that management can approve attendance requests"""
        self.client.force_authenticate(user=self.management_user)
        response = self.client.post(self.approve_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['request']['status'], 'approved')
        
        # Verify StudentCourse was created/updated
        student_course = StudentCourse.objects.get(
            student=self.student,
            course=self.course,
            teacher=self.teacher
        )
        self.assertEqual(student_course.classes_attended_count, 2)

        # Verify the request was deleted after processing
        self.assertFalse(UpdateAttendanceRequest.objects.filter(id=self.attendance_request.id).exists())
    
    def test_approve_request_updates_existing_attendance(self):
        """Test that approving a request updates existing attendance"""
        # Create existing StudentCourse
        student_course = StudentCourse.objects.create(
            student=self.student,
            course=self.course,
            teacher=self.teacher,
            classes_attended_count=1
        )
        
        self.client.force_authenticate(user=self.management_user)
        response = self.client.post(self.approve_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify attendance was appended
        student_course.refresh_from_db()
        self.assertEqual(student_course.classes_attended_count, 3)
    
    def test_reject_request_by_management(self):
        """Test that management can reject attendance requests"""
        self.client.force_authenticate(user=self.management_user)
        response = self.client.post(self.reject_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['request']['status'], 'rejected')
        
        # Verify no StudentCourse was created
        self.assertFalse(StudentCourse.objects.filter(
            student=self.student,
            course=self.course,
            teacher=self.teacher
        ).exists())

        # Verify the request was deleted after processing
        self.assertFalse(UpdateAttendanceRequest.objects.filter(id=self.attendance_request.id).exists())
    
    def test_non_management_cannot_approve(self):
        """Test that non-management users cannot approve requests"""
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.post(self.approve_url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Verify request was not changed
        self.attendance_request.refresh_from_db()
        self.assertEqual(self.attendance_request.status, 'pending')
    
    def test_non_management_cannot_reject(self):
        """Test that non-management users cannot reject requests"""
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.post(self.reject_url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Verify request was not changed
        self.attendance_request.refresh_from_db()
        self.assertEqual(self.attendance_request.status, 'pending')
    
    def test_cannot_approve_already_processed_request(self):
        """Test that already processed requests cannot be approved again"""
        # First approve the request
        self.client.force_authenticate(user=self.management_user)
        self.client.post(self.approve_url)
        
        # Try to approve again
        response = self.client.post(self.approve_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('not found', response.data['error'].lower())
    
    def test_cannot_reject_already_processed_request(self):
        """Test that already processed requests cannot be rejected"""
        # First reject the request
        self.client.force_authenticate(user=self.management_user)
        self.client.post(self.reject_url)
        
        # Try to reject again
        response = self.client.post(self.reject_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('not found', response.data['error'].lower())
    
    def test_unauthenticated_cannot_approve(self):
        """Test that unauthenticated users cannot approve requests"""
        response = self.client.post(self.approve_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_unauthenticated_cannot_reject(self):
        """Test that unauthenticated users cannot reject requests"""
        response = self.client.post(self.reject_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ============ Attendance Session Tests ============

class AttendanceSessionTestCase(APITestCase):
    """Test attendance session functionality"""
    
    def setUp(self):
        # Create authenticated user
        self.user = User.objects.create_user(
            username='teacher@test.com',
            email='teacher@test.com',
            password='TestPass123!'
        )
        self.teacher = Teacher.objects.create(
            user=self.user,
            teacher_name='Test Teacher',
            email='teacher@test.com',
            teacher_rollNo='RFID001'
        )
        self.course = Course.objects.create(course_name='Test Course')
        
        self.client.force_authenticate(user=self.user)
        
        self.session_url = reverse('attendancesession-list')
    
    def test_create_attendance_session(self):
        """Test creating/starting an attendance session"""
        data = {
            'teacher': self.teacher.teacher_id,
            'course': self.course.course_id,
            'section': 'A',
            'year': 1
        }
        response = self.client.post(self.session_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['session']['status'], 'active')
        self.assertIn('qr_code_token', response.data['session'])
        self.assertIsNotNone(response.data['session']['qr_code_token'])

    def test_create_attendance_session_accepts_extra_fields(self):
        """Session create should ignore extra frontend fields (geo/program/attendance_type)."""
        data = {
            'teacher': self.teacher.teacher_id,
            'course': self.course.course_id,
            'section': 'A',
            'year': 1,
            'slot_count': 2,
            'attendance_type': 'regular',
            'program': 'CS',
            'latitude': 24.93553388673033,
            'longitude': 67.0442592957783,
            'radius_meters': 50,
        }
        response = self.client.post(self.session_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['session']['slot_count'], 2)
        self.assertEqual(response.data['session']['status'], 'active')
    
    def test_list_attendance_sessions(self):
        """Test listing attendance sessions"""
        AttendanceSession.objects.create(
            teacher=self.teacher,
            course=self.course,
            section='A',
            year=1,
            qr_code_token='test_token_1'
        )
        
        response = self.client.get(self.session_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
    
    def test_stop_attendance_session(self):
        """Test stopping an active attendance session"""
        session = AttendanceSession.objects.create(
            teacher=self.teacher,
            course=self.course,
            section='A',
            year=1,
            qr_code_token='test_token_1',
            status='active'
        )
        
        stop_url = reverse('attendancesession-stop', args=[session.id])
        response = self.client.post(stop_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['session']['status'], 'stopped')
        self.assertIsNotNone(response.data['session']['stopped_at'])

    def test_stop_attendance_session_marks_absent_students(self):
        """Stopping a session should increment absent counts for students who did not attend."""
        student1 = Student.objects.create(
            student_name='Student 1',
            email='student1@test.com',
            student_rollNo='RFID101',
            year=1,
            dept='CS',
            section='A',
            management=self.teacher.management,
        )
        student2 = Student.objects.create(
            student_name='Student 2',
            email='student2@test.com',
            student_rollNo='RFID102',
            year=1,
            dept='CS',
            section='A',
            management=self.teacher.management,
        )

        present_course = StudentCourse.objects.create(
            student=student1,
            course=self.course,
            teacher=self.teacher,
            classes_attended_count=2,
            classes_absent_count=1,
        )
        absent_course = StudentCourse.objects.create(
            student=student2,
            course=self.course,
            teacher=self.teacher,
            classes_attended_count=0,
            classes_absent_count=0,
        )

        session = AttendanceSession.objects.create(
            teacher=self.teacher,
            course=self.course,
            section='A',
            year=1,
            slot_count=2,
            qr_code_token='test_token_absent',
            status='active'
        )

        AttendanceRecord.objects.create(
            session=session,
            student=student1,
            rfid_scanned=True,
            qr_scanned=True,
            is_present=True,
        )

        stop_url = reverse('attendancesession-stop', args=[session.id])
        response = self.client.post(stop_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        present_course.refresh_from_db()
        absent_course.refresh_from_db()

        self.assertEqual(present_course.classes_absent_count, 1)
        self.assertEqual(absent_course.classes_absent_count, 2)
    
    def test_cannot_stop_already_stopped_session(self):
        """Test that already stopped sessions cannot be stopped again"""
        session = AttendanceSession.objects.create(
            teacher=self.teacher,
            course=self.course,
            section='A',
            year=1,
            qr_code_token='test_token_1',
            status='stopped'
        )
        
        stop_url = reverse('attendancesession-stop', args=[session.id])
        response = self.client.post(stop_url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_get_qr_code(self):
        """Test getting QR code for an active session"""
        session = AttendanceSession.objects.create(
            teacher=self.teacher,
            course=self.course,
            section='A',
            year=1,
            qr_code_token='test_token_1',
            status='active'
        )
        
        qr_url = reverse('attendancesession-qr', args=[session.id])
        response = self.client.get(qr_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('qr_code', response.data)
        self.assertIn('qr_token', response.data)
        self.assertIn('data:image/png;base64,', response.data['qr_code'])
    
    def test_cannot_get_qr_for_stopped_session(self):
        """Test that QR code cannot be generated for stopped sessions"""
        session = AttendanceSession.objects.create(
            teacher=self.teacher,
            course=self.course,
            section='A',
            year=1,
            qr_code_token='test_token_1',
            status='stopped'
        )
        
        qr_url = reverse('attendancesession-qr', args=[session.id])
        response = self.client.get(qr_url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_filter_sessions_by_teacher(self):
        """Test filtering sessions by teacher"""
        other_teacher = Teacher.objects.create(
            teacher_name='Other Teacher',
            email='other@test.com',
            teacher_rollNo='RFID002'
        )
        
        AttendanceSession.objects.create(
            teacher=self.teacher,
            course=self.course,
            section='A',
            year=1,
            qr_code_token='test_token_1'
        )
        
        AttendanceSession.objects.create(
            teacher=other_teacher,
            course=self.course,
            section='B',
            year=2,
            qr_code_token='test_token_2'
        )
        
        response = self.client.get(self.session_url, {'teacher': self.teacher.teacher_id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['teacher'], self.teacher.teacher_id)


class RFIDScanTestCase(APITestCase):
    """Test RFID scanning functionality"""
    
    def setUp(self):
        self.teacher = Teacher.objects.create(
            teacher_name='Test Teacher',
            email='teacher@test.com',
            teacher_rollNo='RFID001'
        )
        self.course = Course.objects.create(course_name='Test Course')
        self.student = Student.objects.create(
            student_name='Test Student',
            email='student@test.com',
            student_rollNo='RFID_STUDENT_1',
            year=1,
            dept='CS',
            section='A'
        )
        self.session = AttendanceSession.objects.create(
            teacher=self.teacher,
            course=self.course,
            section='A',
            year=1,
            qr_code_token='test_token_1',
            status='active'
        )
        
        self.rfid_scan_url = reverse('rfid-scan')
    
    def test_rfid_scan_success(self):
        """Test successful RFID scan"""
        data = {
            'rfid': 'RFID_STUDENT_1',
            'session_id': self.session.id
        }
        response = self.client.post(self.rfid_scan_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['rfid_scanned'])
        self.assertFalse(response.data['qr_scanned'])
        self.assertFalse(response.data['is_present'])
        self.assertTrue(response.data['needs_qr'])
        
        # Verify record was created
        record = AttendanceRecord.objects.get(session=self.session, student=self.student)
        self.assertTrue(record.rfid_scanned)
        self.assertFalse(record.qr_scanned)
        self.assertFalse(record.is_present)
    
    def test_rfid_scan_invalid_student(self):
        """Test RFID scan with invalid student RFID"""
        data = {
            'rfid': 'INVALID_RFID',
            'session_id': self.session.id
        }
        response = self.client.post(self.rfid_scan_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_rfid_scan_inactive_session(self):
        """Test RFID scan on inactive session"""
        self.session.status = 'stopped'
        self.session.save()
        
        data = {
            'rfid': 'RFID_STUDENT_1',
            'session_id': self.session.id
        }
        response = self.client.post(self.rfid_scan_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_rfid_scan_wrong_section(self):
        """Test RFID scan with student from different section"""
        self.student.section = 'B'
        self.student.save()
        
        data = {
            'rfid': 'RFID_STUDENT_1',
            'session_id': self.session.id
        }
        response = self.client.post(self.rfid_scan_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class QRScanTestCase(APITestCase):
    """Test QR code scanning functionality"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='student@test.com',
            email='student@test.com',
            password='TestPass123!'
        )
        self.teacher = Teacher.objects.create(
            teacher_name='Test Teacher',
            email='teacher@test.com',
            teacher_rollNo='RFID001'
        )
        self.course = Course.objects.create(course_name='Test Course')
        self.student = Student.objects.create(
            user=self.user,
            student_name='Test Student',
            email='student@test.com',
            student_rollNo='RFID_STUDENT_1',
            year=1,
            dept='CS',
            section='A'
        )
        self.session = AttendanceSession.objects.create(
            teacher=self.teacher,
            course=self.course,
            section='A',
            year=1,
            qr_code_token='test_token_1',
            slot_count=2,
            latitude=24.93553388673033,
            longitude=67.0442592957783,
            radius_meters=50,
            status='active'
        )
        
        self.client.force_authenticate(user=self.user)
        self.qr_scan_url = reverse('qr-scan')
    
    def test_qr_scan_success(self):
        """Test successful QR scan"""
        data = {
            'qr_token': 'test_token_1',
            'student_id': self.student.student_id,
            'latitude': 24.93553388673033,
            'longitude': 67.0442592957783,
        }
        response = self.client.post(self.qr_scan_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['rfid_scanned'])
        self.assertTrue(response.data['qr_scanned'])
        self.assertFalse(response.data['is_present'])
        self.assertTrue(response.data['needs_rfid'])
        
        # Verify record was created
        record = AttendanceRecord.objects.get(session=self.session, student=self.student)
        self.assertFalse(record.rfid_scanned)
        self.assertTrue(record.qr_scanned)
        self.assertFalse(record.is_present)
    
    def test_qr_scan_invalid_token(self):
        """Test QR scan with invalid token"""
        data = {
            'qr_token': 'invalid_token',
            'student_id': self.student.student_id,
            'latitude': 24.93553388673033,
            'longitude': 67.0442592957783,
        }
        response = self.client.post(self.qr_scan_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_qr_scan_inactive_session(self):
        """Test QR scan on inactive session"""
        self.session.status = 'stopped'
        self.session.save()
        
        data = {
            'qr_token': 'test_token_1',
            'student_id': self.student.student_id,
            'latitude': 24.93553388673033,
            'longitude': 67.0442592957783,
        }
        response = self.client.post(self.qr_scan_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_qr_scan_outside_radius_rejected(self):
        """QR scan should be rejected when device is outside session radius."""
        data = {
            'qr_token': 'test_token_1',
            'student_id': self.student.student_id,
            # ~111m away east/west (approx) which exceeds 50m
            'latitude': 24.93553388673033,
            'longitude': 67.0452592957783,
        }
        response = self.client.post(self.qr_scan_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Outside', response.data.get('error', ''))

    @override_settings(ATTENDANCE_REQUIRE_RFID=False)
    def test_qr_only_marks_present_when_rfid_not_required(self):
        """When 2FA is disabled, a QR scan alone should mark the student present."""
        data = {
            'qr_token': 'test_token_1',
            'student_id': self.student.student_id,
            'latitude': 24.93553388673033,
            'longitude': 67.0442592957783,
        }
        response = self.client.post(self.qr_scan_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_present'])

        # Re-scan should not add more attendance for the same session.
        response2 = self.client.post(self.qr_scan_url, data, format='json')
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertTrue(response2.data['is_present'])

        student_course = StudentCourse.objects.get(student=self.student, course=self.course, teacher=self.teacher)
        self.assertEqual(student_course.classes_attended_count, 2)


class TwoFactorAttendanceTestCase(APITestCase):
    """Test 2FA attendance (RFID + QR)"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='student@test.com',
            email='student@test.com',
            password='TestPass123!'
        )
        self.teacher = Teacher.objects.create(
            teacher_name='Test Teacher',
            email='teacher@test.com',
            teacher_rollNo='RFID001'
        )
        self.course = Course.objects.create(course_name='Test Course')
        self.student = Student.objects.create(
            user=self.user,
            student_name='Test Student',
            email='student@test.com',
            student_rollNo='RFID_STUDENT_1',
            year=1,
            dept='CS',
            section='A'
        )
        self.session = AttendanceSession.objects.create(
            teacher=self.teacher,
            course=self.course,
            section='A',
            year=1,
            qr_code_token='test_token_1',
            slot_count=2,
            latitude=24.93553388673033,
            longitude=67.0442592957783,
            radius_meters=50,
            status='active'
        )
        
        self.client.force_authenticate(user=self.user)
        self.rfid_scan_url = reverse('rfid-scan')
        self.qr_scan_url = reverse('qr-scan')
    
    def test_both_scans_marks_present(self):
        """Test that both RFID and QR scans mark student as present"""
        # First scan RFID
        rfid_data = {
            'rfid': 'RFID_STUDENT_1',
            'session_id': self.session.id
        }
        rfid_response = self.client.post(self.rfid_scan_url, rfid_data, format='json')
        self.assertEqual(rfid_response.status_code, status.HTTP_200_OK)
        self.assertFalse(rfid_response.data['is_present'])
        
        # Then scan QR
        qr_data = {
            'qr_token': 'test_token_1',
            'student_id': self.student.student_id,
            'latitude': 24.93553388673033,
            'longitude': 67.0442592957783,
        }
        qr_response = self.client.post(self.qr_scan_url, qr_data, format='json')
        self.assertEqual(qr_response.status_code, status.HTTP_200_OK)
        self.assertTrue(qr_response.data['is_present'])
        
        # Verify record shows present
        record = AttendanceRecord.objects.get(session=self.session, student=self.student)
        self.assertTrue(record.rfid_scanned)
        self.assertTrue(record.qr_scanned)
        self.assertTrue(record.is_present)
        self.assertIsNotNone(record.marked_present_at)
        
        # Verify StudentCourse was updated
        student_course = StudentCourse.objects.get(
            student=self.student,
            course=self.course,
            teacher=self.teacher
        )
        self.assertEqual(student_course.classes_attended_count, 2)

        # Scanning again should not add more attendance for the same session.
        qr_data = {
            'qr_token': 'test_token_1',
            'student_id': self.student.student_id,
            'latitude': 24.93553388673033,
            'longitude': 67.0442592957783,
        }
        qr_response2 = self.client.post(self.qr_scan_url, qr_data, format='json')
        self.assertEqual(qr_response2.status_code, status.HTTP_200_OK)
        self.assertTrue(qr_response2.data['is_present'])
        student_course.refresh_from_db()
        self.assertEqual(student_course.classes_attended_count, 2)
    
    def test_qr_then_rfid_marks_present(self):
        """Test that scanning QR first then RFID also marks present"""
        # First scan QR
        qr_data = {
            'qr_token': 'test_token_1',
            'student_id': self.student.student_id,
            'latitude': 24.93553388673033,
            'longitude': 67.0442592957783,
        }
        qr_response = self.client.post(self.qr_scan_url, qr_data, format='json')
        self.assertEqual(qr_response.status_code, status.HTTP_200_OK)
        self.assertFalse(qr_response.data['is_present'])
        
        # Then scan RFID
        rfid_data = {
            'rfid': 'RFID_STUDENT_1',
            'session_id': self.session.id
        }
        rfid_response = self.client.post(self.rfid_scan_url, rfid_data, format='json')
        self.assertEqual(rfid_response.status_code, status.HTTP_200_OK)
        self.assertTrue(rfid_response.data['is_present'])
        
        # Verify record shows present
        record = AttendanceRecord.objects.get(session=self.session, student=self.student)
        self.assertTrue(record.is_present)
    
    def test_only_rfid_does_not_mark_present(self):
        """Test that only RFID scan does not mark student as present"""
        rfid_data = {
            'rfid': 'RFID_STUDENT_1',
            'session_id': self.session.id
        }
        response = self.client.post(self.rfid_scan_url, rfid_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['is_present'])
        
        # Verify no StudentCourse was created
        self.assertFalse(StudentCourse.objects.filter(
            student=self.student,
            course=self.course,
            teacher=self.teacher
        ).exists())
    
    def test_only_qr_does_not_mark_present(self):
        """Test that only QR scan does not mark student as present"""
        qr_data = {
            'qr_token': 'test_token_1',
            'student_id': self.student.student_id,
            'latitude': 24.93553388673033,
            'longitude': 67.0442592957783,
        }
        response = self.client.post(self.qr_scan_url, qr_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['is_present'])
        
        # Verify no StudentCourse was created
        self.assertFalse(StudentCourse.objects.filter(
            student=self.student,
            course=self.course,
            teacher=self.teacher
        ).exists())
    
    def test_neither_scan_no_attendance(self):
        """Test that no scans means no attendance record"""
        # Verify no record exists
        self.assertFalse(AttendanceRecord.objects.filter(
            session=self.session,
            student=self.student
        ).exists())


class AttendanceSessionStatisticsTestCase(APITestCase):
    """Test attendance statistics endpoint"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='teacher@test.com',
            email='teacher@test.com',
            password='TestPass123!'
        )
        self.teacher = Teacher.objects.create(
            user=self.user,
            teacher_name='Test Teacher',
            email='teacher@test.com',
            teacher_rollNo='RFID001'
        )
        self.course = Course.objects.create(course_name='Test Course')
        self.session = AttendanceSession.objects.create(
            teacher=self.teacher,
            course=self.course,
            section='A',
            year=1,
            qr_code_token='test_token_1',
            status='active'
        )
        
        # Create students
        self.student1 = Student.objects.create(
            student_name='Student 1',
            email='student1@test.com',
            student_rollNo='RFID_1',
            year=1, dept='CS', section='A'
        )
        self.student2 = Student.objects.create(
            student_name='Student 2',
            email='student2@test.com',
            student_rollNo='RFID_2',
            year=1, dept='CS', section='A'
        )
        self.student3 = Student.objects.create(
            student_name='Student 3',
            email='student3@test.com',
            student_rollNo='RFID_3',
            year=1, dept='CS', section='A'
        )
        
        self.client.force_authenticate(user=self.user)
    
    def test_attendance_statistics(self):
        """Test getting attendance statistics for a session"""
        # Create different attendance scenarios
        # Student 1: Both RFID and QR (present)
        AttendanceRecord.objects.create(
            session=self.session,
            student=self.student1,
            rfid_scanned=True,
            qr_scanned=True,
            is_present=True
        )
        
        # Student 2: Only RFID (not present)
        AttendanceRecord.objects.create(
            session=self.session,
            student=self.student2,
            rfid_scanned=True,
            qr_scanned=False,
            is_present=False
        )
        
        # Student 3: Only QR (not present)
        AttendanceRecord.objects.create(
            session=self.session,
            student=self.student3,
            rfid_scanned=False,
            qr_scanned=True,
            is_present=False
        )
        
        attendance_url = reverse('attendancesession-attendance', args=[self.session.id])
        response = self.client.get(attendance_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['statistics']['total_students'], 3)
        self.assertEqual(response.data['statistics']['present'], 1)
        self.assertEqual(response.data['statistics']['absent'], 2)
        self.assertEqual(response.data['statistics']['rfid_only'], 1)
        self.assertEqual(response.data['statistics']['qr_only'], 1)




# ============ Tests for Unified Frontend-Compatible Endpoints ============

class UnifiedLoginTestCase(APITestCase):
    """Tests for POST /api/login – the unified login endpoint consumed by the frontend."""

    def setUp(self):
        self.url = reverse('unified-login')

        # Create a student
        self.student_user = User.objects.create_user(
            username='stu@test.com', email='stu@test.com', password='Pass123!'
        )
        self.student = Student.objects.create(
            user=self.student_user, email='stu@test.com',
            student_name='Test Student', student_rollNo='RFID_STU',
            year=1, dept='CS', section='A'
        )

        # Create a teacher
        self.teacher_user = User.objects.create_user(
            username='tch@test.com', email='tch@test.com', password='Pass123!'
        )
        self.teacher = Teacher.objects.create(
            user=self.teacher_user, email='tch@test.com',
            teacher_name='Test Teacher', teacher_rollNo='RFID_TCH'
        )

        # Create a management (admin) user
        self.admin_user = User.objects.create_user(
            username='adm@test.com', email='adm@test.com', password='Pass123!'
        )
        self.management = Management.objects.create(
            user=self.admin_user, email='adm@test.com',
            Management_name='Test Admin'
        )

    def test_student_login_with_role(self):
        """Frontend sends { email, password, role: 'student' }"""
        response = self.client.post(self.url, {
            'email': 'stu@test.com',
            'password': 'Pass123!',
            'role': 'student',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertEqual(response.data['user_type'], 'student')
        self.assertEqual(response.data['email'], 'stu@test.com')

    def test_teacher_login_with_role(self):
        """Frontend sends { email, password, role: 'teacher' }"""
        response = self.client.post(self.url, {
            'email': 'tch@test.com',
            'password': 'Pass123!',
            'role': 'teacher',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user_type'], 'teacher')

    def test_admin_login_with_role(self):
        """Frontend sends { email, password, role: 'admin' } – maps to Management"""
        response = self.client.post(self.url, {
            'email': 'adm@test.com',
            'password': 'Pass123!',
            'role': 'admin',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user_type'], 'admin')

    def test_wrong_password(self):
        response = self.client.post(self.url, {
            'email': 'stu@test.com',
            'password': 'WrongPass!',
            'role': 'student',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_wrong_role_for_user(self):
        """Student credentials used with role='teacher' should return 404"""
        response = self.client.post(self.url, {
            'email': 'stu@test.com',
            'password': 'Pass123!',
            'role': 'teacher',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_missing_email(self):
        response = self.client.post(self.url, {
            'password': 'Pass123!',
            'role': 'student',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_role(self):
        response = self.client.post(self.url, {
            'email': 'stu@test.com',
            'password': 'Pass123!',
            'role': 'superuser',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class UnifiedSignupTestCase(APITestCase):
    """Tests for POST /api/signup – the unified signup endpoint consumed by the frontend."""

    def setUp(self):
        self.url = reverse('unified-signup')

    def test_signup_student_with_frontend_fields(self):
        """Admin panel registers a student using frontend field names."""
        response = self.client.post(self.url, {
            'role': 'student',
            'name': 'New Student',
            'email': 'newstudent@test.com',
            'password': 'Pass123!',
            'id': 'ROLL001',
            'year': '2',
            'program': 'CS',
            'section': 'B',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['user_type'], 'student')
        self.assertTrue(Student.objects.filter(email='newstudent@test.com').exists())
        student = Student.objects.get(email='newstudent@test.com')
        self.assertEqual(student.student_name, 'New Student')
        self.assertEqual(student.student_rollNo, 'ROLL001')
        self.assertEqual(student.year, 2)
        self.assertEqual(student.dept, 'CS')

    def test_signup_student_without_optional_fields(self):
        """Student registration without section/program uses sensible defaults."""
        response = self.client.post(self.url, {
            'role': 'student',
            'name': 'Min Student',
            'email': 'minstudent@test.com',
            'password': 'Pass123!',
            'id': 'ROLL002',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        student = Student.objects.get(email='minstudent@test.com')
        self.assertEqual(student.section, 'A')  # default

    def test_signup_teacher_with_frontend_fields(self):
        """Admin panel registers a teacher using frontend field names."""
        response = self.client.post(self.url, {
            'role': 'teacher',
            'name': 'New Teacher',
            'email': 'newteacher@test.com',
            'password': 'Pass123!',
            'id': 'TCH001',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['user_type'], 'teacher')
        self.assertTrue(Teacher.objects.filter(email='newteacher@test.com').exists())

    def test_signup_admin(self):
        """Admin (management) signup from SignUp.jsx."""
        response = self.client.post(self.url, {
            'role': 'admin',
            'name': 'New Admin',
            'email': 'newadmin@test.com',
            'password': 'Pass123!',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['user_type'], 'admin')
        self.assertTrue(Management.objects.filter(email='newadmin@test.com').exists())

    def test_duplicate_email(self):
        self.client.post(self.url, {
            'role': 'student',
            'name': 'A', 'email': 'dup@test.com',
            'password': 'Pass123!', 'id': 'X1',
        }, format='json')
        response = self.client.post(self.url, {
            'role': 'student',
            'name': 'B', 'email': 'dup@test.com',
            'password': 'Pass123!', 'id': 'X2',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_required_fields(self):
        response = self.client.post(self.url, {
            'role': 'student',
            'email': 'incomplete@test.com',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class UserDetailsTestCase(APITestCase):
    """Tests for GET /api/user-details – returns current user's profile."""

    def setUp(self):
        self.url = reverse('user-details')
        self.user = User.objects.create_user(
            username='me@test.com', email='me@test.com', password='Pass123!'
        )
        self.student = Student.objects.create(
            user=self.user, email='me@test.com',
            student_name='Me Student', student_rollNo='RFID_ME',
            year=3, dept='IT', section='C'
        )

    def test_authenticated_user_gets_profile(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['role'], 'student')
        self.assertEqual(response.data['name'], 'Me Student')
        self.assertEqual(response.data['email'], 'me@test.com')

    def test_unauthenticated_user_denied(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class UserLogoutTestCase(APITestCase):
    """Tests for GET /api/user-logout."""

    def setUp(self):
        self.url = reverse('user-logout')
        self.user = User.objects.create_user(
            username='bye@test.com', email='bye@test.com', password='Pass123!'
        )

    def test_authenticated_logout(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)

    def test_unauthenticated_logout_denied(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ============ Tests for Student Registration with Courses ============

class StudentRegistrationWithCoursesTestCase(APITestCase):
    """Tests for course handling in the unified student registration endpoint."""

    def setUp(self):
        self.url = reverse('unified-signup')

    def test_student_signup_with_courses_creates_course_objects(self):
        """Courses field 'CS301: Database, CS401: Algo' should create Course objects."""
        response = self.client.post(self.url, {
            'role': 'student',
            'name': 'Course Student',
            'email': 'cstudent@test.com',
            'password': 'Pass123!',
            'id': 'ROLL_CS',
            'year': '2',
            'program': 'CS',
            'courses': 'CS301: Database Management, CS401: Distributed Systems',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data['courses']), 2)
        # Verify Course objects were created
        from core.models import Course
        self.assertTrue(Course.objects.filter(course_code='CS301').exists())
        self.assertTrue(Course.objects.filter(course_code='CS401').exists())

    def test_student_signup_without_courses(self):
        """Student signup without courses should still succeed."""
        response = self.client.post(self.url, {
            'role': 'student',
            'name': 'NoCourse Student',
            'email': 'nocourse@test.com',
            'password': 'Pass123!',
            'id': 'ROLL_NC',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['courses'], [])

    def test_student_signup_reuses_existing_course(self):
        """Registering two students with the same course code doesn't create duplicates."""
        from core.models import Course
        Course.objects.create(course_code='CS501', course_name='Algorithms')

        self.client.post(self.url, {
            'role': 'student',
            'name': 'First Student',
            'email': 's1@test.com',
            'password': 'Pass123!',
            'id': 'ROLL_S1',
            'courses': 'CS501: Algorithms',
        }, format='json')
        # Only one CS501 course should exist
        self.assertEqual(Course.objects.filter(course_code='CS501').count(), 1)


# ============ Tests for Teacher Registration with Phone/Years/Programs/Courses ============

class TeacherRegistrationFullDataTestCase(APITestCase):
    """Tests for phone, years, programs, courses in teacher registration."""

    def setUp(self):
        self.url = reverse('unified-signup')

    def test_teacher_signup_saves_phone_years_programs(self):
        """Teacher signup should persist phone, years, programs."""
        response = self.client.post(self.url, {
            'role': 'teacher',
            'name': 'Prof. Ahmad',
            'email': 'ahmad@test.com',
            'password': 'Pass123!',
            'id': 'TCH_AHMAD',
            'phone': '03001234567',
            'years': '1,2',
            'programs': 'CS,IT',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['phone'], '03001234567')
        self.assertEqual(response.data['years'], '1,2')
        self.assertEqual(response.data['programs'], 'CS,IT')
        # Verify in DB
        from core.models import Teacher
        t = Teacher.objects.get(email='ahmad@test.com')
        self.assertEqual(t.phone, '03001234567')
        self.assertEqual(t.years, '1,2')
        self.assertEqual(t.programs, 'CS,IT')

    def test_teacher_signup_with_courses_creates_taught_courses(self):
        """Teacher signup with courses should create Course + TaughtCourse objects."""
        from core.models import TaughtCourse
        response = self.client.post(self.url, {
            'role': 'teacher',
            'name': 'Dr. Khan',
            'email': 'khan@test.com',
            'password': 'Pass123!',
            'id': 'TCH_KHAN',
            'courses': 'CS601: Compiler Design, CS701: AI',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data['courses']), 2)
        from core.models import Teacher
        teacher = Teacher.objects.get(email='khan@test.com')
        self.assertEqual(TaughtCourse.objects.filter(teacher=teacher).count(), 2)

    def test_teacher_signup_without_optional_fields(self):
        """Teacher signup without phone/years/programs should use defaults."""
        response = self.client.post(self.url, {
            'role': 'teacher',
            'name': 'Basic Teacher',
            'email': 'basic@test.com',
            'password': 'Pass123!',
            'id': 'TCH_BASIC',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['phone'], '')
        self.assertEqual(response.data['years'], '')
        self.assertEqual(response.data['programs'], '')


# ============ Tests for Student Filtering via Backend ============

class StudentFilterTestCase(APITestCase):
    """Tests for GET /api/students/?year=X&program=Y filtering."""

    def setUp(self):
        self.user = User.objects.create_user(username='admin_u', password='Pass123!')
        self.client.force_authenticate(user=self.user)

        Student.objects.create(student_name='Alice', student_rollNo='A001', year=1, dept='CS', section='A', email='alice@t.com')
        Student.objects.create(student_name='Bob',   student_rollNo='B001', year=1, dept='IT', section='A', email='bob@t.com')
        Student.objects.create(student_name='Carol', student_rollNo='C001', year=2, dept='CS', section='B', email='carol@t.com')

    def test_filter_by_year(self):
        response = self.client.get('/api/students/?year=1')
        self.assertEqual(response.status_code, 200)
        names = [s['student_name'] for s in response.data]
        self.assertIn('Alice', names)
        self.assertIn('Bob', names)
        self.assertNotIn('Carol', names)

    def test_filter_by_program(self):
        """Frontend sends 'program'; backend maps it to 'dept'."""
        response = self.client.get('/api/students/?program=CS')
        self.assertEqual(response.status_code, 200)
        names = [s['student_name'] for s in response.data]
        self.assertIn('Alice', names)
        self.assertIn('Carol', names)
        self.assertNotIn('Bob', names)

    def test_filter_by_year_and_program(self):
        response = self.client.get('/api/students/?year=1&program=CS')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['student_name'], 'Alice')

    def test_response_includes_program_alias(self):
        """StudentSerializer must return a 'program' field (alias for dept)."""
        response = self.client.get('/api/students/?year=1&program=CS')
        self.assertEqual(response.status_code, 200)
        self.assertIn('program', response.data[0])
        self.assertEqual(response.data[0]['program'], 'CS')


class StudentFilterOptionsTestCase(APITestCase):
    """Tests for GET /api/students/filter-options/ within a management."""

    def setUp(self):
        self.url = reverse('student-filter-options')
        self.user = User.objects.create_user(username='filter_admin', password='Pass123!')
        self.client.force_authenticate(user=self.user)
        self.management = Management.objects.create(
            user=self.user,
            Management_name='Filter Management',
            email='filter_admin@test.com'
        )

        Student.objects.create(
            student_name='Alice', student_rollNo='FA001', year=1, dept='CS', section='A', email='alice_filter@t.com',
            management=self.management,
        )
        Student.objects.create(
            student_name='Bob', student_rollNo='FB001', year=2, dept='IT', section='A', email='bob_filter@t.com',
            management=self.management,
        )
        Student.objects.create(
            student_name='Carol', student_rollNo='FC001', year=1, dept='CS', section='B', email='carol_filter@t.com',
            management=self.management,
        )

        other_user = User.objects.create_user(username='other_filter_admin', password='Pass123!')
        other_management = Management.objects.create(
            user=other_user,
            Management_name='Other Filter Management',
            email='other_filter_admin@test.com'
        )
        Student.objects.create(
            student_name='Hidden', student_rollNo='FH001', year=4, dept='SE', section='A', email='hidden_filter@t.com',
            management=other_management,
        )

    def test_returns_unique_years_and_departments_for_management(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['years'], [1, 2])
        self.assertEqual(response.data['departments'], ['CS', 'IT'])
        self.assertEqual(response.data['programs'], ['CS', 'IT'])

    def test_non_management_user_gets_403(self):
        self.client.force_authenticate(user=User.objects.create_user(username='plain_user', password='Pass123!'))
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)


class TeacherFilterOptionsTestCase(APITestCase):
    """Tests for GET /api/teachers/filter-options/ within a management."""

    def setUp(self):
        self.url = reverse('teacher-filter-options')
        self.user = User.objects.create_user(username='teacher_filter_admin', password='Pass123!')
        self.client.force_authenticate(user=self.user)
        self.management = Management.objects.create(
            user=self.user,
            Management_name='Teacher Filter Management',
            email='teacher_filter_admin@test.com'
        )

        Teacher.objects.create(
            teacher_name='Prof. Smith', teacher_rollNo='TF001', years='1,2', programs='CS,IT', email='smith_filter@t.com',
            management=self.management,
        )
        Teacher.objects.create(
            teacher_name='Dr. Jones', teacher_rollNo='TF002', years='2,4', programs='IT,DS', email='jones_filter@t.com',
            management=self.management,
        )
        Teacher.objects.create(
            teacher_name='Mr. Ali', teacher_rollNo='TF003', years='1', programs='CS', email='ali_filter@t.com',
            management=self.management,
        )

        other_user = User.objects.create_user(username='other_teacher_filter_admin', password='Pass123!')
        other_management = Management.objects.create(
            user=other_user,
            Management_name='Other Teacher Filter Management',
            email='other_teacher_filter_admin@test.com'
        )
        Teacher.objects.create(
            teacher_name='Hidden Prof', teacher_rollNo='TF004', years='5', programs='SE', email='hidden_filter@t.com',
            management=other_management,
        )

    def test_returns_unique_years_and_programs_for_management(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['years'], [1, 2, 4])
        self.assertEqual(response.data['programs'], ['CS', 'DS', 'IT'])

    def test_non_management_user_gets_403(self):
        self.client.force_authenticate(user=User.objects.create_user(username='plain_teacher_user', password='Pass123!'))
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)


# ============ Tests for Teacher Filtering via Backend ============

class TeacherFilterTestCase(APITestCase):
    """Tests for GET /api/teachers/?year=X&program=Y filtering."""

    def setUp(self):
        self.user = User.objects.create_user(username='admin_t', password='Pass123!')
        self.client.force_authenticate(user=self.user)

        Teacher.objects.create(teacher_name='Prof. Smith', teacher_rollNo='TS01', years='1,2', programs='CS,IT', email='smith@t.com')
        Teacher.objects.create(teacher_name='Dr. Jones',   teacher_rollNo='TJ01', years='3,4', programs='IT,DS', email='jones@t.com')
        Teacher.objects.create(teacher_name='Mr. Ali',     teacher_rollNo='TA01', years='1',   programs='CS',    email='ali@t.com')

    def test_filter_by_year(self):
        response = self.client.get('/api/teachers/?year=1')
        self.assertEqual(response.status_code, 200)
        names = [t['teacher_name'] for t in response.data]
        self.assertIn('Prof. Smith', names)
        self.assertIn('Mr. Ali', names)
        self.assertNotIn('Dr. Jones', names)

    def test_filter_by_program(self):
        response = self.client.get('/api/teachers/?program=DS')
        self.assertEqual(response.status_code, 200)
        names = [t['teacher_name'] for t in response.data]
        self.assertIn('Dr. Jones', names)
        self.assertNotIn('Prof. Smith', names)

    def test_filter_by_year_and_program(self):
        response = self.client.get('/api/teachers/?year=1&program=CS')
        self.assertEqual(response.status_code, 200)
        names = [t['teacher_name'] for t in response.data]
        self.assertIn('Prof. Smith', names)
        self.assertIn('Mr. Ali', names)
        self.assertNotIn('Dr. Jones', names)

    def test_response_includes_phone_years_programs(self):
        """TeacherSerializer must return phone, years, programs."""
        response = self.client.get('/api/teachers/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('phone', response.data[0])
        self.assertIn('years', response.data[0])
        self.assertIn('programs', response.data[0])


# ============ Tests for Attendance Summary Endpoints ============

class StudentAttendanceSummaryTestCase(APITestCase):
    """Tests for GET /api/attendance/student/?student_rollNo=X"""

    def setUp(self):
        self.url = reverse('attendance-student-summary')
        self.user = User.objects.create_user(username='mgmt_att', password='Pass123!')
        self.client.force_authenticate(user=self.user)
        self.management = Management.objects.create(
            user=self.user,
            Management_name='Attendance Management',
            email='mgmt_att@test.com'
        )

        self.teacher = Teacher.objects.create(
            teacher_name='Prof. A',
            teacher_rollNo='T_ATT',
            email='att_t@t.com',
            management=self.management,
        )
        self.course = Course.objects.create(course_code='CS101', course_name='Intro CS')
        self.student = Student.objects.create(
            student_name='Test Stu', student_rollNo='ROLL001', year=1, dept='CS', section='A', email='ts@t.com',
            management=self.management,
        )
        self.second_student = Student.objects.create(
            student_name='Other Stu', student_rollNo='ROLL002', year=1, dept='CS', section='A', email='other@t.com',
            management=self.management,
        )
        self.other_management_user = User.objects.create_user(username='mgmt_other', password='Pass123!')
        self.other_management = Management.objects.create(
            user=self.other_management_user,
            Management_name='Other Management',
            email='mgmt_other@test.com'
        )
        self.other_teacher = Teacher.objects.create(
            teacher_name='Prof. Other',
            teacher_rollNo='T_OTHER',
            email='other_teacher@t.com',
            management=self.other_management,
        )
        self.other_student = Student.objects.create(
            student_name='Hidden Stu', student_rollNo='ROLL003', year=1, dept='CS', section='A', email='hidden@t.com',
            management=self.other_management,
        )

        self.sc = StudentCourse.objects.create(
            student=self.student,
            course=self.course,
            teacher=self.teacher,
            classes_attended_count=2
        )
        self.second_sc = StudentCourse.objects.create(
            student=self.second_student,
            course=self.course,
            teacher=self.teacher,
            classes_attended_count=1
        )
        StudentCourse.objects.create(
            student=self.other_student,
            course=self.course,
            teacher=self.other_teacher,
            classes_attended_count=3
        )

        import secrets
        for i in range(3):
            AttendanceSession.objects.create(
                teacher=self.teacher, course=self.course,
                section='A', year=1,
                qr_code_token=secrets.token_urlsafe(16) + str(i),
                status='stopped'
            )
        for i in range(2):
            AttendanceSession.objects.create(
                teacher=self.other_teacher, course=self.course,
                section='A', year=1,
                qr_code_token=secrets.token_urlsafe(16) + 'other' + str(i),
                status='stopped'
            )

    def test_summary_by_roll_no(self):
        response = self.client.get(f'{self.url}?student_rollNo=ROLL001')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['student_rollNo'], 'ROLL001')
        self.assertEqual(response.data['name'], 'Test Stu')
        self.assertEqual(len(response.data['courses']), 1)
        course_info = response.data['courses'][0]
        self.assertEqual(course_info['course_code'], 'CS101')
        self.assertEqual(course_info['attended'], 2)
        self.assertEqual(course_info['total_sessions'], 3)

    def test_summary_by_program_and_year_returns_matching_students(self):
        response = self.client.get(f'{self.url}?program=CS&year=1')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['filters']['program'], 'CS')
        self.assertEqual(response.data['filters']['year'], '1')

        rolls = [student['student_rollNo'] for student in response.data['students']]
        self.assertIn('ROLL001', rolls)
        self.assertIn('ROLL002', rolls)
        self.assertNotIn('ROLL003', rolls)

    def test_summary_by_combined_filters_returns_scoped_matches(self):
        response = self.client.get(f'{self.url}?student_rollNo=ROLL002&program=CS&year=1')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['students'][0]['student_rollNo'], 'ROLL002')
        self.assertEqual(response.data['students'][0]['courses'][0]['total_sessions'], 3)

    def test_summary_uses_slot_count_for_total_sessions(self):
        slot_course = Course.objects.create(course_code='CS406', course_name='Software Design')
        StudentCourse.objects.create(
            student=self.student,
            course=slot_course,
            teacher=self.teacher,
            classes_attended_count=2,
        )

        import secrets
        AttendanceSession.objects.create(
            teacher=self.teacher,
            course=slot_course,
            section='A',
            year=1,
            slot_count=2,
            qr_code_token=secrets.token_urlsafe(16) + 'slot',
            status='stopped',
        )

        response = self.client.get(f'{self.url}?student_rollNo=ROLL001')
        self.assertEqual(response.status_code, 200)
        slot_entry = next(c for c in response.data['courses'] if c['course_code'] == 'CS406')
        self.assertEqual(slot_entry['attended'], 2)
        self.assertEqual(slot_entry['total_sessions'], 2)
        self.assertAlmostEqual(slot_entry['percent'], 100.0)

    def test_missing_roll_no_returns_400(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 400)

    def test_nonexistent_roll_no_returns_404(self):
        response = self.client.get(f'{self.url}?student_rollNo=NONEXISTENT')
        self.assertEqual(response.status_code, 404)

    def test_unauthenticated_denied(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(f'{self.url}?student_rollNo=ROLL001')
        self.assertEqual(response.status_code, 401)


class CourseAttendanceSummaryTestCase(APITestCase):
    """Tests for GET /api/attendance/course/?course_code=X"""

    def setUp(self):
        self.url = reverse('attendance-course-summary')
        self.user = User.objects.create_user(username='mgmt_cat', password='Pass123!')
        self.client.force_authenticate(user=self.user)
        self.management = Management.objects.create(
            user=self.user,
            Management_name='Course Attendance Management',
            email='mgmt_cat@test.com'
        )

        self.teacher = Teacher.objects.create(
            teacher_name='Prof. B',
            teacher_rollNo='T_CAT',
            email='cat_t@t.com',
            management=self.management,
        )
        self.course = Course.objects.create(course_code='IT201', course_name='Networks')
        self.s1 = Student.objects.create(
            student_name='Stu One', student_rollNo='S_ONE', year=2, dept='IT', section='A', email='s1@t.com',
            management=self.management,
        )
        self.s2 = Student.objects.create(
            student_name='Stu Two', student_rollNo='S_TWO', year=2, dept='IT', section='A', email='s2@t.com',
            management=self.management,
        )
        TaughtCourse.objects.create(
            teacher=self.teacher,
            course=self.course,
            section='A',
            year=2,
            classes_taken_count=0,
        )

        StudentCourse.objects.create(student=self.s1, course=self.course, teacher=self.teacher, classes_attended_count=1)
        StudentCourse.objects.create(student=self.s2, course=self.course, teacher=self.teacher, classes_attended_count=0)

        import secrets
        for i in range(2):
            AttendanceSession.objects.create(
                teacher=self.teacher, course=self.course,
                section='A', year=2,
                qr_code_token=secrets.token_urlsafe(16) + str(i),
                status='stopped'
            )

    def test_course_summary_by_code(self):
        response = self.client.get(f'{self.url}?course_code=IT201')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['course_code'], 'IT201')
        self.assertEqual(len(response.data['students']), 2)

        stu_one = next(s for s in response.data['students'] if s['roll'] == 'S_ONE')
        self.assertEqual(stu_one['attended'], 1)
        self.assertEqual(stu_one['total_sessions'], 2)
        self.assertAlmostEqual(stu_one['percent'], 50.0)

        stu_two = next(s for s in response.data['students'] if s['roll'] == 'S_TWO')
        self.assertEqual(stu_two['attended'], 0)

    def test_missing_params_returns_400(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 400)

    def test_nonexistent_course_returns_404(self):
        response = self.client.get(f'{self.url}?course_code=XXXX')
        self.assertEqual(response.status_code, 404)

    def test_course_summary_uses_slot_count_for_total_sessions(self):
        import secrets
        AttendanceSession.objects.create(
            teacher=self.teacher,
            course=self.course,
            section='A',
            year=2,
            slot_count=3,
            qr_code_token=secrets.token_urlsafe(16) + 'slots',
            status='stopped'
        )

        response = self.client.get(f'{self.url}?course_code=IT201')
        self.assertEqual(response.status_code, 200)
        stu_one = next(s for s in response.data['students'] if s['roll'] == 'S_ONE')
        self.assertEqual(stu_one['total_sessions'], 5)
