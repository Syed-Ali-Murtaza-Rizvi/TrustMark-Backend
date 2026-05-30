from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_updateattendancerequest_management'),
    ]

    operations = [
        migrations.RenameField(
            model_name='student',
            old_name='rfid',
            new_name='student_rollNo',
        ),
        migrations.RenameField(
            model_name='teacher',
            old_name='rfid',
            new_name='teacher_rollNo',
        ),
    ]