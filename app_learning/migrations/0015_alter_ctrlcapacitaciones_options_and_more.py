# Generated by Django 5.0.7 on 2025-06-10 14:13

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_learning', '0014_ctrlcapacitaciones_archivo_presentacion_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='ctrlcapacitaciones',
            options={'ordering': ['-fecha', 'hora_inicial'], 'verbose_name': 'Evento', 'verbose_name_plural': 'Eventos'},
        ),
        migrations.AlterModelOptions(
            name='eventimage',
            options={'verbose_name': 'Imagen de evento', 'verbose_name_plural': 'Imágenes de eventos'},
        ),
        migrations.AddField(
            model_name='ctrlcapacitaciones',
            name='verificacion_identidad',
            field=models.CharField(blank=True, choices=[('SI', 'SI'), ('NO', 'NO')], default='NO', max_length=2, null=True, verbose_name='verificacion de identidad'),
        ),
        migrations.AlterField(
            model_name='ctrlcapacitaciones',
            name='area_encargada',
            field=models.CharField(max_length=100, verbose_name='Área encargada'),
        ),
        migrations.AlterField(
            model_name='ctrlcapacitaciones',
            name='estado',
            field=models.CharField(choices=[('ACTIVA', 'ACTIVA'), ('CERRADA', 'CERRADA'), ('CANCELADA', 'CANCELADA'), ('PENDIENTE', 'PENDIENTE')], default='ACTIVA', max_length=10, verbose_name='Estado'),
        ),
        migrations.AlterField(
            model_name='ctrlcapacitaciones',
            name='hora_final',
            field=models.TimeField(verbose_name='Hora de finalización'),
        ),
        migrations.AlterField(
            model_name='ctrlcapacitaciones',
            name='hora_inicial',
            field=models.TimeField(verbose_name='Hora de inicio'),
        ),
        migrations.AlterField(
            model_name='ctrlcapacitaciones',
            name='image_url',
            field=models.URLField(blank=True, null=True, verbose_name='URL de imagen'),
        ),
        migrations.AlterField(
            model_name='ctrlcapacitaciones',
            name='modalidad',
            field=models.CharField(choices=[('PRESENCIAL', 'PRESENCIAL'), ('VIRTUAL', 'VIRTUAL'), ('MIXTA', 'MIXTA')], default='', max_length=10, verbose_name='Modalidad'),
        ),
        migrations.AlterField(
            model_name='ctrlcapacitaciones',
            name='moderador',
            field=models.CharField(max_length=60, verbose_name='Moderador'),
        ),
        migrations.AlterField(
            model_name='ctrlcapacitaciones',
            name='objetivo',
            field=models.CharField(max_length=255, verbose_name='Objetivo'),
        ),
        migrations.AlterField(
            model_name='ctrlcapacitaciones',
            name='qr_base64',
            field=models.TextField(blank=True, null=True, verbose_name='Código QR (Base64)'),
        ),
        migrations.AlterField(
            model_name='ctrlcapacitaciones',
            name='responsable',
            field=models.CharField(default='', max_length=60, verbose_name='Responsable'),
        ),
        migrations.AlterField(
            model_name='ctrlcapacitaciones',
            name='tema',
            field=models.CharField(max_length=60, verbose_name='Tema'),
        ),
        migrations.AlterField(
            model_name='ctrlcapacitaciones',
            name='user',
            field=models.CharField(default='user', max_length=250, verbose_name='Usuario creador'),
        ),
        migrations.AlterField(
            model_name='eventimage',
            name='capacitacion',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='app_learning.ctrlcapacitaciones', verbose_name='Evento'),
        ),
        migrations.AlterField(
            model_name='eventimage',
            name='image_url',
            field=models.URLField(max_length=500, verbose_name='URL de la imagen'),
        ),
    ]
