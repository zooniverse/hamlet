# Generated by Django 2.2.1 on 2019-05-23 11:03

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='SubjectSetExport',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('subject_set_id', models.IntegerField()),
                ('status', models.CharField(choices=[('p', 'Pending'), ('r', 'Running'), ('c', 'Complete'), ('f', 'Failed')], default='p', max_length=1)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='MediaMetadata',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('p', 'Pending'), ('r', 'Running'), ('c', 'Complete'), ('f', 'Failed')], default='p', max_length=1)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('subject_id', models.IntegerField()),
                ('hash', models.CharField(max_length=32, null=True)),
                ('filesize', models.IntegerField(null=True)),
                ('url', models.URLField()),
                ('export', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='exports.SubjectSetExport')),
            ],
        ),
    ]
