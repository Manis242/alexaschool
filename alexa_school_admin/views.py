from django.shortcuts import render
from django.contrib.auth.decorators import login_required
# Importez vos modèles ici si vous souhaitez récupérer des données réelles
# from your_app.models import Student, Teacher, Course # Exemple

@login_required
def custom_dashboard(request):
    """
    Vue pour le tableau de bord personnalisé de SchoolNet.
    Cette vue récupérera les données nécessaires et les passera au template.
    """
    # Exemple de données statiques pour le moment.
    # Vous remplacerez cela par des requêtes à votre base de données.
    context = {
        'total_students': 1250, # Student.objects.count()
        'total_teachers': 85,   # Teacher.objects.count()
        'total_courses': 150,   # Course.objects.count()
        'recent_enrollments': 12,
        'active_courses': 140,
        'announcements': [
            "Nouvelle mise à jour du système",
            "Réunion du personnel le 20 juillet",
        ],
        'current_user_id': request.user.id if request.user.is_authenticated else 'N/A',
    }
    return render(request, 'alexa_school_admin/dashboard.html', context)