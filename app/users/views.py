from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model

User = get_user_model()


def landing(request):
    """Landing page - redirect to dashboard if logged in."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'landing.html')


@login_required
def dashboard(request):
    """Main dashboard showing user's audit status."""
    from app.audits.models import Audit
    
    latest_audit = Audit.objects.filter(user=request.user).order_by('-created_at').first()
    
    context = {
        'latest_audit': latest_audit,
    }
    return render(request, 'dashboard.html', context)
