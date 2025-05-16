            
    import os
import pdfplumber
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.checkbox import CheckBox
from kivy.uix.filechooser import FileChooserListView
from kivy.metrics import dp
from kivy.utils import platform
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from datetime import datetime

# Pour Android
if platform == 'android':
    from android.permissions import request_permissions, Permission
    from android.storage import app_storage_path


class ArticleSelectionPopup(Popup):
    def __init__(self, article, prix, callback, **kwargs):
        super().__init__(**kwargs)
        self.article = article
        self.prix = prix
        self.callback = callback
        
        self.title = f"Quantité pour : {article[:25]}..." if len(article) > 25 else f"Quantité pour : {article}"
        self.size_hint = (0.9, 0.4)
        
        layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        
        self.quantite_input = TextInput(
            hint_text="Quantité", 
            input_filter='int',
            multiline=False,
            size_hint_y=None,
            height=dp(50),
            font_size=20
        )
        
        btn_valider = Button(
            text="VALIDER",
            size_hint_y=None,
            height=dp(50),
            background_color=(0.2, 0.6, 1, 1))
        btn_valider.bind(on_press=self.valider)
        
        layout.add_widget(Label(text=f"Prix unitaire: {prix}", font_size=18))
        layout.add_widget(self.quantite_input)
        layout.add_widget(btn_valider)
        
        self.content = layout
    
    def valider(self, instance):
        quantite = self.quantite_input.text
        if quantite and int(quantite) > 0:
            self.callback(self.article, self.prix, int(quantite))
            self.dismiss()
        else:
            self.quantite_input.hint_text = "Quantité invalide!"
            self.quantite_input.text = ""


class PDFChooserPopup(Popup):
    def __init__(self, callback, **kwargs):
        super().__init__(**kwargs)
        self.callback = callback
        self.title = "Sélectionner le fichier PDF"
        self.size_hint = (0.9, 0.9)
        
        layout = BoxLayout(orientation='vertical')
        
        self.file_chooser = FileChooserListView(
            filters=['*.pdf'],
            size_hint=(1, 0.9)
        )
        
        btn_box = BoxLayout(size_hint_y=None, height=dp(50))
        btn_cancel = Button(text="Annuler")
        btn_select = Button(text="Sélectionner", background_color=(0.2, 0.6, 1, 1))
        
        btn_cancel.bind(on_press=self.dismiss)
        btn_select.bind(on_press=self.select_file)
        
        btn_box.add_widget(btn_cancel)
        btn_box.add_widget(btn_select)
        
        layout.add_widget(self.file_chooser)
        layout.add_widget(btn_box)
        
        self.content = layout
    
    def select_file(self, instance):
        if self.file_chooser.selection:
            self.callback(self.file_chooser.selection[0])
            self.dismiss()


class CommandeApp(App):
    def build(self):
        # Demander les permissions sur Android
        if platform == 'android':
            request_permissions([Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE])
        
        self.articles = []
        self.selection = []
        self.all_articles = []
        
        # Layout principal
        main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # SECTION CLIENT
        client_box = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(120))
        
        # Case Client
        client_box.add_widget(Label(text="[b]INFORMATIONS CLIENT[/b]", markup=True, size_hint_y=None, height=dp(30)))
        self.nom_client = TextInput(
            hint_text="Nom complet du client",
            multiline=False,
            size_hint_y=None,
            height=dp(50),
            font_size=18)
        client_box.add_widget(self.nom_client)
        
        # Case Recherche
        client_box.add_widget(Label(text="[b]RECHERCHE ARTICLE[/b]", markup=True, size_hint_y=None, height=dp(30)))
        self.recherche_input = TextInput(
            hint_text="Tapez pour rechercher un article...",
            multiline=False,
            size_hint_y=None,
            height=dp(50),
            font_size=18)
        self.recherche_input.bind(text=self.filtrer_articles)
        client_box.add_widget(self.recherche_input)
        
        main_layout.add_widget(client_box)
        
        # Bouton Charger Articles
        btn_charger = Button(
            text="CHARGER LES ARTICLES",
            size_hint_y=None,
            height=dp(60),
            background_color=(0.2, 0.6, 1, 1),
            font_size=18)
        btn_charger.bind(on_press=self.charger_articles)
        main_layout.add_widget(btn_charger)
        
        # Liste des articles
        scroll = ScrollView()
        self.liste_articles = GridLayout(
            cols=3,
            spacing=10,
            size_hint_y=None,
            row_default_height=dp(40))
        self.liste_articles.bind(minimum_height=self.liste_articles.setter('height'))
        
        # En-têtes de colonne
        self.liste_articles.add_widget(Label(text="[b]✓[/b]", markup=True))
        self.liste_articles.add_widget(Label(text="[b]ARTICLE[/b]", markup=True))
        self.liste_articles.add_widget(Label(text="[b]PRIX (DH)[/b]", markup=True))
        
        scroll.add_widget(self.liste_articles)
        main_layout.add_widget(scroll)
        
        # Bouton Générer Commande
        btn_generer = Button(
            text="GÉNÉRER LA COMMANDE PDF",
            size_hint_y=None,
            height=dp(60),
            background_color=(0.4, 0.8, 0.4, 1),
            font_size=18)
        btn_generer.bind(on_press=self.generer_commande)
        main_layout.add_widget(btn_generer)
        
        return main_layout
    
    def filtrer_articles(self, instance, value):
        if not self.all_articles:
            return
            
        search_term = value.lower().strip()
        
        if search_term:
            self.articles = [
                (article, prix) 
                for article, prix in self.all_articles 
                if search_term in article.lower()
            ]
        else:
            self.articles = self.all_articles.copy()
            
        self.mettre_a_jour_liste_articles()
    
    def mettre_a_jour_liste_articles(self):
        self.liste_articles.clear_widgets()
        
        # En-têtes
        self.liste_articles.add_widget(Label(text="[b]✓[/b]", markup=True))
        self.liste_articles.add_widget(Label(text="[b]ARTICLE[/b]", markup=True))
        self.liste_articles.add_widget(Label(text="[b]PRIX (DH)[/b]", markup=True))
        
        # Articles
        for article, prix in self.articles:
            cb = CheckBox(size_hint_x=None, width=dp(40))
            cb.active = any(item[0] == article for item in self.selection)
            cb.bind(active=lambda instance, value, a=article, p=prix: self.on_article_select(instance, value, a, p))
            
            self.liste_articles.add_widget(cb)
            self.liste_articles.add_widget(Label(text=article, font_size=16))
            self.liste_articles.add_widget(Label(text=prix, font_size=16))
    
    def charger_articles(self, instance):
        # Ouvrir le sélecteur de fichiers
        popup = PDFChooserPopup(callback=self.process_pdf)
        popup.open()
    
    def process_pdf(self, pdf_path):
        try:
            with pdfplumber.open(pdf_path) as pdf:
                self.articles = []
                for page in pdf.pages:
                    tables = page.extract_tables()
                    for table in tables:
                        for row in table:
                            if len(row) >= 2 and row[0].strip() and row[1].strip():
                                article = row[0].strip()
                                prix = row[1].strip()
                                self.articles.append((article, prix))
            
            self.all_articles = self.articles.copy()
            self.mettre_a_jour_liste_articles()
            self.show_popup("Succès", f"{len(self.articles)} articles chargés")
        
        except Exception as e:
            self.show_popup("Erreur", f"Erreur de chargement:\n{str(e)}")
    
    def on_article_select(self, instance, value, article, prix):
        if value:
            popup = ArticleSelectionPopup(
                article=article,
                prix=prix,
                callback=self.ajouter_article_quantite)
            popup.open()
        else:
            self.selection = [item for item in self.selection if item[0] != article]
    
    def ajouter_article_quantite(self, article, prix, quantite):
        for i, item in enumerate(self.selection):
            if item[0] == article:
                self.selection[i] = (article, prix, quantite)
                return
        
        self.selection.append((article, prix, quantite))
        self.mettre_a_jour_liste_articles()
    
    def generer_commande(self, instance):
        if not self.nom_client.text.strip():
            self.show_popup("Erreur", "Veuillez entrer un nom de client")
            return
        
        if not self.selection:
            self.show_popup("Erreur", "Aucun article sélectionné")
            return
        
        # Créer le dossier de commandes
        if platform == 'android':
            dossier_commandes = os.path.join(app_storage_path(), "COMMANDE_AKASYA")
        else:
            dossier_commandes = "COMMANDE_AKASYA"
            
        if not os.path.exists(dossier_commandes):
            os.makedirs(dossier_commandes)
        
        nom_client = self.nom_client.text.strip().replace(" ", "_")
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_filename = os.path.join(dossier_commandes, f"COMMANDE_{nom_client}_{date_str}.pdf")
        
        try:
            # Création du PDF
            c = canvas.Canvas(pdf_filename, pagesize=A4)
            width, height = A4
            
            # Configuration du document
            left_margin = 2 * cm
            top_margin = 2 * cm
            right_margin = 2 * cm
            
            # En-tête
            c.setFont("Helvetica-Bold", 16)
            c.drawString(left_margin, height - top_margin, "COMMANDE AKASYA")
            c.setFont("Helvetica", 12)
            c.drawString(left_margin, height - top_margin - 1*cm, f"Client: {self.nom_client.text.strip()}")
            c.drawString(left_margin, height - top_margin - 1.5*cm, f"Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
            
            # Ligne de séparation
            c.line(left_margin, height - top_margin - 2*cm, width - right_margin, height - top_margin - 2*cm)
            
            # Colonnes
            col_article = left_margin
            col_prix = col_article + 10 * cm
            col_qte = col_prix + 2 * cm
            col_total = col_qte + 2 * cm
            
            # En-têtes de colonnes
            c.setFont("Helvetica-Bold", 12)
            y_position = height - top_margin - 2.5*cm
            c.drawString(col_article, y_position, "ARTICLE")
            c.drawString(col_prix, y_position, "PRIX UNIT.")
            c.drawString(col_qte, y_position, "QTE")
            c.drawString(col_total, y_position, "TOTAL DH")
            
            # Ligne sous les en-têtes
            c.line(left_margin, y_position - 0.3*cm, width - right_margin, y_position - 0.3*cm)
            
            # Articles
            c.setFont("Helvetica", 11)
            y_position -= 1*cm
            total_general = 0
            
            for article, prix, qte in self.selection:
                try:
                    prix_clean = prix.replace(' DH', '').replace(',', '.').strip()
                    prix_num = float(prix_clean)
                    total = prix_num * qte
                    total_general += total
                    
                    c.drawString(col_article, y_position, article)
                    c.drawRightString(col_prix + 1*cm, y_position, f"{prix_num:.2f} DH")
                    c.drawRightString(col_qte + 0.5*cm, y_position, str(qte))
                    c.drawRightString(col_total + 1*cm, y_position, f"{total:.2f} DH")
                    
                    y_position -= 0.7*cm
                    
                    if y_position < 2*cm:
                        c.showPage()
                        y_position = height - top_margin - 1*cm
                        c.setFont("Helvetica", 11)
                
                except ValueError:
                    continue
            
            # Total
            c.line(left_margin, y_position - 0.5*cm, width - right_margin, y_position - 0.5*cm)
            c.setFont("Helvetica-Bold", 12)
            c.drawRightString(col_total, y_position - 1*cm, "TOTAL GENERAL:")
            c.drawRightString(col_total + 1*cm, y_position - 1*cm, f"{total_general:.2f} DH")
            
            c.save()
            
            self.show_popup("Succès", f"Commande enregistrée:\n{pdf_filename}")
            
            # Réinitialisation
            self.selection = []
            self.nom_client.text = ""
            self.recherche_input.text = ""
            
            for child in self.liste_articles.children:
                if isinstance(child, CheckBox):
                    child.active = False
        
        except Exception as e:
            self.show_popup("Erreur", f"Erreur PDF:\n{str(e)}")
    
    def show_popup(self, title, message):
        popup = Popup(
            title=title,
            content=Label(text=message, padding=20, font_size=18),
            size_hint=(0.8, 0.5))
        popup.open()


if __name__ == '__main__':
    CommandeApp().run() 
