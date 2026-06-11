from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth.models import User

from .models import Management, Teacher, Student, Course, TaughtCourse, StudentCourse


class ManagementBulkUpdateStudentCoursesTestCase(APITestCase):
    def setUp(self):
        # Create management user and management
        self.mgmt_user = User.objects.create_user(username='mgmt@test.com', email='mgmt@test.com', password='TestPass123!')
        self.management = Management.objects.create(user=self.mgmt_user, Management_name='Mgmt', email='mgmt@test.com')

        # Authenticate as management user
        self.client.force_authenticate(user=self.mgmt_user)

        # Common cohort details
        self.program = 'CS'
        self.year = 2
        self.section = 'A'

        # Create courses
        self.course1 = Course.objects.create(course_name='Course 1', course_code='CS101')
        self.course2 = Course.objects.create(course_name='Course 2', course_code='CS102')
        self.old_course = Course.objects.create(course_name='Old Course', course_code='CS000')

        # Create a teacher in the same management and with matching programs
        self.teacher = Teacher.objects.create(teacher_name='T1', email='t1@test.com', teacher_rollNo='T001', management=self.management, programs='CS')

        # Create taught course mappings so courses are in-scope for this management
        TaughtCourse.objects.create(teacher=self.teacher, course=self.course1, section=self.section, year=self.year)
        TaughtCourse.objects.create(teacher=self.teacher, course=self.course2, section=self.section, year=self.year)

        # Create students in the management/program/year cohort
        self.student1 = Student.objects.create(student_name='S1', email='s1@test.com', student_rollNo='S001', year=self.year, dept=self.program, section=self.section, management=self.management)
        self.student2 = Student.objects.create(student_name='S2', email='s2@test.com', student_rollNo='S002', year=self.year, dept=self.program, section=self.section, management=self.management)

        # Pre-existing student course assignment (should be removed)
        StudentCourse.objects.create(student=self.student1, course=self.old_course, teacher=self.teacher)
        StudentCourse.objects.create(student=self.student2, course=self.old_course, teacher=self.teacher)

    def test_bulk_update_replaces_student_courses_without_affecting_teachers(self):
        url = reverse('management-bulk-update-student-courses', args=[self.management.Management_id, self.program, self.year])
        payload = {'course_ids': [self.course1.course_id, self.course2.course_id]}

        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get('success'))
        self.assertEqual(response.data.get('students_updated'), 2)

        # Ensure old student-course rows removed and new ones created
        sc1 = StudentCourse.objects.filter(student=self.student1).order_by('course__course_id')
        sc2 = StudentCourse.objects.filter(student=self.student2).order_by('course__course_id')

        self.assertEqual(sc1.count(), 2)
        self.assertEqual(sc2.count(), 2)

        course_ids_s1 = set(sc.course.course_id for sc in sc1)
        course_ids_s2 = set(sc.course.course_id for sc in sc2)
        self.assertEqual(course_ids_s1, {self.course1.course_id, self.course2.course_id})
        self.assertEqual(course_ids_s2, {self.course1.course_id, self.course2.course_id})

        # Teachers and taught course entries should remain intact
        self.assertTrue(Teacher.objects.filter(teacher_id=self.teacher.teacher_id).exists())
        self.assertTrue(TaughtCourse.objects.filter(teacher=self.teacher, course=self.course1).exists())
        self.assertTrue(TaughtCourse.objects.filter(teacher=self.teacher, course=self.course2).exists())

    def test_bulk_update_accepts_course_codes(self):
        """API should accept non-numeric course identifiers (course codes)"""
        url = reverse('management-bulk-update-student-courses', args=[self.management.Management_id, self.program, self.year])
        payload = {'course_ids': [self.course1.course_code, self.course2.course_code]}

        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get('success'))

        sc1 = StudentCourse.objects.filter(student=self.student1).order_by('course__course_id')
        sc2 = StudentCourse.objects.filter(student=self.student2).order_by('course__course_id')
        self.assertEqual(sc1.count(), 2)
        self.assertEqual(sc2.count(), 2)
