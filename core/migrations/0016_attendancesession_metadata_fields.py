from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0015_remove_legacy_text_attendance_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='attendancesession',
            name='attendance_type',
            field=models.CharField(
                choices=[('regular', 'Regular'), ('compensatory', 'Compensatory')],
                default='regular',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='attendancesession',
            name='latitude',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='attendancesession',
            name='longitude',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='attendancesession',
            name='program',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AddField(
            model_name='attendancesession',
            name='radius_meters',
            field=models.PositiveIntegerField(default=50),
        ),
    ]
