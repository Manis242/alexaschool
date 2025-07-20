from django import forms
from .models import Etudiant, Emargement, Matiere, Formateur, Article, Option, Niveau, Semestre, EmargementTemporaire # NOUVEAU: Importez EmargementTemporaire
from .models import Etudiant, Inscription,Formateur, Matiere, Note

class PreInscriptionForm(forms.ModelForm):
    class Meta:
        model = Etudiant
        fields = [
            'nom', 'prenom', 'date_naissance', 'lieu_naissance', 'sexe',
            'email', 'telephone', 'adresse', 'option', 'niveau',
            'dernier_diplome', 'motivations', 'photo_de_profil'
        ]
        widgets = {
            'date_naissance': forms.DateInput(attrs={'type': 'date'}),
            'motivations': forms.Textarea(attrs={'rows': 5}),
        }
        labels = {
            'nom': "Nom",
            'prenom': "Prénom",
            'date_naissance': "Date de naissance",
            'lieu_naissance': "Lieu de naissance",
            'sexe': "Sexe",
            'email': "Adresse e-mail",
            'telephone': "Numéro de téléphone",
            'adresse': "Adresse postale",
            'option': "Option choisie",
            'niveau': "Niveau d'études",
            'dernier_diplome': "Dernier diplôme obtenu",
            'motivations': "Vos motivations pour nous rejoindre",
            'photo_de_profil': "Photo de profil",
        }

# EmargementForm (MODIFIÉ pour cibler EmargementTemporaire)
class EmargementForm(forms.ModelForm):
    class Meta:
        model = EmargementTemporaire # MODIFIÉ: Cible EmargementTemporaire
        fields = ['matiere', 'date_heure_debut', 'date_heure_fin', 'salle', 'notes']
        widgets = {
            'date_heure_debut': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'date_heure_fin': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
        }
        labels = {
            'matiere': "Matière enseignée",
            'date_heure_debut': "Date et heure de début",
            'date_heure_fin': "Date et heure de fin",
            'salle': "Salle de cours",
            'notes': "Notes additionnelles",
        }

    def __init__(self, *args, **kwargs):
        self.formateur = kwargs.pop('formateur', None)
        super().__init__(*args, **kwargs)
        if self.formateur:
            self.fields['matiere'].queryset = self.formateur.matieres.all()
        else:
            self.fields['matiere'].queryset = Matiere.objects.none()

class ArticleForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = ['titre', 'contenu', 'image', 'est_publie']
        labels = {
            'titre': "Titre de l'article",
            'contenu': "Contenu de l'article",
            'image': "Image de l'article",
            'est_publie': "Publier l'article (visible par tous)",
        }
        widgets = {
            'contenu': forms.Textarea(attrs={'rows': 10}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'instance' in kwargs and kwargs['instance']:
            if kwargs['instance'].auteur and not kwargs['instance'].auteur.is_staff:
                self.fields['est_publie'].widget.attrs['disabled'] = True
                self.fields['est_publie'].help_text = "Seuls les administrateurs peuvent publier directement ou modifier le statut de publication."
        elif 'request' in kwargs:
            if not kwargs['request'].user.is_staff:
                self.fields['est_publie'].widget.attrs['disabled'] = True
                self.fields['est_publie'].help_text = "Votre article sera soumis à validation avant publication."


# Formulaire pour la gestion des étudiants dans l'admin personnalisé
class EtudiantAdminForm(forms.ModelForm):
    class Meta:
        model = Etudiant
        # Exposez tous les champs pertinents pour l'administration
        fields = [
            'user', 'nom', 'prenom', 'matricule', 'date_naissance', 'sexe',
            'adresse', 'telephone', 'email', 'dernier_diplome', 'option',
            'niveau', 'photo_de_profil'
        ]
        widgets = {
            'date_naissance': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Rendez le champ 'user' optionnel si vous ne voulez pas toujours lier un utilisateur existant
        # Ou ajoutez une logique pour créer un utilisateur si non fourni
        self.fields['user'].required = False
        # Ajoutez des classes Tailwind pour un meilleur style
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2'


# Formulaire pour la mise à jour du statut d'inscription
class InscriptionStatusForm(forms.ModelForm):
    class Meta:
        model = Inscription
        fields = ['statut']
        widgets = {
            'statut': forms.Select(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Vous pouvez limiter les choix de statut si nécessaire
        # self.fields['statut'].choices = [('EN_ATTENTE_PAIEMENT', 'En attente de paiement'), ('INSCRIT', 'Inscrit'), ('ANNULE', 'Annulé')]

# NOUVEAU: Formulaire pour la gestion des formateurs dans l'admin personnalisé
class FormateurAdminForm(forms.ModelForm):
    class Meta:
        model = Formateur
        fields = [
            'user', 'nom', 'prenom', 'code_formateur', 'email', 'telephone',
            'date_embauche', 'matieres', 'prix_par_heure'
        ]
        widgets = {
            'date_embauche': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user'].required = False
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2'
        # Pour les champs ManyToMany (matieres), vous pouvez utiliser CheckboxSelectMultiple ou un widget personnalisé
        # self.fields['matieres'].widget = forms.CheckboxSelectMultiple()


# NOUVEAU: Formulaire pour la gestion des matières dans l'admin personnalisé
class MatiereAdminForm(forms.ModelForm):
    class Meta:
        model = Matiere
        fields = ['nom', 'description'] # Ajoutez d'autres champs si votre modèle Matiere en a
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2'}),
            'description': forms.Textarea(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2', 'rows': 3}),
        }


# NOUVEAU: Formulaire pour la gestion des notes dans l'admin personnalisé
class NoteAdminForm(forms.ModelForm):
    class Meta:
        model = Note
        fields = ['etudiant', 'matiere', 'valeur', 'semestre', 'formateur']
        widgets = {
            #'date_saisie': forms.DateInput(attrs={'type': 'date'}),
            'etudiant': forms.Select(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2'}),
            'matiere': forms.Select(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2'}),
            'semestre': forms.Select(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2'}),
            'formateur': forms.Select(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2'}),
            'valeur': forms.NumberInput(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2', 'step': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name not in ['date_saisie', 'valeur']: # Ces champs ont déjà des widgets spécifiques
                field.widget.attrs['class'] = 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2'
