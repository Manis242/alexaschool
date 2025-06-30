from django.contrib import admin
from .models import Option, Niveau, Formateur, Etudiant, Inscription, Article, Matiere, Coefficient, Note, Emargement, \
    Semestre, EmargementTemporaire, Like, Comment
from django.utils.html import format_html
from django.utils import timezone
from django.contrib import messages

# Enregistrement des modèles simples
admin.site.register(Option)
admin.site.register(Niveau)
admin.site.register(Matiere)
admin.site.register(Semestre)
admin.site.register(EmargementTemporaire) # NOUVEAU: Enregistrez le modèle EmargementTemporaire

# Personnalisation de l'affichage de l'étudiant dans l'admin
@admin.register(Etudiant)
class EtudiantAdmin(admin.ModelAdmin):
    list_display = ('nom', 'prenom', 'matricule', 'option', 'niveau', 'sexe', 'dernier_diplome', 'email', 'get_inscription_status', 'display_profile_photo')
    search_fields = ('nom', 'prenom', 'matricule', 'email', 'dernier_diplome')
    list_filter = ('option', 'niveau', 'sexe', 'dernier_diplome')
    raw_id_fields = ('user',)


    def get_inscription_status(self, obj):
        try:
            return obj.inscription.get_statut_display()
        except Inscription.DoesNotExist:
            return "Pas d'inscription"
    get_inscription_status.short_description = "Statut Inscription"

    def display_profile_photo(self, obj):
        if obj.photo_de_profil:
            return format_html('<img src="{}" width="50" height="50" style="border-radius: 50%;" />', obj.photo_de_profil.url)
        return "Pas de photo"
    display_profile_photo.short_description = "Photo"

# Personnalisation de l'affichage du formateur dans l'admin
@admin.register(Formateur)
class FormateurAdmin(admin.ModelAdmin):
    list_display = ('nom', 'prenom', 'code_formateur', 'email', 'prix_par_heure', 'display_matieres', 'user_linked')  # NOUVEAU: Ajout de prix_par_heure
    search_fields = ('nom', 'prenom', 'code_formateur', 'email')
    filter_horizontal = ('matieres',)
    raw_id_fields = ('user',) # Permet de lier un utilisateur existant
    # NOUVEAU: Ajoutez 'prix_par_heure' aux fields si vous utilisez fields ou fieldsets
    fields = ('user', 'nom', 'prenom', 'code_formateur', 'email', 'telephone', 'date_embauche', 'matieres', 'prix_par_heure')

    def display_matieres(self, obj):
        return ", ".join([matiere.nom for matiere in obj.matieres.all()])
    display_matieres.short_description = "Matières enseignées"

    def user_linked(self, obj):
        return bool(obj.user)
    user_linked.boolean = True
    user_linked.short_description = "Compte lié"


# Personnalisation de l'affichage de l'inscription dans l'admin
@admin.register(Inscription)
class InscriptionAdmin(admin.ModelAdmin):
    list_display = ('etudiant_full_name', 'statut', 'date_demande', 'date_validation', 'montant_paye')
    list_filter = ('statut', 'date_demande', 'date_validation')
    search_fields = ('etudiant__nom', 'etudiant__prenom', 'etudiant__matricule')
    actions = ['marquer_en_attente_paiement', 'marquer_inscrit', 'marquer_annule']

    def etudiant_full_name(self, obj):
        return f"{obj.etudiant.nom} {obj.etudiant.prenom}"
    etudiant_full_name.short_description = "Étudiant"

    def marquer_en_attente_paiement(self, request, queryset):
        inscriptions_a_traiter = queryset.filter(statut='PRE_INSCRIPTION')
        for inscription in inscriptions_a_traiter:
            inscription.statut = 'EN_ATTENTE_PAIEMENT'
            inscription.save()
        self.message_user(request, f"{len(inscriptions_a_traiter)} inscription(s) marquée(s) comme 'En attente de paiement' et les e-mails envoyés.", messages.SUCCESS)
    marquer_en_attente_paiement.short_description = "Marquer comme 'En attente de paiement' et envoyer mail"

    def marquer_inscrit(self, request, queryset):
        updated_count = 0
        for inscription in queryset:
            if inscription.statut in ['PRE_INSCRIPTION', 'EN_ATTENTE_PAIEMENT']:
                inscription.statut = 'INSCRIT'
                inscription.save()
                updated_count += 1
        self.message_user(request, f"{updated_count} inscription(s) marquée(s) comme 'Inscrit' et les identifiants envoyés.", messages.SUCCESS)
    marquer_inscrit.short_description = "Marquer comme 'Inscrit' et envoyer les identifiants"

    def marquer_annule(self, request, queryset):
        updated_count = queryset.update(statut='ANNULE')
        self.message_user(request, f"{updated_count} inscription(s) marquée(s) comme 'Annulé'.", messages.WARNING)
    marquer_annule.short_description = "Marquer comme 'Annulé'"

# Personnalisation de l'affichage du Coefficient dans l'admin
@admin.register(Coefficient)
class CoefficientAdmin(admin.ModelAdmin):
    list_display = ('matiere', 'option', 'niveau', 'valeur')
    list_filter = ('option', 'niveau', 'matiere')
    search_fields = ('matiere__nom', 'option__nom', 'niveau__nom')
    raw_id_fields = ('matiere', 'option', 'niveau')

# Personnalisation de l'affichage de la Note dans l'admin
@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ('etudiant', 'matiere', 'valeur', 'semestre', 'formateur', 'date_saisie')
    list_filter = ('semestre', 'matiere', 'formateur', 'date_saisie')
    search_fields = ('etudiant__nom', 'etudiant__prenom', 'matiere__nom')
    raw_id_fields = ('etudiant', 'matiere', 'formateur', 'semestre')

# Personnalisation de l'affichage de l'Émargement dans l'admin
@admin.register(Emargement)
class EmargementAdmin(admin.ModelAdmin):
    list_display = ('formateur', 'matiere', 'date_heure_debut', 'date_heure_fin', 'duree_heures', 'salle')
    list_filter = ('formateur', 'matiere', 'salle', 'date_heure_debut')
    search_fields = ('formateur__nom', 'formateur__prenom', 'matiere__nom', 'salle')
    raw_id_fields = ('formateur', 'matiere')
    readonly_fields = ('duree_heures',)

# Personnalisation de l'affichage de l'Article dans l'admin
@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('titre', 'auteur', 'date_publication', 'est_publie', 'like_count', 'comment_count') # Afficher le comment_count
    list_filter = ('est_publie', 'auteur', 'date_publication')
    search_fields = ('titre', 'contenu', 'auteur__username', 'auteur__first_name', 'auteur__last_name')
    date_hierarchy = 'date_publication'
    raw_id_fields = ('auteur',)

    actions = ['make_published', 'make_unpublished']

    def make_published(self, request, queryset):
        updated_count = queryset.update(est_publie=True)
        self.message_user(request, f"{updated_count} article(s) marqué(s) comme publié(s).", messages.SUCCESS)
    make_published.short_description = "Marquer les articles sélectionnés comme publiés"

    def make_unpublished(self, request, queryset):
        updated_count = queryset.update(est_publie=False)
        self.message_user(request, f"{updated_count} article(s) marqué(s) comme non publié(s).", messages.WARNING)
    make_unpublished.short_description = "Marquer les articles sélectionnés comme non publiés"

# NOUVEAU: Enregistrement du modèle Like dans l'admin
@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ('user', 'article', 'date_liked')
    list_filter = ('user', 'article', 'date_liked')
    search_fields = ('user__username', 'article__titre')
    raw_id_fields = ('user', 'article')
    date_hierarchy = 'date_liked'

# NOUVEAU : Enregistrement du modèle Comment dans l'admin
@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'article', 'content', 'date_posted')
    list_filter = ('user', 'article', 'date_posted')
    search_fields = ('user__username', 'article__titre', 'content')
    raw_id_fields = ('user', 'article')
    date_hierarchy = 'date_posted'