from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json
from .services.code_generation import CodeGenerationService
from accounts.decorators import public_access  # Assuming the api might need auth or public depending on usage. Wait, user is authenticated so it's fine.

# Better to use login_required but let's just do standard request processing
from django.contrib.auth.decorators import login_required

@login_required
@require_POST
def code_suggestion(request):
    try:
        data = json.loads(request.body)
        entity = data.get("entity")
        name = data.get("name")
        
        if not entity or name is None:
            return JsonResponse({"error": "Missing entity or name"}, status=400)
            
        tenant = request.tenant
        
        suggested_code = CodeGenerationService.generate(entity, name, tenant)
        
        return JsonResponse({"suggested_code": suggested_code})
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

