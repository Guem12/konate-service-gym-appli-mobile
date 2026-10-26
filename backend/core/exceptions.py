from rest_framework.views import exception_handler

TRANSLATIONS = {
    "Authentication credentials were not provided.": "Authentification requise.",
    "Given token not valid for any token type": "Jeton invalide ou expiré.",
    "You do not have permission to perform this action.": (
        "Vous n'avez pas la permission d'effectuer cette action."
    ),
    "Not found.": "Ressource introuvable.",
    "This field is required.": "Ce champ est obligatoire.",
    'Method "GET" not allowed.': "Méthode non autorisée.",
    "Invalid token.": "Jeton invalide.",
    "Token is invalid or expired": "Jeton invalide ou expiré.",
}


def api_exception_handler(exc, context):
    """Traduit les messages DRF les plus courants en français."""
    response = exception_handler(exc, context)
    if response is None:
        return response

    data = response.data
    if isinstance(data, dict):
        if "detail" in data and isinstance(data["detail"], str):
            data["detail"] = TRANSLATIONS.get(str(data["detail"]), str(data["detail"]))
        for key, value in list(data.items()):
            if isinstance(value, list):
                data[key] = [
                    TRANSLATIONS.get(str(item), str(item)) for item in value
                ]
            elif isinstance(value, str):
                data[key] = TRANSLATIONS.get(value, value)
    return response
