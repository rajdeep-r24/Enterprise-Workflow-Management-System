import re
from django.apps import apps
from django.utils.text import slugify

class CodeGenerationService:
    COMMON_ABBREVIATIONS = {
        "human resources": "HR",
        "information technology": "IT",
        "finance": "FIN",
        "quality assurance": "QA",
        "research and development": "RND",
        "public relations": "PR",
        "administration": "ADMIN",
    }

    @classmethod
    def generate(cls, entity_name, name, tenant):
        """
        Generate a unique code for the given entity in the given organization.
        
        Rules:
        - Check predefined common abbreviations.
        - Fallback to UPPER_SNAKE_CASE using slugify.
        - Enforce uniqueness within the organization.
        - Suffix with -2, -3 etc. if collision occurs.
        """
        if not name:
            return ""

        name_lower = name.strip().lower()
        if name_lower in cls.COMMON_ABBREVIATIONS:
            base_code = cls.COMMON_ABBREVIATIONS[name_lower]
        else:
            base_code = slugify(name).replace("-", "_").upper()

        if not base_code:
            return ""

        # Map frontend entity names to actual Django models
        model_map = {
            "department": "departments.Department",
            "designation": "designations.Designation",
            "location": "locations.Location",
            "requesttype": "forms_engine.FormDefinition",
            "workflow": "workflow.WorkflowDefinition",
        }
        
        entity_key = entity_name.replace("_", "").replace(" ", "").lower()
        if entity_key not in model_map:
            return base_code

        model = apps.get_model(model_map[entity_key])

        # Optimize by getting all existing codes starting with base_code
        existing_codes = set(
            model.objects.filter(
                organization=tenant,
                code__startswith=base_code
            ).values_list("code", flat=True)
        )

        suggested_code = base_code
        suffix = 1

        while suggested_code in existing_codes:
            suffix += 1
            suggested_code = f"{base_code}-{suffix}"

        return suggested_code
