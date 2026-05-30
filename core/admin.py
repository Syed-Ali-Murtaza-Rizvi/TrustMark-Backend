from django import forms
from django.contrib import admin
from .models import Class, Student, Management, Teacher, Course, TaughtCourse, StudentCourse, UpdateAttendanceRequest

# Register your models here.
@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ('classroom_id', 'scanner_id')
    search_fields = ('scanner_id',)

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('student_id', 'student_name', 'email', 'student_rollNo', 'year', 'dept', 'section', 'overall_attendance')
    search_fields = ('student_name', 'email', 'student_rollNo', 'dept', 'section')
    list_filter = ('year', 'dept', 'section')

@admin.register(Management)
class ManagementAdmin(admin.ModelAdmin):
    list_display = ('Management_id', 'Management_name', 'email')
    search_fields = ('Management_name', 'email')

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('course_id', 'course_name')
    search_fields = ('course_name',)

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('teacher_id', 'teacher_name', 'email', 'teacher_rollNo')
    search_fields = ('teacher_name', 'email', 'teacher_rollNo')

class TaughtCourseAdminForm(forms.ModelForm):
    class Meta:
        model = TaughtCourse
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['teacher'].empty_label = "---Select Teacher---"
        self.fields['course'].empty_label = "---Select Course---"

@admin.register(TaughtCourse)
class TaughtCourseAdmin(admin.ModelAdmin):
    form = TaughtCourseAdminForm
    list_display = ('id', 'teacher', 'course', 'classes_taken_count')
    list_filter = ('teacher', 'course')
    search_fields = ('teacher__teacher_name', 'course__course_name')

class StudentCourseAdminForm(forms.ModelForm):
    class Meta:
        model = StudentCourse
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['student'].empty_label = "---Select Student---"
        self.fields['teacher'].empty_label = "---Select Teacher---"
        self.fields['course'].empty_label = "---Select Course---"

@admin.register(StudentCourse)
class StudentCourseAdmin(admin.ModelAdmin):
    form = StudentCourseAdminForm
    list_display = ('id', 'student', 'course', 'teacher', 'classes_attended_count')
    list_filter = ('course', 'teacher')
    search_fields = ('student__student_name', 'course__course_name', 'teacher__teacher_name')


class UpdateAttendanceRequestAdminForm(forms.ModelForm):
    class Meta:
        model = UpdateAttendanceRequest
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['teacher'].empty_label = "---Select Teacher---"
        self.fields['student'].empty_label = "---Select Student---"
        self.fields['course'].empty_label = "---Select Course---"
        if 'processed_by' in self.fields:
            self.fields['processed_by'].empty_label = "---Select Management---"


@admin.register(UpdateAttendanceRequest)
class UpdateAttendanceRequestAdmin(admin.ModelAdmin):
    form = UpdateAttendanceRequestAdminForm
    list_display = ('id', 'teacher', 'student', 'course', 'classes_to_add', 'status', 'requested_at', 'processed_by')
    list_filter = ('status', 'teacher', 'course', 'requested_at')
    search_fields = ('teacher__teacher_name', 'student__student_name', 'course__course_name', 'reason')
    readonly_fields = ('requested_at', 'processed_at')
