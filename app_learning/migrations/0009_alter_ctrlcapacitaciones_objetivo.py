# Generated by Django 5.0.7 on 2024-08-12 11:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_learning', '0008_alter_ctrlcapacitaciones_area_encargada_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ctrlcapacitaciones',
            name='objetivo',
            field=models.CharField(default='Redactar el objetivo en un máximo de 160 caracteres', max_length=161),
        ),
    ]
