"""
URL configuration for school_management project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from core import views # NOUVEAU: Importez le module views de l'application core

urlpatterns = [

    path('admin/emargements/validation/', views.emargement_validation_view, name='emargement_validation'),
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    # URLs d'authentification de Django (connexion/déconnexion)
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),

    # URLs pour la réinitialisation du mot de passe
    path('password_reset/',
         auth_views.PasswordResetView.as_view(template_name='core/password_reset_form.html',
                                               email_template_name='core/password_reset_email.html',
                                               subject_template_name='core/password_reset_subject.txt'),
         name='password_reset'),
    path('password_reset/done/',
         auth_views.PasswordResetDoneView.as_view(template_name='core/password_reset_done.html'),
         name='password_reset_done'),
    path('reset/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(template_name='core/password_reset_confirm.html'),
         name='password_reset_confirm'),
    path('reset/done/',
         auth_views.PasswordResetCompleteView.as_view(template_name='core/password_reset_complete.html'),
         name='password_reset_complete'),

    # URLs pour les formateurs et l'administration des émargements
    path('formateur/emargement/', include('core.urls')), # C'est déjà inclus via `path('', include('core.urls'))`
]
# URLs spécifiques à l'application core
urlpatterns += [
    path('api/like_article/', views.like_article, name='like_article'), # NOUVEAU: URL pour la fonction de like
]
# URLs spécifiques à l'application core
#urlpatterns += [

#]


# Servir les fichiers médias en mode développement
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
