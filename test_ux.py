import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from organizations.models import Organization
from forms_engine.forms import RequestTypeForm, FormFieldForm, WorkflowStepForm

org = Organization.objects.first()

print("Testing Request Type Creation...")
form = RequestTypeForm(data={"name": "Travel Expense"}, tenant=org)
if form.is_valid():
    from workflow.models import WorkflowDefinition, WorkflowVersion
    workflow_def = WorkflowDefinition.objects.create(
        organization=org,
        name=form.cleaned_data["name"],
        code=form.cleaned_data["code"],
        description=form.cleaned_data["description"]
    )
    workflow_version = WorkflowVersion.objects.create(
        workflow=workflow_def,
        version=1,
        is_latest=True
    )
    form_def = form.save(commit=False)
    form_def.organization = org
    form_def.workflow = workflow_version
    form_def.is_published = False
    form_def.save()
    print("✓ Request Type:", form_def.code)
else:
    print("x Failed:", form.errors)

print("\nTesting Field Creation...")
field_form1 = FormFieldForm(data={
    "label": "Destination",
    "field_type": "text",
}, form_definition=form_def)
if field_form1.is_valid():
    f1 = field_form1.save(commit=False)
    f1.form = form_def
    f1.save()
    print(f"✓ Field 1: {f1.field_name}, required={f1.is_required}, order={f1.order}")
else:
    print("x Failed Field 1:", field_form1.errors)

field_form2 = FormFieldForm(data={
    "label": "Travel Mode",
    "field_type": "select",
    "options": "Flight, Train, Bus"
}, form_definition=form_def)
if field_form2.is_valid():
    f2 = field_form2.save(commit=False)
    f2.form = form_def
    f2.save()
    print(f"✓ Field 2: {f2.field_name}, required={f2.is_required}, order={f2.order}, options={f2.options}")
else:
    print("x Failed Field 2:", field_form2.errors)

print("\nTesting Step Creation...")
step_form1 = WorkflowStepForm(data={
    "name": "Manager Approval",
    "approver_type": "MANAGER",
    "is_required": True,
}, workflow_version=form_def.workflow, tenant=org)
if step_form1.is_valid():
    s1 = step_form1.save(commit=False)
    s1.workflow_version = form_def.workflow
    s1.save()
    print(f"✓ Step 1: {s1.name}, order={s1.step_order}")
else:
    print("x Failed Step 1:", step_form1.errors)

step_form2 = WorkflowStepForm(data={
    "name": "Finance Approval",
    "approver_type": "ROLE",
    "role_code": "FINANCE",
    "is_required": True,
}, workflow_version=form_def.workflow, tenant=org)
if step_form2.is_valid():
    s2 = step_form2.save(commit=False)
    s2.workflow_version = form_def.workflow
    s2.save()
    print(f"✓ Step 2: {s2.name}, order={s2.step_order}")
else:
    print("x Failed Step 2:", step_form2.errors)
