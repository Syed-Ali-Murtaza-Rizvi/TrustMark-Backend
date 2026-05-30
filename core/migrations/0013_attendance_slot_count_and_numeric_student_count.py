from django.db import migrations, models


def backfill_classes_attended_count(apps, schema_editor):
    StudentCourse = apps.get_model('core', 'StudentCourse')
    for sc in StudentCourse.objects.all().iterator():
        classes_str = sc.classes_attended or ''
        count = len([c.strip() for c in classes_str.split(',') if c.strip()])
        sc.classes_attended_count = count
        sc.save(update_fields=['classes_attended_count'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0012_updateattendancerequest_attendancetype'),
    ]

    operations = [
        migrations.AddField(
            model_name='attendancesession',
            name='slot_count',
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name='studentcourse',
            name='classes_attended_count',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.RunPython(backfill_classes_attended_count, migrations.RunPython.noop),
    ]
