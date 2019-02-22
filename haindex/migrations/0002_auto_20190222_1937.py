# Generated by Django 2.1.7 on 2019-02-22 19:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('haindex', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='repository',
            name='display_name',
            field=models.CharField(blank=True, max_length=100, verbose_name='Display name'),
        ),
        migrations.AlterField(
            model_name='repository',
            name='name',
            field=models.CharField(max_length=100, verbose_name='Name'),
        ),
    ]