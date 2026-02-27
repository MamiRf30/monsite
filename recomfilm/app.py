from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json
import os

app = Flask(__name__)
CORS(app)  # Permet les requêtes depuis le frontend

# ============================================
# CONFIGURATION DE L'API GROQ
# ============================================
# 1. Allez sur https://console.groq.com
# 2. Créez un compte gratuit
# 3. Allez dans "API Keys"
# 4. Créez une nouvelle clé API
# 5. Remplacez 'YOUR_GROQ_API_KEY_HERE' ci-dessous par votre clé
# ============================================

GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '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')
GROQ_API_URL = 'https://api.groq.com/openai/v1/chat/completions'

# Modèle Groq à utiliser (rapide et performant)
GROQ_MODEL = 'llama-3.3-70b-versatile'


@app.route('/recommend', methods=['POST'])
def recommend_movie():
    """
    Endpoint pour obtenir une recommandation de film via Groq AI
    Reçoit: mood, language, genre
    Retourne: informations du film recommandé
    """
    try:
        data = request.get_json()
        mood = data.get('mood')
        language = data.get('language')
        genre = data.get('genre')

        # Validation des données
        if not mood or not language or not genre:
            return jsonify({"error": "Tous les champs sont requis"}), 400

        # Vérifier si la clé API Groq est configurée
        if GROQ_API_KEY == 'YOUR_GROQ_API_KEY_HERE':
            # Mode démo sans clé API
            print("⚠️  Clé API Groq non configurée - utilisation du mode démo")
            movie = get_demo_recommendation(mood, language, genre)
            return jsonify(movie)

        # Générer la recommandation avec Groq
        movie = get_groq_recommendation(mood, language, genre)
        return jsonify(movie)

    except Exception as e:
        print(f"❌ Erreur serveur: {str(e)}")
        return jsonify({"error": f"Erreur serveur: {str(e)}"}), 500


def get_groq_recommendation(mood, language, genre):
    """
    Utilise l'API Groq pour générer une recommandation de film intelligente
    """
    
    # Construire le prompt pour Groq
    prompt = f"""Tu es un expert en cinéma. Recommande UN SEUL film qui correspond exactement à ces critères:

- Humeur de l'utilisateur: {mood}
- Langue du film: {language}
- Genre: {genre}

Réponds UNIQUEMENT avec un objet JSON valide dans ce format exact (sans texte avant ou après):
{{
    "title": "Titre du film",
    "overview": "Description détaillée du film en 2-3 phrases expliquant pourquoi il correspond à l'humeur et au genre demandés",
    "rating": "Note/10",
    "date": "Année de sortie",
    "poster_url": ""
}}

Important:
- Choisis un film réel et connu
- L'overview doit être en français et détaillé
- Laisse poster_url vide (chaîne vide)
- Assure-toi que le JSON est valide"""

    try:
        # Appel à l'API Groq
        headers = {
            'Authorization': f'Bearer {GROQ_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': GROQ_MODEL,
            'messages': [
                {
                    'role': 'system',
                    'content': 'Tu es un expert en recommandations de films. Tu réponds uniquement en JSON valide.'
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'temperature': 0.8,
            'max_tokens': 500
        }

        print(f"🤖 Appel à Groq API avec le modèle {GROQ_MODEL}...")
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        # Extraire la recommandation
        ai_response = result['choices'][0]['message']['content'].strip()
        
        # Nettoyer la réponse (enlever les backticks markdown si présents)
        ai_response = ai_response.replace('```json', '').replace('```', '').strip()
        
        print(f"✅ Réponse de Groq reçue")
        print(f"📝 Contenu: {ai_response[:200]}...")
        
        # Parser le JSON
        movie_data = json.loads(ai_response)
        
        return movie_data

    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur lors de l'appel à Groq API: {str(e)}")
        if hasattr(e.response, 'text'):
            print(f"Détails: {e.response.text}")
        # Retour en mode démo en cas d'erreur
        return get_demo_recommendation(mood, language, genre)
    
    except json.JSONDecodeError as e:
        print(f"❌ Erreur de parsing JSON: {str(e)}")
        print(f"Réponse reçue: {ai_response}")
        # Retour en mode démo en cas d'erreur
        return get_demo_recommendation(mood, language, genre)


def get_demo_recommendation(mood, language, genre):
    """
    Retourne une recommandation de démo quand l'API Groq n'est pas configurée
    """
    
    # Base de données de films de démo
    demo_movies = {
        'action': {
            'title': 'Spider-Man: No Way Home',
            'overview': "Peter Parker fait face à ses plus grands défis alors que son identité secrète est révélée au monde. Avec l'aide du Doctor Strange, il tente de réparer les dégâts, mais les choses deviennent dangereuses lorsque des visiteurs d'autres dimensions arrivent. Ce film d'action spectaculaire est parfait pour votre humeur actuelle!",
            'rating': '⭐ 8.2/10',
            'date': '📅 2021',
            'poster_url': ''
        },
        'comédie': {
            'title': 'The Grand Budapest Hotel',
            'overview': "Une comédie visuelle époustouflante qui suit les aventures de Gustave H., le concierge légendaire d'un hôtel européen prestigieux, et de Zero Moustafa, son protégé. Entre vol de tableaux, romance et humour absurde, ce film est une expérience cinématographique unique qui vous fera rire et vous émerveillera!",
            'rating': '⭐ 8.1/10',
            'date': '📅 2014',
            'poster_url': ''
        },
        'drame': {
            'title': 'Les Évadés (The Shawshank Redemption)',
            'overview': "L'histoire poignante d'Andy Dufresne, un banquier condamné à perpétuité pour un crime qu'il n'a pas commis. En prison, il développe une amitié profonde avec Red et trouve des moyens de maintenir l'espoir vivant. Un chef-d'œuvre du cinéma qui explore la résilience humaine et la rédemption.",
            'rating': '⭐ 9.3/10',
            'date': '📅 1994',
            'poster_url': ''
        },
        'romance': {
            'title': 'La La Land',
            'overview': "Une histoire d'amour magique entre Mia, une actrice en herbe, et Sebastian, un musicien de jazz passionné, dans la ville des rêves de Los Angeles. Ce film musical enchanteur capture parfaitement les hauts et les bas de la poursuite de ses rêves tout en tombant amoureux. Les chansons et les chorégraphies sont inoubliables!",
            'rating': '⭐ 8.0/10',
            'date': '📅 2016',
            'poster_url': ''
        },
        'horreur': {
            'title': 'Sans un bruit (A Quiet Place)',
            'overview': "Dans un monde post-apocalyptique où des créatures aveugles chassent au son, une famille doit vivre dans le silence absolu pour survivre. Ce thriller d'horreur innovant crée une tension insoutenable sans presque aucun dialogue. Parfait pour ceux qui cherchent des frissons et de l'angoisse!",
            'rating': '⭐ 7.5/10',
            'date': '📅 2018',
            'poster_url': ''
        },
        'science-fiction': {
            'title': 'Inception',
            'overview': "Dom Cobb est un voleur spécialisé dans l'extraction d'informations à partir des rêves. On lui propose une mission impossible: implanter une idée dans l'esprit de quelqu'un. Ce chef-d'œuvre de science-fiction vous plongera dans des niveaux de réalité vertigineux avec des effets visuels époustouflants!",
            'rating': '⭐ 8.8/10',
            'date': '📅 2010',
            'poster_url': ''
        },
        'aventure': {
            'title': 'Indiana Jones et les Aventuriers de l\'Arche Perdue',
            'overview': "Le légendaire archéologue Indiana Jones part à la recherche de l'Arche d'Alliance avant que les nazis ne mettent la main dessus. Action, mystère, humour et aventure s'entremêlent dans ce classique intemporel qui définit le genre. Attachez votre ceinture pour une aventure inoubliable!",
            'rating': '⭐ 8.4/10',
            'date': '📅 1981',
            'poster_url': ''
        },
        'thriller': {
            'title': 'Se7en',
            'overview': "Deux détectives, l'un vétéran cynique et l'autre jeune idéaliste, traquent un tueur en série qui base ses meurtres sur les sept péchés capitaux. Ce thriller psychologique sombre et intense vous tiendra en haleine jusqu'à sa conclusion choquante. Parfait pour votre humeur actuelle!",
            'rating': '⭐ 8.6/10',
            'date': '📅 1995',
            'poster_url': ''
        },
        'animation': {
            'title': 'Spider-Man: New Generation',
            'overview': "Miles Morales devient Spider-Man et découvre un multivers où plusieurs versions de Spider-Man existent. Cette révolution visuelle de l'animation combine action, humour et émotion dans une expérience cinématographique unique. Un film d'animation qui repousse toutes les limites!",
            'rating': '⭐ 8.4/10',
            'date': '📅 2018',
            'poster_url': ''
        },
        'famille': {
            'title': 'Coco',
            'overview': "Miguel, un jeune garçon passionné de musique, se retrouve transporté au Pays des Morts où il découvre les secrets de son histoire familiale. Ce film Pixar émouvant célèbre la famille, la mémoire et la culture mexicaine avec des visuels époustouflants et une musique inoubliable.",
            'rating': '⭐ 8.4/10',
            'date': '📅 2017',
            'poster_url': ''
        },
        'fantaisie': {
            'title': 'Le Seigneur des Anneaux: La Communauté de l\'Anneau',
            'overview': "Frodon Sacquet hérite d'un anneau magique qui doit être détruit pour sauver la Terre du Milieu. Accompagné d'une communauté de héros, il entreprend un voyage épique. Cette trilogie légendaire redéfinit le genre fantasy avec des décors spectaculaires et une histoire captivante!",
            'rating': '⭐ 8.9/10',
            'date': '📅 2001',
            'poster_url': ''
        },
        'crime': {
            'title': 'Le Parrain',
            'overview': "L'épopée d'une famille mafieuse italo-américaine à New York. Vito Corleone, le patriarche, transfère le contrôle de son empire criminel à son fils Michael, un héros de guerre réticent. Ce chef-d'œuvre du cinéma explore le pouvoir, la famille et la trahison avec une maîtrise absolue.",
            'rating': '⭐ 9.2/10',
            'date': '📅 1972',
            'poster_url': ''
        },
        'documentaire': {
            'title': 'Planète Terre II',
            'overview': "Une exploration époustouflante de la nature et de la vie sauvage à travers les îles, montagnes, jungles, déserts, prairies et villes du monde. Filmé avec des technologies de pointe, ce documentaire révèle des comportements animaux jamais vus auparavant. Une expérience visuelle extraordinaire!",
            'rating': '⭐ 9.5/10',
            'date': '📅 2016',
            'poster_url': ''
        },
        'western': {
            'title': 'Le Bon, la Brute et le Truand',
            'overview': "Trois hommes poursuivent une fortune en or pendant la Guerre de Sécession américaine. Ce western spaghetti iconique de Sergio Leone, avec sa musique légendaire d'Ennio Morricone, redéfinit le genre avec son style visuel unique et ses personnages inoubliables.",
            'rating': '⭐ 8.8/10',
            'date': '📅 1966',
            'poster_url': ''
        }
    }
    
    # Sélectionner un film en fonction du genre
    movie = demo_movies.get(genre, demo_movies['action'])
    
    # Ajouter une mention sur l'humeur dans l'overview
    mood_texts = {
        'heureux': "Ce film joyeux correspond parfaitement à votre humeur positive!",
        'triste': "Ce film touchant saura résonner avec votre état d'esprit mélancolique.",
        'excite': "Préparez-vous à une expérience cinématographique excitante et intense!",
        'romantique': "Laissez-vous emporter par cette belle histoire qui réchauffera votre cœur.",
        'peur': "Idéal pour assouvir votre envie de sensations fortes et de frissons!",
        'calme': "Parfait pour une soirée relaxante et contemplative."
    }
    
    movie_copy = movie.copy()
    movie_copy['overview'] = f"{movie['overview']} {mood_texts.get(mood, '')}"
    
    return movie_copy


@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint de vérification de santé du serveur"""
    api_configured = GROQ_API_KEY != 'YOUR_GROQ_API_KEY_HERE'
    return jsonify({
        "status": "ok",
        "message": "Backend Flask avec Groq AI est en ligne!",
        "groq_api_configured": api_configured,
        "mode": "Production (Groq AI)" if api_configured else "Démo (sans API)"
    })



    print("=" * 70)
    print("🕷️  SPIDEY CINEMA - Backend Flask avec Groq AI")
    print("=" * 70)
    print(f"🌐 Serveur lancé sur: http://localhost:5000")
    
    if GROQ_API_KEY == 'YOUR_GROQ_API_KEY_HERE':
        print("⚠️  Clé API Groq: NON CONFIGURÉE ❌")
        print("📝 Mode: DÉMO (recommandations prédéfinies)")
        print("")
        print("Pour utiliser Groq AI:")
        print("  1. Allez sur https://console.groq.com")
        print("  2. Créez un compte gratuit")
        print("  3. Générez une clé API")
        print("  4. Remplacez GROQ_API_KEY dans app.py")
    else:
        print(f"✅ Clé API Groq: CONFIGURÉE ✅")
        print(f"🤖 Modèle utilisé: {GROQ_MODEL}")
        print("📝 Mode: PRODUCTION (recommandations IA)")
    
    print("")
    print("Endpoints disponibles:")
    print("  POST /recommend - Obtenir une recommandation de film")
    print("  GET  /health    - Vérifier l'état du serveur")
    print("=" * 70)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
