# Generated manually for catalog app

from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Semester',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('term_code', models.CharField(help_text='e.g., 26SP, 25FA', max_length=10, unique=True)),
                ('label', models.CharField(help_text='e.g., Spring 2026', max_length=50)),
                ('is_current', models.BooleanField(default=False, help_text='Is this the current semester?')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'ordering': ['-term_code']},
        ),
        migrations.CreateModel(
            name='Course',
            fields=[
                ('course_code', models.CharField(help_text='Base course code, e.g., ARTS1101', max_length=20, primary_key=True, serialize=False, validators=[django.core.validators.RegexValidator(message='Must be ABCD1234 format', regex='^[A-Z]{4}\\d{4}$')])),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                ('credits', models.DecimalField(decimal_places=1, default=3.0, max_digits=3)),
                ('department', models.CharField(blank=True, max_length=100)),
                ('level', models.CharField(choices=[('undergraduate', 'Undergraduate'), ('graduate', 'Graduate')], default='undergraduate', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'ordering': ['course_code']},
        ),
        migrations.CreateModel(
            name='Section',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('section_suffix', models.CharField(help_text='e.g., 01, 02, 03', max_length=10)),
                ('instructor', models.CharField(blank=True, max_length=200)),
                ('raw_meeting_text', models.TextField(help_text='Original meeting string from catalog')),
                ('meetings_json', models.JSONField(blank=True, default=dict, help_text='Parsed meeting data')),
                ('location', models.CharField(blank=True, max_length=100)),
                ('status', models.CharField(blank=True, choices=[('open', 'Open'), ('closed', 'Closed'), ('waitlist', 'Waitlist')], default='open', max_length=20)),
                ('seats_open', models.IntegerField(blank=True, null=True)),
                ('crn', models.CharField(blank=True, help_text='Course Registration Number', max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sections', to='catalog.course')),
                ('semester', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sections', to='catalog.semester')),
            ],
            options={
                'ordering': ['course', 'section_suffix'],
                'unique_together': {('semester', 'course', 'section_suffix')},
            },
        ),
    ]
