# Generated manually: CoreTag + Section.core_tags M2M

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CoreTag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=80, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'ordering': ['name']},
        ),
        migrations.AddField(
            model_name='section',
            name='core_tags',
            field=models.ManyToManyField(
                blank=True,
                help_text='Core requirements this section satisfies (from CSV). Cross-listed sections can have multiple tags.',
                related_name='sections',
                to='catalog.coretag'
            ),
        ),
    ]
