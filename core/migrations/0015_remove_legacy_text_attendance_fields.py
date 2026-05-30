from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_numeric_classes_taken_count'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='studentcourse',
            name='classes_attended',
        ),
        migrations.RemoveField(
            model_name='taughtcourse',
            name='classes_taken',
        ),
    ]
