from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json
from app.assistant.ai import get_ai_recommendation


@login_required
def assistant_chat(request):
    """AI assistant chat interface."""
    from app.audits.models import Audit
    
    latest_audit = Audit.objects.filter(user=request.user).order_by('-created_at').first()
    context = {
        'audit': latest_audit,
    }
    return render(request, 'assistant/chat.html', context)


@login_required
@require_http_methods(["POST"])
def assistant_query(request):
    """Handle AI assistant queries."""
    try:
        data = json.loads(request.body)
        query = data.get('query', '')
        constraints = data.get('constraints', {})
        
        recommendation = get_ai_recommendation(request.user, query, constraints)
        
        return JsonResponse({
            'success': True,
            'response': recommendation
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
