# Generated migration for geo, phone, age fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0005_eventparticipant'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='geo',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='eventparticipant',
            name='age',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='eventparticipant',
            name='phone',
            field=models.CharField(blank=True, default='', max_length=30),
        ),
    ]
