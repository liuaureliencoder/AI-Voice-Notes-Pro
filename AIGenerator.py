import customtkinter as ctk
from tkinter import filedialog, messagebox
import whisper
import threading
import os
from pathlib import Path

# Configuration du style "Moderne"
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Le texte d'exemple qu'on veut utiliser comme Placeholder
TEXTE_PLACEHOLDER = "Ex: Réunion sur le projet Python. Vocabulaire : Google, Github, Whisper... je veux que les mots importants soient en gras."

class AINotesApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Fenêtre principale
        self.title("🎙️ AI Notes Generator - Edition Expert")
        self.geometry("950x650")

        # Configuration du Grid pour la sidebar et le contenu
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- SIDEBAR (HISTORIQUE) ---
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        self.hist_label = ctk.CTkLabel(self.sidebar, text="🕒 Historique", font=("Roboto", 18, "bold"))
        self.hist_label.pack(pady=20, padx=10)
        
        self.hist_list = ctk.CTkTextbox(self.sidebar, width=190, font=("Roboto", 11))
        self.hist_list.pack(pady=10, padx=10, fill="both", expand=True)
        self.hist_list.configure(state="disabled")

        # --- MAIN FRAME ---
        self.main_frame = ctk.CTkFrame(self, corner_radius=15)
        self.main_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")

        # Titre Principal
        self.label_title = ctk.CTkLabel(self.main_frame, text="AI Notes Generator", font=("Roboto", 28, "bold"))
        self.label_title.pack(pady=15)

        # --- RÉGLAGES (LANGUE ET DESCRIPTION) ---
        self.settings_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.settings_frame.pack(pady=10, padx=20, fill="x")

        # Label et ComboBox pour la langue
        self.lang_label = ctk.CTkLabel(self.settings_frame, text="Langue de l'audio :", font=("Roboto", 13))
        self.lang_label.grid(row=0, column=0, padx=10, sticky="w")
        
        self.lang_choice = ctk.CTkComboBox(self.settings_frame, width=160, values=["Détection Auto", "Français", "English", "Español", "Deutsch"])
        self.lang_choice.grid(row=0, column=1, padx=10)
        self.lang_choice.set("Détection Auto")

        # Label pour la description (Context Prompt)
        self.prompt_label = ctk.CTkLabel(self.main_frame, text="Décrivez le contexte (noms propres, vocabulaire technique, sujet...) :", font=("Roboto", 13, "bold"))
        self.prompt_label.pack(pady=(20, 0), padx=40, anchor="w")

        # ---------------------------------------------------------
        # ZONE DE CONTEXTE AVEC PLACEHOLDER (GHOST TEXT)
        # ---------------------------------------------------------
        self.prompt_entry = ctk.CTkTextbox(self.main_frame, height=100, width=500, font=("Roboto", 12))
        self.prompt_entry.pack(pady=10)
        
        # 1. On insère le texte par défaut et on le met en gris
        self.prompt_entry.insert("0.0", TEXTE_PLACEHOLDER)
        self.prompt_entry.configure(fg_color="#333", text_color="#777") # Gris clair
        
        # 2. On attache les événements pour gérer le focus
        self.prompt_entry.bind("<FocusIn>", self.handle_focus_in)
        self.prompt_entry.bind("<FocusOut>", self.handle_focus_out)
        self.has_real_text = False # Un petit flag pour savoir si l'utilisateur a tapé

        # --- BOUTONS ---
        self.btn_select = ctk.CTkButton(self.main_frame, text="📁 Choisir et Lancer la Transcription", 
                                        command=self.start_process, height=45, font=("Roboto", 16, "bold"))
        self.btn_select.pack(pady=15)

        # Bouton Voir (caché au début)
        self.btn_view = ctk.CTkButton(self.main_frame, text="👁️ Voir la transcription", 
                                       command=self.open_last_file, fg_color="#27ae60", hover_color="#1e8449")
        self.btn_view.pack(pady=5)
        self.btn_view.pack_forget()

        # --- LOGS ET PROGRESS ---
        self.log_view = ctk.CTkTextbox(self.main_frame, width=550, height=130, font=("Consolas", 11))
        self.log_view.pack(pady=15)
        self.add_log("Système prêt. Choisissez un fichier pour commencer.")

        self.progress_bar = ctk.CTkProgressBar(self.main_frame, width=500)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=10)

        self.model = None
        self.last_output = None

    # ---------------------------------------------------------
    # GESTION DU PLACEHOLDER (LES NOUVELLES FONCTIONS)
    # ---------------------------------------------------------
    def handle_focus_in(self, event):
        """S'exécute quand l'utilisateur clique ou tabule dans la zone."""
        current_text = self.prompt_entry.get("0.0", "end").strip()
        if current_text == TEXTE_PLACEHOLDER and not self.has_real_text:
            self.prompt_entry.delete("0.0", "end") # On efface le placeholder
            self.prompt_entry.configure(text_color="#eee") # On met la couleur de texte normale (blanc/gris clair)
            self.has_real_text = True # On marque que l'utilisateur écrit maintenant

    def handle_focus_out(self, event):
        """S'exécute quand l'utilisateur clique ailleurs."""
        current_text = self.prompt_entry.get("0.0", "end").strip()
        if current_text == "" or current_text == TEXTE_PLACEHOLDER:
            # Si c'est vide ou si c'est toujours le placeholder, on le remet
            self.prompt_entry.delete("0.0", "end")
            self.prompt_entry.insert("0.0", TEXTE_PLACEHOLDER)
            self.prompt_entry.configure(text_color="#777") # Couleur "Placeholder" (gris)
            self.has_real_text = False # Ce n'est plus du texte réel

    # ---------------------------------------------------------
    # RESTE DU CODE (FONCTIONNALITÉS IA)
    # ---------------------------------------------------------
    def add_log(self, text):
        self.log_view.configure(state="normal")
        self.log_view.insert("end", f"> {text}\n")
        self.log_view.see("end")
        self.log_view.configure(state="disabled")

    def start_process(self):
        file_path = filedialog.askopenfilename(filetypes=[("Audio", "*.mp3 *.wav *.m4a")])
        if file_path:
            self.btn_view.pack_forget()
            threading.Thread(target=self.process_audio, args=(file_path,), daemon=True).start()

    def process_audio(self, path):
        try:
            self.btn_select.configure(state="disabled")
            self.progress_bar.set(0.1)
            
            # Récupération de la langue
            lang = self.lang_choice.get()
            if lang == "Détection Auto": lang = None
            elif lang == "Français": lang = "french"
            else: lang = lang.lower()
            
            # Récupération du Prompt (on ignore le placeholder s'il est là)
            user_prompt = self.prompt_entry.get("0.0", "end").strip()
            if user_prompt == TEXTE_PLACEHOLDER:
                user_prompt = "Transcription précise." # Prompt par défaut si l'utilisateur n'a rien mis

            if not self.model:
                self.add_log("Chargement de l'IA Whisper...")
                self.model = whisper.load_model("base")
            
            self.add_log(f"Traitement lancé pour : {os.path.basename(path)}")
            self.progress_bar.set(0.4)
            
            # Transcription
            result = self.model.transcribe(path, language=lang, initial_prompt=user_prompt)
            
            # Sauvegarde
            output_name = Path(path).stem + "_Notes.md"
            with open(output_name, "w", encoding="utf-8") as f:
                f.write(f"# 📝 Compte-rendu : {os.path.basename(path)}\n\n{result['text']}")
            
            self.last_output = output_name
            self.progress_bar.set(1.0)
            self.add_log(f"✅ Terminé ! Fichier : {output_name}")
            
            # Ajout à l'historique
            self.hist_list.configure(state="normal")
            self.hist_list.insert("0.0", f"• {os.path.basename(output_name)}\n")
            self.hist_list.configure(state="disabled")
            
            self.btn_view.pack(pady=10)
            
        except Exception as e:
            self.add_log(f"❌ Erreur : {str(e)}")
        finally:
            self.btn_select.configure(state="normal")

    def open_last_file(self):
        if self.last_output: os.startfile(self.last_output)

if __name__ == "__main__":
    app = AINotesApp()
    app.mainloop()
