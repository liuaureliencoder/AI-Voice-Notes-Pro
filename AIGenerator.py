import customtkinter as ctk
from tkinter import filedialog
import whisper
import threading
import os
from pathlib import Path

# Configuration de l'interface
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Variable globale pour le texte d'aide (Placeholder)
PLACEHOLDER_TEXT = "Exemple : Réunion technique. Vocabulaire : Google, GitHub, Python. Prioriser la clarté du texte."

class AIGenerator(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configuration de la fenêtre principale
        self.title("AI Voice Notes Pro")
        self.geometry("950x650")

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Panneau latéral (Historique) ---
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        self.hist_label = ctk.CTkLabel(self.sidebar, text="Historique", font=("Roboto", 18, "bold"))
        self.hist_label.pack(pady=20, padx=10)
        
        self.hist_list = ctk.CTkTextbox(self.sidebar, width=190, font=("Roboto", 11))
        self.hist_list.pack(pady=10, padx=10, fill="both", expand=True)
        self.hist_list.configure(state="disabled")

        # --- Contenu principal ---
        self.main_frame = ctk.CTkFrame(self, corner_radius=15)
        self.main_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")

        self.label_title = ctk.CTkLabel(self.main_frame, text="AI Notes Generator", font=("Roboto", 28, "bold"))
        self.label_title.pack(pady=15)

        # --- Paramètres de transcription ---
        self.settings_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.settings_frame.pack(pady=10, padx=20, fill="x")

        self.lang_label = ctk.CTkLabel(self.settings_frame, text="Langue source :", font=("Roboto", 13))
        self.lang_label.grid(row=0, column=0, padx=10, sticky="w")
        
        self.lang_choice = ctk.CTkComboBox(self.settings_frame, width=160, values=["Détection Auto", "Français", "English", "Español"])
        self.lang_choice.grid(row=0, column=1, padx=10)
        self.lang_choice.set("Détection Auto")

        self.prompt_label = ctk.CTkLabel(self.main_frame, text="Contexte de la transcription :", font=("Roboto", 13, "bold"))
        self.prompt_label.pack(pady=(20, 0), padx=40, anchor="w")

        # --- Zone de saisie avec gestion du Placeholder ---
        self.prompt_entry = ctk.CTkTextbox(self.main_frame, height=100, width=500, font=("Roboto", 12))
        self.prompt_entry.pack(pady=10)
        
        # Initialisation du texte d'aide
        self.prompt_entry.insert("0.0", PLACEHOLDER_TEXT)
        self.prompt_entry.configure(text_color="#777") 
        
        self.prompt_entry.bind("<FocusIn>", self.handle_focus_in)
        self.prompt_entry.bind("<FocusOut>", self.handle_focus_out)
        self.placeholder_is_active = True 

        # --- Actions ---
        self.btn_select = ctk.CTkButton(self.main_frame, text="Sélectionner un fichier et transcrire", 
                                        command=self.start_process, height=45, font=("Roboto", 16, "bold"))
        self.btn_select.pack(pady=15)

        self.btn_view = ctk.CTkButton(self.main_frame, text="Ouvrir le document", 
                                       command=self.open_last_file, fg_color="#27ae60")
        self.btn_view.pack_forget()

        # --- Sortie console et progression ---
        self.log_view = ctk.CTkTextbox(self.main_frame, width=550, height=130, font=("Consolas", 11))
        self.log_view.pack(pady=15)
        self.log_event("Application prête.")

        self.progress_bar = ctk.CTkProgressBar(self.main_frame, width=500)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=10)

        self.model = None
        self.last_output_path = None

    # --- Gestion de l'interface utilisateur ---
    def handle_focus_in(self, event):
        if self.placeholder_is_active:
            self.prompt_entry.delete("0.0", "end")
            self.prompt_entry.configure(text_color="#eee")
            self.placeholder_is_active = False

    def handle_focus_out(self, event):
        if self.prompt_entry.get("0.0", "end").strip() == "":
            self.prompt_entry.insert("0.0", PLACEHOLDER_TEXT)
            self.prompt_entry.configure(text_color="#777")
            self.placeholder_is_active = True

    def log_event(self, message):
        self.log_view.configure(state="normal")
        self.log_view.insert("end", f"> {message}\n")
        self.log_view.see("end")
        self.log_view.configure(state="disabled")

    # --- Traitement des données ---
    def start_process(self):
        file_path = filedialog.askopenfilename(filetypes=[("Audio files", "*.mp3 *.wav *.m4a")])
        if file_path:
            self.btn_view.pack_forget()
            threading.Thread(target=self.run_transcription, args=(file_path,), daemon=True).start()

    def run_transcription(self, path):
        try:
            self.btn_select.configure(state="disabled")
            self.progress_bar.set(0.2)
            
            # Paramétrage de la langue
            selected_lang = self.lang_choice.get()
            lang_code = None if selected_lang == "Détection Auto" else selected_lang.lower()
            
            # Récupération du prompt
            input_prompt = "" if self.placeholder_is_active else self.prompt_entry.get("0.0", "end").strip()

            if not self.model:
                self.log_event("Chargement du modèle Whisper...")
                self.model = whisper.load_model("base")
            
            self.log_event(f"Traitement en cours : {os.path.basename(path)}")
            self.progress_bar.set(0.5)
            
            # Exécution de Whisper
            result = self.model.transcribe(path, language=lang_code, initial_prompt=input_prompt)
            
            # Exportation du résultat
            output_filename = Path(path).stem + "_Notes.md"
            with open(output_filename, "w", encoding="utf-8") as f:
                f.write(f"# Compte-rendu : {os.path.basename(path)}\n\n{result['text']}")
            
            self.last_output_path = output_filename
            self.progress_bar.set(1.0)
            self.log_event(f"Transcription terminée. Fichier généré : {output_filename}")
            
            # Mise à jour de l'historique
            self.hist_list.configure(state="normal")
            self.hist_list.insert("0.0", f"- {output_filename}\n")
            self.hist_list.configure(state="disabled")
            self.btn_view.pack(pady=10)
            
        except Exception as error:
            self.log_event(f"Erreur système : {str(error)}")
        finally:
            self.btn_select.configure(state="normal")

    def open_last_file(self):
        if self.last_output_path: 
            os.startfile(self.last_output_path)

if __name__ == "__main__":
    app = AIGenerator()
    app.mainloop()
