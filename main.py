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
from kivy.metrics import dp
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4  # Changé pour format A4
from reportlab.lib.units import cm  # Utilisation des centimètres
from datetime import datetime

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

class CommandeApp(App):
    def build(self):
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
        pdf_path = "C:\\Users\\said\\OneDrive\\Bureau\\articles.pdf"
        
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
        
        dossier_commandes = "COMMANDE AKASYA"
        if not os.path.exists(dossier_commandes):
            os.makedirs(dossier_commandes)
        
        nom_client = self.nom_client.text.strip().replace(" ", "_")
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_filename = f"{dossier_commandes}/COMMANDT_{nom_client}_{date_str}.pdf"
        
        try:
            # Format A4 avec marges en cm
            c = canvas.Canvas(pdf_filename, pagesize=A4)
            width, height = A4
            
            # Marges
            left_margin = 2 * cm
            top_margin = 2 * cm
            right_margin = 2 * cm
            
            # Calcul des largeurs de colonnes
            max_article_width = max([len(article) for article, _, _ in self.selection] + [6])  # 6 = "Article"
            max_prix_width = max([len(prix) for _, prix, _ in self.selection] + [9])  # 9 = "Prix Unit."
            max_qte_width = 5  # "Quantité"
            max_total_width = 10  # "Total DH"
            
            # Définition des positions des colonnes
            col_article = left_margin
            col_prix = col_article + (max_article_width * 0.3 * cm)
            col_qte = col_prix + (max_prix_width * 0.3 * cm)
            col_total = col_qte + (max_qte_width * 0.5 * cm)
            
            # En-tête du document
            c.setFont("Helvetica-Bold", 16)
            c.drawString(left_margin, height - top_margin, "COMMANDE AKASYA")
            c.setFont("Helvetica", 12)
            c.drawString(left_margin, height - top_margin - 1*cm, f"Client: {self.nom_client.text.strip()}")
            c.drawString(left_margin, height - top_margin - 1.5*cm, f"Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
            
            # Ligne de séparation
            c.line(left_margin, height - top_margin - 2*cm, width - right_margin, height - top_margin - 2*cm)
            
            # En-têtes de colonnes
            c.setFont("Helvetica-Bold", 12)
            y_position = height - top_margin - 2.5*cm
            c.drawString(col_article, y_position, "ARTICLE")
            c.drawString(col_prix, y_position, "PRIX UNIT.")
            c.drawString(col_qte, y_position, "QTE")
            c.drawString(col_total, y_position, "TOTAL DH")
            
            # Ligne sous les en-têtes
            c.line(left_margin, y_position - 0.3*cm, width - right_margin, y_position - 0.3*cm)
            
            # Contenu des articles
            c.setFont("Helvetica", 11)
            y_position -= 1*cm
            total_general = 0
            
            for article, prix, qte in self.selection:
                try:
                    # Nettoyage et conversion du prix
                    prix_clean = prix.replace(' DH', '').replace(',', '.').strip()
                    prix_num = float(prix_clean)
                    total = prix_num * qte
                    total_general += total
                    
                    # Affichage des données
                    c.drawString(col_article, y_position, article)
                    c.drawRightString(col_prix + max_prix_width*0.2*cm, y_position, f"{prix_num:.2f} DH")
                    c.drawRightString(col_qte + max_qte_width*0.2*cm, y_position, str(qte))
                    c.drawRightString(col_total + max_total_width*0.2*cm, y_position, f"{total:.2f} DH")
                    
                    y_position -= 0.7*cm
                    
                    # Saut de page si nécessaire
                    if y_position < 2*cm:
                        c.showPage()
                        y_position = height - top_margin - 1*cm
                        c.setFont("Helvetica", 11)
                
                except ValueError:
                    continue
            
            # Ligne de total
            c.line(left_margin, y_position - 0.5*cm, width - right_margin, y_position - 0.5*cm)
            
            # Total général
            c.setFont("Helvetica-Bold", 12)
            c.drawRightString(col_total, y_position - 1*cm, "TOTAL GENERAL:")
            c.drawRightString(col_total + max_total_width*0.2*cm, y_position - 1*cm, f"{total_general:.2f} DH")
            
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
