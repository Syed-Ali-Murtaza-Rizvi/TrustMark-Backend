import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_studentcourse_teacher_nullable'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='management',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='students',
                to='core.management',
            ),
        ),
        migrations.AddField(
            model_name='teacher',
            name='management',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='teachers',
                to='core.management',
            ),
        ),
    ]
