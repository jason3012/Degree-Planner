from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator

User = get_user_model()


class Audit(models.Model):
    """Student degree audit upload."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='audits')
    uploaded_pdf = models.FileField(upload_to='audits/%Y/%m/%d/')
    created_at = models.DateTimeField(auto_now_add=True)
    parse_version = models.CharField(max_length=20, default='1.0')
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Audit for {self.user.email} - {self.created_at.date()}"


class AuditCourse(models.Model):
    """Course extracted from audit PDF."""
    audit = models.ForeignKey(Audit, on_delete=models.CASCADE, related_name='courses')
    term_code = models.CharField(max_length=10, help_text="e.g., 26SP, 25FA")
    course_code = models.CharField(
        max_length=20,
        validators=[RegexValidator(regex=r'^[A-Z]{4}\d{4}$', message='Must be base code ABCD1234')],
        help_text="Base course code only, e.g., ARTS1101"
    )
    credits = models.DecimalField(max_digits=3, decimal_places=1)
    status = models.CharField(max_length=20, choices=[
        ('completed', 'Completed'),
        ('in_progress', 'In Progress'),
        ('withdrawn', 'Withdrawn'),
    ])
    grade_token = models.CharField(max_length=10, blank=True, help_text="e.g., A, A-, B+, IP, AP, W")
    title_raw = models.CharField(max_length=200, blank=True)
    
    class Meta:
        unique_together = [['audit', 'term_code', 'course_code']]
        ordering = ['term_code', 'course_code']
    
    def __str__(self):
        return f"{self.course_code} ({self.term_code}) - {self.status}"
