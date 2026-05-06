from django.db import migrations, models


def seed_hospital_branches(apps, schema_editor):
    HospitalSettings = apps.get_model('patients', 'HospitalSettings')
    defaults = [
        {
            "branch": "LNM",
            "slug": "laxmi",
            "uhid_prefix": "SHL",
            "hospital_name": "SANGI HOSPITAL",
            "branch_name": "Lakshmi Nagar",
            "address": "Lakshmi Nagar, Mathura, Uttar Pradesh - 281004",
            "phone": "+91-9717444531 / +91-9717444532",
            "email": "laxminagar@sangihospital.com",
            "website": "https://www.sangihospital.com",
        },
        {
            "branch": "RYM",
            "slug": "raya",
            "uhid_prefix": "SHR",
            "hospital_name": "SANGI HOSPITAL",
            "branch_name": "Raya",
            "address": "Raya, Mathura, Uttar Pradesh - 281204",
            "phone": "+91-9311212090 / +91-9311212091",
            "email": "info@sangihospital.com",
            "website": "https://www.sangihospital.com",
        },
    ]
    for payload in defaults:
        HospitalSettings.objects.update_or_create(branch=payload["branch"], defaults=payload)


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0012_medicinemaster_quantity'),
    ]

    operations = [
        migrations.AlterField(
            model_name='hospitalsettings',
            name='branch',
            field=models.CharField(default='LNM', max_length=10, unique=True),
        ),
        migrations.AddField(
            model_name='hospitalsettings',
            name='slug',
            field=models.SlugField(blank=True, default='', max_length=50, unique=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='hospitalsettings',
            name='uhid_prefix',
            field=models.CharField(default='SHL', max_length=10),
        ),
        migrations.AlterField(
            model_name='departmentlogentry',
            name='branch',
            field=models.CharField(default='LNM', max_length=10),
        ),
        migrations.RunPython(seed_hospital_branches, migrations.RunPython.noop),
    ]
