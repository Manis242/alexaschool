from django.db import models
from django.contrib.auth.models import User
import uuid
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.db.models import Sum, F
from datetime import timedelta

# NOUVEAU MODÈLE: Semestre
class Semestre(models.Model):
    nom = models.CharField(max_length=100, unique=True, verbose_name="Nom du semestre")
    date_debut = models.DateField(verbose_name="Date de début")
    date_fin = models.DateField(verbose_name="Date de fin")

    class Meta:
        verbose_name = "Semestre"
        verbose_name_plural = "Semestres"
        ordering = ['nom'] # Trie par nom par défaut

    def __str__(self):
        return self.nom

# Modèle pour les options (ex: Informatique, Gestion, Marketing)
class Option(models.Model):
    nom = models.CharField(max_length=100, unique=True, verbose_name="Nom de l'option")
    description = models.TextField(blank=True, null=True, verbose_name="Description")

    class Meta:
        verbose_name = "Option"
        verbose_name_plural = "Options"
        ordering = ['nom']

    def __str__(self):
        return self.nom

# Modèle pour les niveaux (ex: L1, L2, L3, M1, M2)
class Niveau(models.Model):
    nom = models.CharField(max_length=50, unique=True, verbose_name="Nom du niveau")
    description = models.TextField(blank=True, null=True, verbose_name="Description")

    class Meta:
        verbose_name = "Niveau"
        verbose_name_plural = "Niveaux"
        ordering = ['nom']

    def __str__(self):
        return self.nom

# Matiere
class Matiere(models.Model):
    nom = models.CharField(max_length=100, unique=True, verbose_name="Nom de la matière")
    description = models.TextField(blank=True, null=True, verbose_name="Description")

    class Meta:
        verbose_name = "Matière"
        verbose_name_plural = "Matières"
        ordering = ['nom']

    def __str__(self):
        return self.nom

# Formateur (MODIFICATION: Ajout de la logique de création de compte utilisateur)
class Formateur(models.Model):
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Compte utilisateur (optionnel)")
    nom = models.CharField(max_length=100, verbose_name="Nom")
    prenom = models.CharField(max_length=100, verbose_name="Prénom")
    code_formateur = models.CharField(max_length=20, unique=True, verbose_name="Code Formateur")
    email = models.EmailField(unique=True, verbose_name="Email")
    telephone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Téléphone")
    date_embauche = models.DateField(verbose_name="Date d'embauche")
    matieres = models.ManyToManyField(Matiere, blank=True, verbose_name="Matières enseignées")
    prix_par_heure = models.DecimalField(max_digits=8, decimal_places=2, default=0.00, verbose_name="Prix par heure (FCFA)")  # NOUVEAU: Prix par heure

    class Meta:
        verbose_name = "Formateur"
        verbose_name_plural = "Formateurs"
        ordering = ['nom', 'prenom']

    def __str__(self):
        return f"{self.nom} {self.prenom} ({self.code_formateur})"

    def save(self, *args, **kwargs):
        is_new_formateur = not self.pk # Vérifie si c'est une nouvelle instance
        original_user_id = None
        if self.pk:
            try:
                original_formateur = Formateur.objects.get(pk=self.pk)
                original_user_id = original_formateur.user_id
            except Formateur.DoesNotExist:
                pass # Ne devrait pas arriver si self.pk existe

        super().save(*args, **kwargs) # Sauvegarde l'instance Formateur pour que self.pk existe

        # Créer un compte utilisateur si l'e-mail est renseigné et qu'aucun utilisateur n'est lié
        # OU si un utilisateur a été délié et qu'un e-mail est toujours présent
        if self.email and not self.user:
            username = self.code_formateur # Utilise le code_formateur comme nom d'utilisateur
            password = str(uuid.uuid4())[:8] # Génère un mot de passe aléatoire court

            try:
                user, created = User.objects.get_or_create(username=username, defaults={'email': self.email})
                if created:
                    user.set_password(password) # Définit le mot de passe (qui sera haché)
                    user.first_name = self.prenom
                    user.last_name = self.nom
                    user.save()
                    self.user = user # Lie l'utilisateur créé au formateur
                    self.save(update_fields=['user']) # Sauvegarde le formateur pour persister le lien User
                    print(f"Compte utilisateur créé pour le formateur {self.nom} {self.prenom}. Nom d'utilisateur: {username}, Mot de passe: {password}")

                    # Envoi de l'e-mail avec les identifiants
                    subject = 'Vos identifiants de connexion Formateur - ALEXA-SCHOOL'
                    message = (
                        f"Bonjour {self.prenom},\n\n"
                        "Votre compte formateur sur SchoolNet a été créé.\n"
                        "Vous pouvez vous connecter avec les identifiants suivants :\n\n"
                        f"  - **Adresse du site :** http://127.0.0.1:8000/login/\n"
                        f"  - **Votre identifiant :** {username}\n"
                        f"  - **Votre mot de passe :** {password}\n\n"
                        "Pour des raisons de sécurité, nous vous recommandons fortement de changer votre mot de passe après votre première connexion.\n\n"
                        "Cordialement,\nL'Administration de l'École ALEXA-SCHOOL"
                    )
                    from_email = settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@example.com'
                    recipient_list = [self.email]
                    try:
                        send_mail(subject, message, from_email, recipient_list, fail_silently=False)
                        print(f"E-mail de connexion envoyé à {self.email} pour le formateur.")
                    except Exception as e:
                        print(f"Erreur lors de l'envoi de l'e-mail de connexion au formateur: {e}")
                else:
                    # L'utilisateur existe déjà avec ce nom d'utilisateur, s'assurer qu'il est lié et à jour
                    if user.email != self.email:
                        user.email = self.email
                        user.save()
                    if self.user != user:
                        self.user = user
                        self.save(update_fields=['user'])
                    print(f"Compte utilisateur pour le formateur {self.nom} {self.prenom} existe déjà et est lié/mis à jour.")

            except Exception as e:
                print(f"Erreur lors de la création/liaison de l'utilisateur pour le formateur {self.email}: {e}")

# Etudiant
class Etudiant(models.Model):
    SEXE_CHOICES = [
        ('M', 'Masculin'),
        ('F', 'Féminin'),
        ('AUTRE', 'Autre'),
    ]
    DIPLOME_CHOICES = [
        ('AUCUN', 'Aucun'),
        ('BEPC', 'BEPC'),
        ('BACCALAUREAT', 'Baccalauréat'),
        ('BTS', 'BTS / DUT'),
        ('LICENCE', 'Licence'),
        ('MASTER', 'Master'),
        ('DOCTORAT', 'Doctorat'),
        ('AUTRE', 'Autre'),
    ]

    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Compte utilisateur (optionnel)")
    nom = models.CharField(max_length=100, verbose_name="Nom")
    prenom = models.CharField(max_length=100, verbose_name="Prénom")
    date_naissance = models.DateField(verbose_name="Date de naissance")
    lieu_naissance = models.CharField(max_length=100, blank=True, null=True, verbose_name="Lieu de naissance")
    matricule = models.CharField(max_length=50, unique=True, blank=True, null=True, verbose_name="Numéro Matricule")
    email = models.EmailField(unique=True, verbose_name="Email de l'étudiant")
    telephone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Téléphone")
    adresse = models.CharField(max_length=255, blank=True, null=True, verbose_name="Adresse")
    photo_de_profil = models.ImageField(upload_to='photos_profil/', blank=True, null=True, verbose_name="Photo de profil")

    sexe = models.CharField(max_length=10, choices=SEXE_CHOICES, verbose_name="Sexe", default='AUTRE')
    dernier_diplome = models.CharField(max_length=50, choices=DIPLOME_CHOICES, blank=True, null=True, verbose_name="Dernier diplôme obtenu")
    motivations = models.TextField(blank=True, null=True, verbose_name="Vos motivations pour nous rejoindre")

    option = models.ForeignKey(Option, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Option")
    niveau = models.ForeignKey(Niveau, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Niveau")

    class Meta:
        verbose_name = "Étudiant"
        verbose_name_plural = "Étudiants"
        ordering = ['nom', 'prenom']

    def __str__(self):
        return f"{self.nom} {self.prenom} ({self.matricule if self.matricule else 'Non inscrit'})"

    def calculer_moyenne_generale(self, notes_queryset=None):
        """
        Calcule la moyenne générale de l'étudiant en fonction de ses notes
        (optionnellement filtrées par semestre) et des coefficients des matières
        pour son option et niveau.
        """
        if not self.option or not self.niveau:
            return None, "L'étudiant n'a pas d'option ou de niveau défini."

        if notes_queryset is None:
            notes = self.note_set.all()
        else:
            notes = notes_queryset

        if not notes.exists():
            return None, "Aucune note enregistrée pour cet étudiant (ou pour le semestre sélectionné)."

        total_points = 0
        total_coefficients = 0
        details_notes = []

        for note in notes:
            try:
                coefficient = Coefficient.objects.get(
                    matiere=note.matiere,
                    option=self.option,
                    niveau=self.niveau
                )
                points_matiere = note.valeur * coefficient.valeur
                total_points += points_matiere
                total_coefficients += coefficient.valeur
                details_notes.append({
                    'matiere': note.matiere.nom,
                    'note': note.valeur,
                    'coefficient': coefficient.valeur,
                    'points': points_matiere
                })
            except Coefficient.DoesNotExist:
                details_notes.append({
                    'matiere': note.matiere.nom,
                    'note': note.valeur,
                    'coefficient': 'N/A',
                    'points': 'N/A',
                    'erreur': "Coefficient non trouvé pour cette matière, option et niveau."
                })
                continue

        if total_coefficients == 0:
            return None, "Aucun coefficient valide trouvé pour le calcul de la moyenne."

        moyenne = total_points / total_coefficients
        mention = self._determiner_mention(moyenne)

        return {
            'moyenne': round(moyenne, 2),
            'mention': mention,
            'details': details_notes
        }, None

    def _determiner_mention(self, moyenne):
        """Détermine la mention en fonction de la moyenne."""
        if moyenne >= 16:
            return "Très Bien"
        elif moyenne >= 14:
            return "Bien"
        elif moyenne >= 12:
            return "Assez Bien"
        elif moyenne >= 10:
            return "Passable"
        else:
            return "Insuffisant"

# Inscription
class Inscription(models.Model):
    STATUT_CHOICES = [
        ('PRE_INSCRIPTION', 'Pré-inscription'),
        ('EN_ATTENTE_PAIEMENT', 'En attente de paiement'),
        ('INSCRIT', 'Inscrit'),
        ('ANNULE', 'Annulé'),
    ]

    etudiant = models.OneToOneField(Etudiant, on_delete=models.CASCADE, verbose_name="Étudiant")
    date_demande = models.DateTimeField(auto_now_add=True, verbose_name="Date de la demande")
    date_validation = models.DateTimeField(null=True, blank=True, verbose_name="Date de validation")
    statut = models.CharField(max_length=50, choices=STATUT_CHOICES, default='PRE_INSCRIPTION', verbose_name="Statut de l'inscription")
    montant_paye = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Montant payé")

    class Meta:
        verbose_name = "Inscription"
        verbose_name_plural = "Inscriptions"
        ordering = ['-date_demande']

    def __str__(self):
        return f"Inscription de {self.etudiant.nom} {self.etudiant.prenom} - Statut: {self.statut}"

    def save(self, *args, **kwargs):
        original_status = None
        if self.pk:
            try:
                original_inscription = Inscription.objects.get(pk=self.pk)
                original_status = original_inscription.statut
            except Inscription.DoesNotExist:
                pass

        super().save(*args, **kwargs)

        if original_status == 'PRE_INSCRIPTION' and self.statut == 'EN_ATTENTE_PAIEMENT':
            if not self.etudiant.matricule:
                self.etudiant.matricule = str(uuid.uuid4()).replace('-', '')[:10].upper()
                self.etudiant.save()
            self.date_validation = timezone.now()

            subject = 'Votre demande d\'inscription a été validée - Veuillez procéder au paiement'
            message = (
                f"Bonjour {self.etudiant.prenom},\n\n"
                "Nous avons bien reçu votre demande de pré-inscription pour l'école ALEXA SCHOOL.\n"
                "Votre demande est en cours de traitement. Nous vous contacterons bientôt "
                "pour les prochaines étapes.\n\n"
                "Cordialement,\nL'Administration de l'École ALEXA SCHOOL"
            )
            from_email = settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@example.com'
            recipient_list = [self.etudiant.email]
            try:
                send_mail(subject, message, from_email, recipient_list, fail_silently=False)
                print(f"E-mail de demande de paiement envoyé à {self.etudiant.email}")
            except Exception as e:
                print(f"Erreur lors de l'envoi de l'e-mail de paiement: {e}")

        if (original_status in ['EN_ATTENTE_PAIEMENT', 'PRE_INSCRIPTION'] and self.statut == 'INSCRIT'):
            if not self.etudiant.matricule:
                self.etudiant.matricule = str(uuid.uuid4()).replace('-', '')[:10].upper()
                self.etudiant.save()

            if not self.etudiant.user:
                user = User.objects.create_user(
                    username=self.etudiant.matricule,
                    email=self.etudiant.email,
                    password=self.etudiant.matricule
                )
                self.etudiant.user = user
                self.etudiant.save()
            else:
                user = self.etudiant.user
                if user.username != self.etudiant.matricule:
                    user.username = self.etudiant.matricule
                user.set_password(self.etudiant.matricule)
                user.email = self.etudiant.email
                user.save()

            subject = 'ALEXA SCHOOL : Confirmation de votre inscription - Vos identifiants de connexion'
            message = (
                f"Bonjour {self.etudiant.prenom},\n\n"
                "Votre inscription a été confirmée ! Nous sommes ravis de vous accueillir dans notre école.\n"
                "Vous pouvez désormais vous connecter à votre espace étudiant avec les informations suivantes :\n\n"
                f"  - **Adresse du site :** http://127.0.0.1:8000/login/\n"
                f"  - **Votre identifiant (Matricule) :** {self.etudiant.matricule}\n"
                f"  - **Votre mot de passe :** {self.etudiant.matricule}\n\n"
                "Pour des raisons de sécurité, nous vous recommandons fortement de changer votre mot de passe après votre première connexion.\n\n"
                "Cordialement,\nL'Administration de l'École ALEXA SCHOOL"
            )
            from_email = settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@example.com'
            recipient_list = [self.etudiant.email]
            try:
                send_mail(subject, message, from_email, recipient_list, fail_silently=False)
                print(f"E-mail de confirmation d'inscription et identifiants envoyé à {self.etudiant.email}")
            except Exception as e:
                print(f"Erreur lors de l'envoi de l'e-mail de confirmation d'inscription: {e}")

# Coefficient
class Coefficient(models.Model):
    matiere = models.ForeignKey(Matiere, on_delete=models.CASCADE, verbose_name="Matière")
    option = models.ForeignKey(Option, on_delete=models.CASCADE, verbose_name="Option")
    niveau = models.ForeignKey(Niveau, on_delete=models.CASCADE, verbose_name="Niveau")
    valeur = models.DecimalField(max_digits=4, decimal_places=2, verbose_name="Valeur du coefficient")

    class Meta:
        verbose_name = "Coefficient"
        verbose_name_plural = "Coefficients"
        unique_together = ('matiere', 'option', 'niveau')

    def __str__(self):
        return f"Coef. {self.valeur} pour {self.matiere.nom} en {self.option.nom} ({self.niveau.nom})"

# Note (MODIFICATION)
class Note(models.Model):
    etudiant = models.ForeignKey(Etudiant, on_delete=models.CASCADE, verbose_name="Étudiant")
    matiere = models.ForeignKey(Matiere, on_delete=models.CASCADE, verbose_name="Matière")
    formateur = models.ForeignKey(Formateur, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Formateur (optionnel)")
    valeur = models.DecimalField(max_digits=4, decimal_places=2, verbose_name="Valeur de la note")
    date_saisie = models.DateTimeField(auto_now_add=True, verbose_name="Date de saisie")
    semestre = models.ForeignKey(Semestre, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Semestre")

    class Meta:
        verbose_name = "Note"
        verbose_name_plural = "Notes"
        unique_together = ('etudiant', 'matiere')
        ordering = ['etudiant__nom', 'etudiant__prenom', 'semestre__nom', 'matiere__nom']

    def __str__(self):
        return f"Note de {self.valeur} pour {self.etudiant.nom} en {self.matiere.nom} ({self.semestre.nom if self.semestre else 'N/A'})"

# Emargement (TABLE FINALE)
class Emargement(models.Model):
    formateur = models.ForeignKey(Formateur, on_delete=models.CASCADE, verbose_name="Formateur")
    matiere = models.ForeignKey(Matiere, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Matière enseignée")
    date_heure_debut = models.DateTimeField(verbose_name="Date et heure de début")
    date_heure_fin = models.DateTimeField(verbose_name="Date et heure de fin")
    salle = models.CharField(max_length=100, blank=True, null=True, verbose_name="Salle de cours")
    notes = models.TextField(blank=True, null=True, verbose_name="Notes additionnelles")

    class Meta:
        verbose_name = "Émargement"
        verbose_name_plural = "Émargements"
        ordering = ['-date_heure_debut']

    def __str__(self):
        return f"Émargement de {self.formateur.nom} {self.formateur.prenom} le {self.date_heure_debut.strftime('%Y-%m-%d %H:%M')}"

    @property
    def duree_heures(self):
        """Calcule la durée du cours en heures."""
        if self.date_heure_debut and self.date_heure_fin:
            duration = self.date_heure_fin - self.date_heure_debut
            return round(duration.total_seconds() / 3600, 2)
        return 0

# NOUVEAU MODÈLE: EmargementTemporaire (pour la validation par l'administrateur)
class EmargementTemporaire(models.Model):
    STATUT_VALIDATION_CHOICES = [
        ('EN_ATTENTE', 'En attente de validation'),
        ('VALIDE', 'Validé'),
        ('REJETE', 'Rejeté'),
    ]

    formateur = models.ForeignKey(Formateur, on_delete=models.CASCADE, verbose_name="Formateur")
    matiere = models.ForeignKey(Matiere, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Matière enseignée")
    date_heure_debut = models.DateTimeField(verbose_name="Date et heure de début")
    date_heure_fin = models.DateTimeField(verbose_name="Date et heure de fin")
    salle = models.CharField(max_length=100, blank=True, null=True, verbose_name="Salle de cours")
    notes = models.TextField(blank=True, null=True, verbose_name="Notes additionnelles (du formateur)")
    statut = models.CharField(max_length=20, choices=STATUT_VALIDATION_CHOICES, default='EN_ATTENTE', verbose_name="Statut de validation")
    date_soumission = models.DateTimeField(auto_now_add=True, verbose_name="Date de soumission")
    date_validation_rejet = models.DateTimeField(null=True, blank=True, verbose_name="Date de validation/rejet")
    motif_rejet = models.TextField(blank=True, null=True, verbose_name="Motif de rejet (si applicable)")
    validateur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Validateur/Rejeteur", related_name='emargements_valides_rejetes')

    class Meta:
        verbose_name = "Émargement Temporaire"
        verbose_name_plural = "Émargements Temporaires"
        ordering = ['-date_soumission']

    def __str__(self):
        return f"Emargement temporaire de {self.formateur.nom} le {self.date_soumission.strftime('%Y-%m-%d %H:%M')} ({self.statut})"

    @property
    def duree_heures(self):
        """Calcule la durée du cours en heures."""
        if self.date_heure_debut and self.date_heure_fin:
            duration = self.date_heure_fin - self.date_heure_debut
            return round(duration.total_seconds() / 3600, 2)
        return 0

# Article
class Article(models.Model):
    TITRE_MAX_LENGTH = 200
    CONTENU_MAX_LENGTH = 5000

    titre = models.CharField(max_length=TITRE_MAX_LENGTH, verbose_name="Titre de l'article")
    contenu = models.TextField(verbose_name="Contenu de l'article")
    date_publication = models.DateTimeField(auto_now_add=True, verbose_name="Date de publication")
    auteur = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Auteur")
    est_publie = models.BooleanField(default=False, verbose_name="Est publié")
    image = models.ImageField(upload_to='article_images/', blank=True, null=True, verbose_name="Image de l'article")

    # like_count est désormais calculé via les relations, pas un champ direct
    # Si vous voulez garder un champ pour un cache ou un affichage rapide, il faudrait le synchroniser
    # Pour l'instant, on va le considérer comme un champ "virtuel" ou basé sur le comptage des Likes

    class Meta:
        verbose_name = "Article"
        verbose_name_plural = "Articles"
        ordering = ['-date_publication']

    def __str__(self):
        return self.titre

    @property
    def like_count(self):
        """Retourne le nombre de likes pour cet article."""
        return self.likes.count()  # Compte les objets Like liés à cet article

    @property
    def comment_count(self):
        """Retourne le nombre de commentaires pour cet article."""
        return self.comments.count()  # NOUVEAU: Compte les objets Comment liés à cet article


# NOUVEAU MODÈLE: Like
class Like(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Utilisateur")
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='likes', verbose_name="Article")
    date_liked = models.DateTimeField(auto_now_add=True, verbose_name="Date du j'aime")

    class Meta:
        verbose_name = "J'aime"
        verbose_name_plural = "J'aime"
        # Empêche un utilisateur de liker le même article plusieurs fois
        unique_together = ('user', 'article')
        ordering = ['-date_liked']

    def __str__(self):
        return f"{self.user.username} aime '{self.article.titre}'"

# NOUVEAU MODÈLE: Comment
class Comment(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='comments', verbose_name="Article")
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Utilisateur")
    content = models.TextField(verbose_name="Contenu du commentaire")
    date_posted = models.DateTimeField(auto_now_add=True, verbose_name="Date de publication")

    class Meta:
        verbose_name = "Commentaire"
        verbose_name_plural = "Commentaires"
        ordering = ['date_posted'] # Trie par date croissante

    def __str__(self):
        return f"Commentaire de {self.user.username} sur '{self.article.titre}'"
