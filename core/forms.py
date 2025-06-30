from django import forms
from .models import Etudiant, Emargement, Matiere, Formateur, Article, Option, Niveau, Semestre, EmargementTemporaire # NOUVEAU: Importez EmargementTemporaire

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

