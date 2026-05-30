from django.db import migrations, models


def backfill_classes_taken_count(apps, schema_editor):
    TaughtCourse = apps.get_model('core', 'TaughtCourse')
    for tc in TaughtCourse.objects.all().iterator():
        classes_str = tc.classes_taken or ''
        count = len([c.strip() for c in classes_str.split(',') if c.strip()])
        tc.classes_taken_count = count
        tc.save(update_fields=['classes_taken_count'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0013_attendance_slot_count_and_numeric_student_count'),
    ]

    operations = [
        migrations.AddField(
            model_name='taughtcourse',
            name='classes_taken_count',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.RunPython(backfill_classes_taken_count, migrations.RunPython.noop),
    ]
