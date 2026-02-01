from django.db import models
from django.core.validators import RegexValidator


class Semester(models.Model):
    """Academic semester/term."""
    term_code = models.CharField(max_length=10, unique=True, help_text="e.g., 26SP, 25FA")
    label = models.CharField(max_length=50, help_text="e.g., Spring 2026")
    is_current = models.BooleanField(default=False, help_text="Is this the current semester?")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-term_code']
    
    def __str__(self):
        return f"{self.label} ({self.term_code})"


class CoreTag(models.Model):
    """Core requirement tag (e.g., Arts, Cultural Diversity). Sections can satisfy multiple cores."""
    name = models.CharField(max_length=80, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Course(models.Model):
    """Base course (e.g., ARTS1101)."""
    course_code = models.CharField(
        max_length=20,
        primary_key=True,
        validators=[RegexValidator(regex=r'^[A-Z]{4}\d{4}$', message='Must be ABCD1234 format')],
        help_text="Base course code, e.g., ARTS1101"
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    credits = models.DecimalField(max_digits=3, decimal_places=1, default=3.0)
    department = models.CharField(max_length=100, blank=True)
    level = models.CharField(max_length=20, choices=[
        ('undergraduate', 'Undergraduate'),
        ('graduate', 'Graduate'),
    ], default='undergraduate')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['course_code']
    
    def __str__(self):
        return f"{self.course_code}: {self.title}"


class Section(models.Model):
    """Course section (e.g., ARTS1101.01)."""
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name='sections')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='sections')
    section_suffix = models.CharField(max_length=10, help_text="e.g., 01, 02, 03")
    instructor = models.CharField(max_length=200, blank=True)
    raw_meeting_text = models.TextField(help_text="Original meeting string from catalog")
    meetings_json = models.JSONField(default=dict, blank=True, help_text="Parsed meeting data")
    location = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=[
        ('open', 'Open'),
        ('closed', 'Closed'),
        ('waitlist', 'Waitlist'),
    ], default='open', blank=True)
    seats_open = models.IntegerField(null=True, blank=True)
    crn = models.CharField(max_length=10, blank=True, help_text="Course Registration Number")
    core_tags = models.ManyToManyField(
        CoreTag,
        related_name='sections',
        blank=True,
        help_text='Core requirements this section satisfies (from CSV). Cross-listed sections can have multiple tags.'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['semester', 'course', 'section_suffix']]
        ordering = ['course', 'section_suffix']
    
    def __str__(self):
        return f"{self.course.course_code}.{self.section_suffix} - {self.semester.label}"
    
    @property
    def full_code(self):
        """Return full course code with section, e.g., ARTS1101.01"""
        return f"{self.course.course_code}.{self.section_suffix}"
