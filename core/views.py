from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import Http404, JsonResponse # NOUVEAU: Importez JsonResponse
from django.db import transaction  # Pour gérer les transactions de base de données
from django.forms import modelform_factory  # Pour créer un formulaire simple pour le motif de rejet
from django.utils import timezone
from django.core.paginator import Paginator # NOUVEAU: Pour la pagination

from .forms import PreInscriptionForm, EmargementForm, ArticleForm, EtudiantAdminForm, InscriptionStatusForm # NOUVEAU: Importez les nouveaux formulaires
from .models import Etudiant, Inscription, Note, Coefficient, Formateur, Emargement, Article, Semestre,EmargementTemporaire, Like, Comment, Option, Niveau # NOUVEAU: Importez Option et Niveau si nécessaire
from .forms import NoteAdminForm, Matiere, MatiereAdminForm, FormateurAdminForm

# Fonctions utilitaires pour les tests d'accès
def is_formateur(user):
    """Vérifie si l'utilisateur est un formateur."""
    return hasattr(user, 'formateur') and user.formateur is not None


def is_admin(user):
    """Vérifie si l'utilisateur est un administrateur (staff)."""
    return user.is_staff


def is_etudiant_with_account(user):
    """Vérifie si l'utilisateur est lié à un profil étudiant."""
    return hasattr(user, 'etudiant') and user.etudiant is not None


def home_view(request):
    """Affiche la page d'accueil."""
    return render(request, 'core/home.html')


def pre_inscription_view(request):
    """Gère le formulaire de pré-inscription."""
    if request.method == 'POST':
        form = PreInscriptionForm(request.POST, request.FILES)
        if form.is_valid():
            etudiant = form.save(commit=False)
            etudiant.save()

            inscription = Inscription.objects.create(
                etudiant=etudiant,
                statut='PRE_INSCRIPTION'
            )

            subject = 'Confirmation de votre demande de pré-inscription'
            message = (
                f"Bonjour {etudiant.prenom},\n\n"
                "Nous avons bien reçu votre demande de pré-inscription pour l'école.\n"
                "Votre demande est en cours de traitement. Nous vous contacterons bientôt "
                "pour les prochaines étapes.\n\n"
                "Cordialement,\nL'Administration de l'École ALEXA SCHOOL"
            )
            from_email = settings.DEFAULT_FROM_EMAIL if hasattr(settings,
                                                                'DEFAULT_FROM_EMAIL') else 'noreply@example.com'
            recipient_list = [etudiant.email]

            try:
                send_mail(subject, message, from_email, recipient_list, fail_silently=False)
                print(f"E-mail de confirmation envoyé à {etudiant.email}")
            except Exception as e:
                print(f"Erreur lors de l'envoi de l'e-mail: {e}")
                messages.error(request, "Une erreur est survenue lors de l'envoi de l'e-mail de confirmation.")

            return redirect('pre_inscription_succes')
    else:
        form = PreInscriptionForm()
    return render(request, 'core/pre_inscription.html', {'form': form})


def pre_inscription_succes_view(request):
    """Affiche la page de succès de pré-inscription."""
    return render(request, 'core/pre_inscription_succes.html')


@login_required
def consultation_notes_view(request):
    """Permet aux étudiants connectés de consulter leurs notes et moyennes par semestre."""
    try:
        etudiant = Etudiant.objects.get(user=request.user)
    except Etudiant.DoesNotExist:
        return render(request, 'core/consultation_notes.html', {
            'error_message': "Votre compte n'est pas lié à un profil étudiant."
        })

    semestres = Semestre.objects.all().order_by('nom')

    selected_semestre_id = request.GET.get('semestre')
    selected_semestre = None

    notes_queryset = etudiant.note_set.all()

    if selected_semestre_id:
        try:
            selected_semestre = Semestre.objects.get(pk=selected_semestre_id)
            notes_queryset = notes_queryset.filter(semestre=selected_semestre)
        except Semestre.DoesNotExist:
            messages.warning(request, "Le semestre sélectionné n'existe pas.")
            selected_semestre_id = None

    resultat_moyenne, erreur_moyenne = etudiant.calculer_moyenne_generale(notes_queryset=notes_queryset)

    context = {
        'etudiant': etudiant,
        'notes': notes_queryset.order_by('matiere__nom'),
        'resultat_moyenne': resultat_moyenne,
        'erreur_moyenne': erreur_moyenne,
        'semestres': semestres,
        'selected_semestre': selected_semestre,
    }
    return render(request, 'core/consultation_notes.html', context)


@login_required
@user_passes_test(is_formateur, login_url='login')
def emargement_form_view(request):
    """Permet aux formateurs d'enregistrer un émargement temporaire pour validation."""
    formateur = get_object_or_404(Formateur, user=request.user)
    if request.method == 'POST':
        form = EmargementForm(request.POST, formateur=formateur)
        if form.is_valid():
            emargement_temp = form.save(commit=False)
            emargement_temp.formateur = formateur
            # Le statut par défaut est 'EN_ATTENTE' (défini dans le modèle)
            if emargement_temp.date_heure_fin <= emargement_temp.date_heure_debut:
                form.add_error('date_heure_fin', "L'heure de fin doit être après l'heure de début.")
            else:
                emargement_temp.save()
                messages.success(request, "Votre émargement a été soumis pour validation par l'administrateur.")
                return redirect('formateur_tableau_de_bord')
    else:
        form = EmargementForm(formateur=formateur)
    return render(request, 'core/emargement_form.html', {'form': form, 'formateur': formateur})


@login_required
@user_passes_test(is_formateur, login_url='login')
def formateur_tableau_de_bord_view(request):
    """Affiche le tableau de bord d'un formateur, avec les émargements validés et temporaires."""
    formateur = get_object_or_404(Formateur, user=request.user)

    # Émargements validés (ceux dans la table finale)
    emargements_valides = formateur.emargement_set.all().order_by('-date_heure_debut')

    # Émargements temporaires soumis par ce formateur
    emargements_temporaires = formateur.emargementtemporaire_set.all().order_by('-date_soumission')

    # Calcul des heures totales par mois UNIQUEMENT pour les émargements validés
    heures_par_mois = {}
    for emargement in emargements_valides:
        if emargement.duree_heures > 0:
            mois_annee = emargement.date_heure_debut.strftime('%Y-%m')
            if mois_annee not in heures_par_mois:
                heures_par_mois[mois_annee] = 0
            heures_par_mois[mois_annee] += emargement.duree_heures

    heures_par_mois_ordonne = dict(sorted(heures_par_mois.items(), reverse=True))

    context = {
        'formateur': formateur,
        'emargements_valides': emargements_valides,
        'emargements_temporaires': emargements_temporaires,
        'heures_par_mois': heures_par_mois_ordonne,
    }
    return render(request, 'core/formateur_tableau_de_bord.html', context)


@login_required
@user_passes_test(is_admin, login_url='login')
def emargement_validation_view(request):
    """
    Permet à l'administrateur de valider ou rejeter les émargements temporaires.
    """
    # Crée un formulaire dynamique pour le champ 'motif_rejet'
    MotifRejetForm = modelform_factory(EmargementTemporaire, fields=('motif_rejet',))

    emargements_en_attente = EmargementTemporaire.objects.filter(statut='EN_ATTENTE').order_by('date_soumission')
    # Les 20 derniers émargements traités (validés ou rejetés)
    emargements_traites_recent = EmargementTemporaire.objects.exclude(statut='EN_ATTENTE').order_by(
        '-date_validation_rejet')[:20]

    if request.method == 'POST':
        action = request.POST.get('action')
        record_id = request.POST.get('record_id')

        if not record_id:
            messages.error(request, "ID de l'enregistrement manquant.")
            return redirect('emargement_validation')

        try:
            emargement_temp = EmargementTemporaire.objects.get(pk=record_id)
        except EmargementTemporaire.DoesNotExist:
            messages.error(request, "Enregistrement d'émargement temporaire non trouvé.")
            return redirect('emargement_validation')

        if action == 'valider':
            try:
                with transaction.atomic():  # Assure que les deux opérations sont atomiques
                    # Créer un nouvel émargement validé dans la table finale
                    Emargement.objects.create(
                        formateur=emargement_temp.formateur,
                        matiere=emargement_temp.matiere,
                        date_heure_debut=emargement_temp.date_heure_debut,
                        date_heure_fin=emargement_temp.date_heure_fin,
                        salle=emargement_temp.salle,
                        notes=f"Validé de l'émargement temporaire (soumis par {emargement_temp.formateur.nom} {emargement_temp.formateur.prenom}): {emargement_temp.notes}"
                    )
                    # Mettre à jour le statut de l'émargement temporaire
                    emargement_temp.statut = 'VALIDE'
                    emargement_temp.date_validation_rejet = timezone.now()
                    emargement_temp.validateur = request.user
                    emargement_temp.save()
                    messages.success(request,
                                     f"Émargement du formateur {emargement_temp.formateur.nom} {emargement_temp.formateur.prenom} validé avec succès.")

                    # Envoyer un email au formateur pour confirmation de validation
                    subject = 'Validation de votre émargement - SchoolNet'
                    message = (
                        f"Bonjour {emargement_temp.formateur.prenom},\n\n"
                        f"Votre émargement du {emargement_temp.date_heure_debut.strftime('%d/%m/%Y à %H:%M')} pour la matière {emargement_temp.matiere.nom if emargement_temp.matiere else 'N/A'} a été VALIDÉ.\n"
                        "Il a été ajouté à votre compte d'heures final.\n\n"
                        "Cordialement,\nL'Administration de l'École ALEXA SCHOOL"
                    )
                    from_email = settings.DEFAULT_FROM_EMAIL
                    recipient_list = [emargement_temp.formateur.email]
                    try:
                        send_mail(subject, message, from_email, recipient_list, fail_silently=False)
                        print(f"E-mail de validation envoyé à {emargement_temp.formateur.email}")
                    except Exception as e:
                        print(f"Erreur lors de l'envoi de l'e-mail de validation: {e}")


            except Exception as e:
                messages.error(request, f"Erreur lors de la validation de l'émargement: {e}")

        elif action == 'rejeter':
            form_rejet = MotifRejetForm(request.POST, instance=emargement_temp)
            if form_rejet.is_valid():
                emargement_temp.statut = 'REJETE'
                emargement_temp.date_validation_rejet = timezone.now()
                emargement_temp.validateur = request.user
                emargement_temp.motif_rejet = form_rejet.cleaned_data.get('motif_rejet')
                emargement_temp.save()
                messages.warning(request,
                                 f"Émargement du formateur {emargement_temp.formateur.nom} {emargement_temp.formateur.prenom} rejeté.")

                # Envoyer un email au formateur pour notification de rejet
                subject = 'Rejet de votre émargement - ALEXA SCHOOL'
                message = (
                    f"Bonjour {emargement_temp.formateur.prenom},\n\n"
                    f"Votre émargement du {emargement_temp.date_heure_debut.strftime('%d/%m/%Y à %H:%M')} pour la matière {emargement_temp.matiere.nom if emargement_temp.matiere else 'N/A'} a été REJETÉ.\n"
                    f"Motif : {emargement_temp.motif_rejet if emargement_temp.motif_rejet else 'Aucun motif fourni.'}\n\n"
                    "Veuillez contacter l'administration si vous avez des questions.\n\n"
                    "Cordialement,\nL'Administration de l'École ALEXA SCHOOL"
                )
                from_email = settings.DEFAULT_FROM_EMAIL
                recipient_list = [emargement_temp.formateur.email]
                try:
                    send_mail(subject, message, from_email, recipient_list, fail_silently=False)
                    print(f"E-mail de rejet envoyé à {emargement_temp.formateur.email}")
                except Exception as e:
                    print(f"Erreur lors de l'envoi de l'e-mail de rejet: {e}")
            else:
                messages.error(request, "Veuillez fournir un motif de rejet.")

        return redirect('emargement_validation')

    context = {
        'emargements_en_attente': emargements_en_attente,
        'emargements_traites_recent': emargements_traites_recent,
        'MotifRejetForm': MotifRejetForm(),  # Passer une instance du formulaire de rejet vide
    }
    return render(request, 'core/emargement_validation.html', context)


@login_required
@user_passes_test(is_admin, login_url='login')
def rapport_heures_formateurs_view(request):
    """Affiche le rapport des heures des formateurs pour l'administration."""
    formateurs = Formateur.objects.all().order_by('nom', 'prenom')

    rapport_global = []
    for formateur in formateurs:
        mois_actuel = timezone.now().month
        annee_actuelle = timezone.now().year

        # Calcul des heures uniquement pour les émargements VALIDÉS
        emargements_du_mois = formateur.emargement_set.filter(
            date_heure_debut__year=annee_actuelle,
            date_heure_debut__month=mois_actuel
        )
        total_heures_mois = sum(e.duree_heures for e in emargements_du_mois if e.duree_heures > 0)

        # Calcul du gain mensuel
        gain_mensuel = Decimal(total_heures_mois)  * (formateur.prix_par_heure if formateur.prix_par_heure else 0)

        rapport_global.append({
            'formateur': formateur,
            'total_heures_mois': round(total_heures_mois, 2),
            'gain_mensuel': round(gain_mensuel, 2),  # NOUVEAU: Ajout du gain mensuel
            'details_emargements': emargements_du_mois.order_by('-date_heure_debut')
        })

    context = {
        'rapport_global': rapport_global,
        'mois_actuel': timezone.now().strftime('%B %Y')
    }
    return render(request, 'core/rapport_heures_formateurs.html', context)


# MODIFICATION: Vue pour gérer les likes/unlikes d'articles
@login_required
def like_article(request):
    if request.method == 'POST':
        article_id = request.POST.get('article_id')
        user = request.user

        if not article_id:
            return JsonResponse({'error': 'ID de l\'article manquant.'}, status=400)

        try:
            article = Article.objects.get(pk=article_id)

            # Vérifier si l'utilisateur a déjà liké cet article
            existing_like = Like.objects.filter(user=user, article=article).first()

            if existing_like:
                # Si l'utilisateur a déjà liké, on supprime le like (unlike)
                existing_like.delete()
                # like_count est une propriété, elle sera automatiquement à jour
                return JsonResponse({'new_like_count': article.like_count, 'liked': False})
            else:
                # Si l'utilisateur n'a pas encore liké, on crée un nouveau like
                Like.objects.create(user=user, article=article)
                # like_count est une propriété, elle sera automatiquement à jour
                return JsonResponse({'new_like_count': article.like_count, 'liked': True})

        except Article.DoesNotExist:
            return JsonResponse({'error': 'Article non trouvé.'}, status=404)
        except Exception as e:
            # Utilisez messages.error pour afficher l'erreur si besoin
            print(f"Erreur lors du like/unlike de l'article: {str(e)}")
            return JsonResponse({'error': f'Une erreur est survenue: {str(e)}'}, status=500)
    return JsonResponse({'error': 'Méthode non autorisée.'}, status=405)


def article_list_view(request):
    """
    Affiche la liste de tous les articles publiés et indique si l'utilisateur connecté
    a déjà liké chaque article.
    """
    articles = Article.objects.filter(est_publie=True).order_by('-date_publication')

    # Créer un ensemble d'IDs d'articles likés par l'utilisateur courant
    liked_article_ids = set()
    if request.user.is_authenticated:
        liked_article_ids = set(Like.objects.filter(user=request.user).values_list('article__id', flat=True))

    context = {
        'articles': articles,
        'liked_article_ids': liked_article_ids  # Passer cette information au template
    }
    return render(request, 'core/article_list.html', context)


# MODIFICATION: Vue pour afficher les détails d'un article et gérer les commentaires
def article_detail_view(request, pk):
    """
    Affiche les détails d'un article spécifique, ses commentaires
    et permet de soumettre un nouveau commentaire.
    """
    article = get_object_or_404(Article, pk=pk)

    # Vérifier si l'article est publié ou si l'utilisateur est l'auteur/admin
    if not article.est_publie and not (
            request.user.is_authenticated and (request.user == article.auteur or request.user.is_staff)):
        raise Http404("Cet article n'est pas publié ou vous n'avez pas les permissions.")

    comments = article.comments.all()  # Récupère tous les commentaires liés à cet article

    if request.method == 'POST' and request.user.is_authenticated:
        # C'est une soumission de commentaire
        content = request.POST.get('comment_content')
        if content:
            Comment.objects.create(article=article, user=request.user, content=content)
            messages.success(request, "Votre commentaire a été ajouté avec succès !")
            return redirect('article_detail', pk=article.pk)  # Rediriger pour éviter la re-soumission

    context = {
        'article': article,
        'comments': comments,  # Passer les commentaires au template
        'user_is_authenticated': request.user.is_authenticated  # Utile pour afficher le formulaire de commentaire
    }
    return render(request, 'core/article_detail.html', context)


@login_required
@user_passes_test(lambda u: u.is_staff or is_etudiant_with_account(u), login_url='login')
def article_create_update_view(request, pk=None):
    """Permet la création ou la modification d'un article."""
    article = None
    if pk:
        article = get_object_or_404(Article, pk=pk)
        if not (request.user == article.auteur or request.user.is_staff):
            messages.error(request, "Vous n'avez pas la permission de modifier cet article.")
            return redirect('article_list')

    if request.method == 'POST':
        form = ArticleForm(request.POST, request.FILES, instance=article)
        if form.is_valid():
            new_article = form.save(commit=False)
            new_article.auteur = request.user

            if request.user.is_staff:
                new_article.est_publie = form.cleaned_data['est_publie']
            else:
                new_article.est_publie = False

            new_article.save()
            messages.success(request, "Article enregistré avec succès !")
            return redirect('article_detail', pk=new_article.pk)
    else:
        form = ArticleForm(instance=article)

    return render(request, 'core/article_form.html', {'form': form, 'article': article})

@login_required
@user_passes_test(is_admin, login_url='login')
def custom_admin_dashboard_view(request):
    """
    Vue pour le tableau de bord d'administration personnalisé.
    Affiche des statistiques clés et des liens rapides.
    """
    # Importations locales pour éviter les problèmes de dépendances circulaires
    from .models import Etudiant, Formateur, Inscription, Article, EmargementTemporaire

    # Récupération des statistiques
    total_etudiants = Etudiant.objects.count()
    total_formateurs = Formateur.objects.count()
    inscriptions_en_attente = Inscription.objects.filter(statut='PRE_INSCRIPTION').count()
    articles_publies = Article.objects.filter(est_publie=True).count()
    emargements_en_attente = EmargementTemporaire.objects.filter(statut='EN_ATTENTE').count()

    context = {
        'total_etudiants': total_etudiants,
        'total_formateurs': total_formateurs,
        'inscriptions_en_attente': inscriptions_en_attente,
        'articles_publies': articles_publies,
        'emargements_en_attente': emargements_en_attente,
        'user': request.user, # Passe l'objet user au template
    }
    return render(request, 'core/custom_admin_dashboard.html', context)



# NOUVEAU: Vues pour la gestion des Étudiants dans l'admin personnalisé

@login_required
@user_passes_test(is_admin, login_url='login')
def etudiant_list_view(request):
    """Affiche la liste de tous les étudiants."""
    etudiants = Etudiant.objects.all().order_by('nom', 'prenom')
    paginator = Paginator(etudiants, 10) # 10 étudiants par page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj,
        'options': Option.objects.all(), # Pour le filtrage si nécessaire
        'niveaux': Niveau.objects.all(), # Pour le filtrage si nécessaire
    }
    return render(request, 'core/etudiant_list.html', context)

@login_required
@user_passes_test(is_admin, login_url='login')
def etudiant_form_view(request, pk=None):
    """Permet la création ou la modification d'un étudiant."""
    etudiant = None
    if pk:
        etudiant = get_object_or_404(Etudiant, pk=pk)

    if request.method == 'POST':
        form = EtudiantAdminForm(request.POST, request.FILES, instance=etudiant)
        if form.is_valid():
            form.save()
            messages.success(request, "Étudiant enregistré avec succès !")
            return redirect('custom_etudiant_list')
        else:
            messages.error(request, "Veuillez corriger les erreurs dans le formulaire.")
    else:
        form = EtudiantAdminForm(instance=etudiant)

    context = {
        'form': form,
        'etudiant': etudiant,
        'is_new': etudiant is None,
    }
    return render(request, 'core/etudiant_form.html', context)

@login_required
@user_passes_test(is_admin, login_url='login')
def etudiant_delete_view(request, pk):
    """Permet de supprimer un étudiant."""
    etudiant = get_object_or_404(Etudiant, pk=pk)
    if request.method == 'POST':
        etudiant.delete()
        messages.success(request, "Étudiant supprimé avec succès.")
        return redirect('custom_etudiant_list')
    context = {'etudiant': etudiant}
    return render(request, 'core/etudiant_confirm_delete.html', context) # Vous devrez créer ce template

# NOUVEAU: Vues pour la gestion des Inscriptions dans l'admin personnalisé

@login_required
@user_passes_test(is_admin, login_url='login')
def inscription_list_view(request):
    """Affiche la liste de toutes les inscriptions."""
    inscriptions = Inscription.objects.all().order_by('-date_demande')
    paginator = Paginator(inscriptions, 10) # 10 inscriptions par page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj,
        'InscriptionStatusForm': InscriptionStatusForm(), # Passer une instance du formulaire de statut
    }
    return render(request, 'core/inscription_list.html', context)

@login_required
@user_passes_test(is_admin, login_url='login')
def inscription_update_status_view(request, pk):
    """Permet de mettre à jour le statut d'une inscription."""
    inscription = get_object_or_404(Inscription, pk=pk)
    if request.method == 'POST':
        form = InscriptionStatusForm(request.POST, instance=inscription)
        if form.is_valid():
            inscription = form.save(commit=False)
            # Logique pour les actions personnalisées comme dans admin.py si nécessaire
            # Par exemple, si le statut devient 'INSCRIT', vous pourriez vouloir envoyer un email
            if inscription.statut == 'INSCRIT' and inscription.statut != Inscription.objects.get(pk=pk).statut:
                 # Envoyer un email avec les identifiants
                subject = 'Votre inscription est confirmée - ALEXA SCHOOL'
                message = (
                    f"Bonjour {inscription.etudiant.prenom},\n\n"
                    f"Votre inscription à l'école ALEXA SCHOOL est maintenant confirmée. "
                    f"Vos identifiants de connexion vous seront envoyés séparément ou sont les mêmes que ceux utilisés pour la pré-inscription.\n\n"
                    "Cordialement,\nL'Administration de l'École ALEXA SCHOOL"
                )
                from_email = settings.DEFAULT_FROM_EMAIL
                recipient_list = [inscription.etudiant.email]
                try:
                    send_mail(subject, message, from_email, recipient_list, fail_silently=False)
                    print(f"E-mail de confirmation d'inscription envoyé à {inscription.etudiant.email}")
                except Exception as e:
                    print(f"Erreur lors de l'envoi de l'e-mail de confirmation d'inscription: {e}")

            inscription.date_validation = timezone.now() # Mettre à jour la date de validation
            inscription.save()
            messages.success(request, f"Statut de l'inscription de {inscription.etudiant.nom} {inscription.etudiant.prenom} mis à jour à '{inscription.get_statut_display()}'.")
        else:
            messages.error(request, "Erreur lors de la mise à jour du statut.")
    return redirect('custom_inscription_list') # Redirige toujours vers la liste après l'action

# NOUVEAU: Vues pour la gestion des Formateurs dans l'admin personnalisé

@login_required
@user_passes_test(is_admin, login_url='login')
def formateur_list_view(request):
    """Affiche la liste de tous les formateurs."""
    formateurs = Formateur.objects.all().order_by('nom', 'prenom')
    paginator = Paginator(formateurs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'core/formateur_list.html', context)

@login_required
@user_passes_test(is_admin, login_url='login')
def formateur_form_view(request, pk=None):
    """Permet la création ou la modification d'un formateur."""
    formateur = None
    if pk:
        formateur = get_object_or_404(Formateur, pk=pk)

    if request.method == 'POST':
        form = FormateurAdminForm(request.POST, request.FILES, instance=formateur)
        if form.is_valid():
            form.save()
            messages.success(request, "Formateur enregistré avec succès !")
            return redirect('custom_formateur_list')
        else:
            messages.error(request, "Veuillez corriger les erreurs dans le formulaire.")
    else:
        form = FormateurAdminForm(instance=formateur)

    context = {
        'form': form,
        'formateur': formateur,
        'is_new': formateur is None,
    }
    return render(request, 'core/formateur_form.html', context)

@login_required
@user_passes_test(is_admin, login_url='login')
def formateur_delete_view(request, pk):
    """Permet de supprimer un formateur."""
    formateur = get_object_or_404(Formateur, pk=pk)
    if request.method == 'POST':
        formateur.delete()
        messages.success(request, "Formateur supprimé avec succès.")
        return redirect('custom_formateur_list')
    context = {'formateur': formateur}
    return render(request, 'core/formateur_confirm_delete.html', context)


# NOUVEAU: Vues pour la gestion des Matières dans l'admin personnalisé

@login_required
@user_passes_test(is_admin, login_url='login')
def matiere_list_view(request):
    """Affiche la liste de toutes les matières."""
    matieres = Matiere.objects.all().order_by('nom')
    paginator = Paginator(matieres, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'core/matiere_list.html', context)

@login_required
@user_passes_test(is_admin, login_url='login')
def matiere_form_view(request, pk=None):
    """Permet la création ou la modification d'une matière."""
    matiere = None
    if pk:
        matiere = get_object_or_404(Matiere, pk=pk)

    if request.method == 'POST':
        form = MatiereAdminForm(request.POST, instance=matiere)
        if form.is_valid():
            form.save()
            messages.success(request, "Matière enregistrée avec succès !")
            return redirect('custom_matiere_list')
        else:
            messages.error(request, "Veuillez corriger les erreurs dans le formulaire.")
    else:
        form = MatiereAdminForm(instance=matiere)

    context = {
        'form': form,
        'matiere': matiere,
        'is_new': matiere is None,
    }
    return render(request, 'core/matiere_form.html', context)

@login_required
@user_passes_test(is_admin, login_url='login')
def matiere_delete_view(request, pk):
    """Permet de supprimer une matière."""
    matiere = get_object_or_404(Matiere, pk=pk)
    if request.method == 'POST':
        matiere.delete()
        messages.success(request, "Matière supprimée avec succès.")
        return redirect('custom_matiere_list')
    context = {'matiere': matiere}
    return render(request, 'core/matiere_confirm_delete.html', context)


# NOUVEAU: Vues pour la gestion des Notes dans l'admin personnalisé

@login_required
@user_passes_test(is_admin, login_url='login')
def note_list_view(request):
    """Affiche la liste de toutes les notes."""
    notes = Note.objects.all().order_by('-date_saisie', 'etudiant__nom', 'matiere__nom')
    paginator = Paginator(notes, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'core/note_list.html', context)

@login_required
@user_passes_test(is_admin, login_url='login')
def note_form_view(request, pk=None):
    """Permet la création ou la modification d'une note."""
    note = None
    if pk:
        note = get_object_or_404(Note, pk=pk)

    if request.method == 'POST':
        form = NoteAdminForm(request.POST, instance=note)
        if form.is_valid():
            form.save()
            messages.success(request, "Note enregistrée avec succès !")
            return redirect('custom_note_list')
        else:
            messages.error(request, "Veuillez corriger les erreurs dans le formulaire.")
    else:
        form = NoteAdminForm(instance=note)

    context = {
        'form': form,
        'note': note,
        'is_new': note is None,
    }
    return render(request, 'core/note_form.html', context)

@login_required
@user_passes_test(is_admin, login_url='login')
def note_delete_view(request, pk):
    """Permet de supprimer une note."""
    note = get_object_or_404(Note, pk=pk)
    if request.method == 'POST':
        note.delete()
        messages.success(request, "Note supprimée avec succès.")
        return redirect('custom_note_list')
    context = {'note': note}
    return render(request, 'core/note_confirm_delete.html', context)
