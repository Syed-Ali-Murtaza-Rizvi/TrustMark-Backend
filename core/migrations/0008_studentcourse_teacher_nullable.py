import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_teacher_phone_years_programs_course_code'),
    ]

    operations = [
        migrations.AlterField(
            model_name='studentcourse',
            name='teacher',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='student_courses',
                to='core.teacher',
            ),
        ),
    ]
