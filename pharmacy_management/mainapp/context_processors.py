from .models import PharmacistMessage

def unread_messages_count(request):
    if not request.user.is_authenticated:
        return {'unread_messages_count': 0}
    
    if request.user.is_staff:
        # Admin sees messages they haven't read yet
        count = PharmacistMessage.objects.filter(is_read_by_admin=False).count()
    else:
        # User sees replies they haven't read yet
        count = PharmacistMessage.objects.filter(user=request.user, is_read_by_user=False).count()
        
    return {'unread_messages_count': count}
