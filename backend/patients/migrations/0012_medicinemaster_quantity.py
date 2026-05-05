from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0011_hospitalsettings_branch'),
    ]

    operations = [
        migrations.AddField(
            model_name='medicinemaster',
            name='quantity',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
