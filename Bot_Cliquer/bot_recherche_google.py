import json
import os
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# Charger les variables d'environnement
load_dotenv()

# Configurer les options pour le navigateur
options = webdriver.ChromeOptions()
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36")

# Charger les configurations du .env
domaines_cibles = os.getenv("DOMAINES_CIBLES").split(",")
domaine_a_ignorer = os.getenv("DOMAINE_A_IGNORER").split(",")
mots_cles = os.getenv("MOTS_CLES").split(",")
log_level = os.getenv("LOG_LEVEL", "INFO")

# Nom du fichier pour sauvegarder les statistiques
json_filename = "search_data.json"

# Charger les données de recherche existantes ou initialiser
if os.path.exists(json_filename):
    with open(json_filename, "r", encoding="utf-8") as file:
        search_data = json.load(file)
else:
    search_data = {}

# Fonction de log en fonction du niveau défini
def log_message(level, message):
    if log_level == "DEBUG" or level == "INFO":
        print(f"[{level}] {message}")

# Fonction pour sauvegarder les données
def sauvegarder_donnees():
    with open(json_filename, "w", encoding="utf-8") as file:
        json.dump(search_data, file, indent=4, ensure_ascii=False)

# Fonction pour enregistrer les statistiques pour chaque requête
def enregistrer_statistiques(requete, page_number, position, url, domaine_cible, visited):
    if requete not in search_data:
        search_data[requete] = []
    
    search_data[requete].append({
        "page": page_number,
        "position": position,
        "url": url,
        "domaine_cible": domaine_cible,
        "visited": visited
    })
    log_message("INFO", f"Données enregistrées : {{'page': {page_number}, 'position': {position}, 'url': '{url}', 'domaine_cible': {domaine_cible}, 'visited': {visited}}}")

# Demander le nombre d'itérations à l'utilisateur
iterations = int(input("[ACTION] Saisissez le nombre d'itérations pour le script : "))

try:
    driver = webdriver.Chrome(options=options)
    tentative = 0

    while tentative < len(mots_cles) * iterations:
        index_mot_cle = tentative % len(mots_cles)  # Pour alterner entre les mots-clés
        requete = mots_cles[index_mot_cle].strip()
        log_message("ACTION", f"Tentative de recherche avec le mot-clé : {requete}")
        driver.get("https://www.google.com")

        # Gérer l'acceptation des cookies
        try:
            accept_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "L2AGLb"))
            )
            accept_button.click()
            log_message("INFO", "Bouton d'acceptation des cookies cliqué.")
        except:
            log_message("INFO", "Aucun message d'acceptation des cookies détecté.")

        try:
            # Rechercher la barre de recherche et envoyer la requête
            search_bar = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, "q"))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", search_bar)
            time.sleep(1)

            search_bar.clear()
            search_bar.send_keys(requete)
            search_bar.submit()
            time.sleep(2)
            log_message("ACTION", f"Requête envoyée : {requete}")

            page_number = 1
            lien_trouve = False

            while page_number <= 3 and not lien_trouve:
                log_message("INFO", f"Recherche sur la page {page_number}...")

                # Obtenir tous les résultats de recherche sponsorisés
                resultats = driver.find_elements(By.XPATH, "//div[@class='uEierd']")
                position = 1

                for resultat in resultats:
                    try:
                        sponsorise = resultat.find_element(By.XPATH, ".//span[contains(text(), 'Sponsorisé')]")
                        if sponsorise:
                            log_message("INFO", "Annonce sponsorisée détectée.")

                            # Détecter le domaine via le CSS
                            try:
                                domaine_css = resultat.find_element(By.XPATH, ".//span[contains(@class, 'OSrXXb')]").text
                                log_message("DEBUG", f"Domaine CSS détecté : {domaine_css}")
                            except:
                                domaine_css = ""
                                log_message("DEBUG", "Domaine CSS non trouvé.")

                            lien = resultat.find_element(By.TAG_NAME, "a")
                            url = lien.get_attribute("href")
                            domaine_cible = domaine_css in domaines_cibles
                            visited = False

                            # Vérification si le domaine CSS correspond au domaine cible
                            if domaine_cible:
                                log_message("ACTION", f"Domaine CSS cible détecté : {domaine_css}. Clic sur l'annonce.")
                                lien.click()
                                visited = True
                                time.sleep(2)
                                lien_trouve = True
                            elif domaine_css in domaine_a_ignorer:
                                log_message("INFO", f"Annonce de domaine ignoré détectée : {domaine_css}. Ignorée par CSS.")
                            else:
                                # Vérification par URL si domaine CSS non déterminant
                                log_message("INFO", f"Vérification URL pour : {url}")
                                domaine_cible = any(domaine in url for domaine in domaines_cibles)
                                if domaine_cible:
                                    log_message("ACTION", f"URL de l'annonce cible détectée : {url}. Clic sur l'annonce.")
                                    lien.click()
                                    visited = True
                                    time.sleep(2)
                                    lien_trouve = True
                                elif any(ignored in url for ignored in domaine_a_ignorer):
                                    log_message("INFO", f"Annonce de domaine ignoré détectée par URL : {url}. Ignorée.")
                                else:
                                    log_message("INFO", f"URL ne correspond pas au domaine cible : {url}.")

                            enregistrer_statistiques(requete, page_number, position, url, domaine_cible, visited)
                            position += 1
                            if visited:
                                break
                    except:
                        log_message("INFO", "Annonce sans tag 'Sponsorisé' ignorée.")
                        position += 1

                if not lien_trouve:
                    try:
                        next_button = driver.find_element(By.XPATH, "//a[@id='pnnext']")
                        next_button.click()
                        page_number += 1
                        time.sleep(2)
                    except:
                        log_message("INFO", "Aucune page suivante trouvée.")
                        break

            if lien_trouve:
                log_message("INFO", f"Lien cible trouvé et cliqué pour le mot-clé '{requete}'.")
                driver.back()
                time.sleep(2)
                tentative += 1
            else:
                log_message("INFO", f"Aucun lien cible trouvé avec le mot-clé '{requete}'.")
                tentative += 1

        except Exception as e:
            log_message("ERROR", f"Erreur lors de l'interaction avec la barre de recherche : {e}")
            tentative += 1

except KeyboardInterrupt:
    log_message("ACTION", "Script interrompu par l'utilisateur avec Ctrl + C.")
finally:
    try:
        driver.quit()
    except:
        pass
    log_message("INFO", "Script terminé proprement.")
    sauvegarder_donnees()
