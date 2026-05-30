import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_student_management_teacher_management'),
    ]

    operations = [
        migrations.AddField(
            model_name='updateattendancerequest',
            name='management',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='attendance_requests',
                to='core.management',
            ),
        ),
    ]
