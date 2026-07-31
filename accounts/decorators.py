from functools import wraps

def public_access(view_func):
    """
    Decorator that marks a view as explicitly public.
    The LoginRequiredMiddleware will bypass authentication checks
    for views decorated with this.
    """
    view_func.is_public = True
    
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        return view_func(*args, **kwargs)
        
    wrapper.is_public = True
    return wrapper
