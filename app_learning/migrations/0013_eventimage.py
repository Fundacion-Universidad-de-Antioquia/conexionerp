# Generated by Django 5.0.7 on 2024-11-21 08:52

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_learning', '0012_ctrlcapacitaciones_image_url'),
    ]

    operations = [
        migrations.CreateModel(
            name='EventImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image_url', models.URLField(max_length=500)),
                ('capacitacion', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='app_learning.ctrlcapacitaciones')),
            ],
        ),
    ]
