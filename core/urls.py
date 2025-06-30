from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),  # Nouvelle URL pour la page d'accueil
    path('pre-inscription/', views.pre_inscription_view, name='pre_inscription'),
    path('pre-inscription/succes/', views.pre_inscription_succes_view, name='pre_inscription_succes'),
    path('notes/', views.consultation_notes_view, name='consultation_notes'),

    # URLs pour l'émargement des formateurs
    path('formateur/emargement/', views.emargement_form_view, name='emargement_form'),
    path('formateur/tableau-de-bord/', views.formateur_tableau_de_bord_view, name='formateur_tableau_de_bord'),
    path('admin/rapport-heures-formateurs/', views.rapport_heures_formateurs_view, name='rapport_heures_formateurs'),

    path('home/', views.home_view, name='home'),  # Nouvelle URL pour la page d'accueil

# NOUVELLES URLs pour les articles
    path('articles/', views.article_list_view, name='article_list'),
    path('articles/nouveau/', views.article_create_update_view, name='article_create'),
    path('articles/<int:pk>/modifier/', views.article_create_update_view, name='article_update'),
    path('articles/<int:pk>/', views.article_detail_view, name='article_detail'),
]
