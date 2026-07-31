from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.db import IntegrityError
from django.core.exceptions import ValidationError

from accounts.decorators import public_access
from organizations.forms import OrganizationSignupForm
from organizations.services import create_organization_and_admin

@public_access
def organization_signup(request):
    if request.method == "POST":
        form = OrganizationSignupForm(request.POST)
        if form.is_valid():
            try:
                # Call the service to create records
                create_organization_and_admin(form.cleaned_data)
                
                # Authenticate and login the new admin
                email = form.cleaned_data['email']
                password = form.cleaned_data['password']
                user = authenticate(request, email=email, password=password)
                
                if user is not None:
                    login(request, user)
                    return redirect('dashboard')
                else:
                    form.add_error(None, "Authentication failed after signup.")
                    
            except IntegrityError:
                form.add_error(None, "A database error occurred. The organization name or email might already be in use.")
            except ValidationError as e:
                form.add_error(None, str(e))
            except Exception as e:
                form.add_error(None, f"An unexpected error occurred: {str(e)}")
    else:
        form = OrganizationSignupForm()
        
    return render(request, "organizations/signup.html", {"form": form})
