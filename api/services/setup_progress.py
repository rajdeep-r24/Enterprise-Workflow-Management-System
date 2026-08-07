from django.apps import apps
from django.utils import timezone
from datetime import timedelta

class SetupProgressService:
    """
    Configuration-driven service to evaluate the onboarding setup progress 
    of an organization based purely on database state.
    """
    
    # Configuration-driven steps
    STEPS = [
        {
            "id": "department",
            "title": "Create your first Department",
            "description": "Departments are the structural units of your organization. They help group employees and configure routing rules.",
            "action_url_name": "department-create",
            "action_label": "Create Department",
            "model": "departments.Department",
            "check_method": "exists"
        },
        {
            "id": "designation",
            "title": "Create your first Designation",
            "description": "Designations define the roles and job titles within your company. They are required before inviting employees.",
            "action_url_name": "designation-create",
            "action_label": "Create Designation",
            "model": "designations.Designation",
            "check_method": "exists"
        },
        {
            "id": "location",
            "title": "Create your first Location",
            "description": "Add physical offices or regions. Workflows can behave differently depending on the requester's location.",
            "action_url_name": "location-create",
            "action_label": "Create Location",
            "model": "locations.Location",
            "check_method": "exists"
        },
        {
            "id": "employee",
            "title": "Invite your first Employee",
            "description": "Bring your team on board. Employees can submit requests and participate in approval workflows.",
            "action_url_name": "employee-create",
            "action_label": "Create Employee",
            "model": "employees.Employee",
            # The ORG_ADMIN counts as 1. So we check if count > 1.
            "check_method": "multiple_exist" 
        },
        {
            "id": "request_type",
            "title": "Create your first Request Type",
            "description": "Define the forms and approval workflows (e.g., Leave Request, Asset Request) that your employees can submit.",
            "action_url_name": "request-type-create",
            "action_label": "Create Request Type",
            "model": "forms_engine.FormDefinition",
            "check_method": "exists"
        },
    ]

    @classmethod
    def get_progress(cls, tenant):
        """
        Calculates the onboarding progress for a given organization.
        Returns a dictionary with completion status, percentage, evaluated steps, and UI state.
        """
        evaluated_steps = []
        completed_count = 0

        for step in cls.STEPS:
            app_label, model_name = step["model"].split(".")
            Model = apps.get_model(app_label, model_name)
            
            qs = Model.objects.filter(organization=tenant)
            
            if step["check_method"] == "multiple_exist":
                is_completed = qs.count() > 1
            else:
                is_completed = qs.exists()

            if is_completed:
                completed_count += 1
                
            evaluated_steps.append({
                **step,
                "is_completed": is_completed
            })

        total_steps = len(cls.STEPS)
        percentage = int((completed_count / total_steps) * 100) if total_steps > 0 else 100
        is_complete = completed_count == total_steps
        
        show_success_card = False
        hide_entirely = False
        
        if is_complete:
            hide_entirely = True
                
        return {
            "steps": evaluated_steps,
            "completed_count": completed_count,
            "total_steps": total_steps,
            "percentage": percentage,
            "is_complete": is_complete,
            "show_success_card": show_success_card,
            "hide_entirely": hide_entirely
        }
