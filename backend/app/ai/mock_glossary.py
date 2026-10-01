"""Glossaries for the offline mock provider.

These tables are deliberately small and school-specific. They let the whole
pipeline run and be tested with no API key and no network, which is what makes
this open-source project easy to evaluate.

They are **not** a substitute for a real translation model. Quality is bounded
by what is listed here; anything unknown is passed through unchanged and
flagged as an uncertainty so a reviewer sees it.
"""

from __future__ import annotations

import re

#: English -> target. Applied longest-phrase-first so multi-word terms win.
GLOSSARIES: dict[str, dict[str, str]] = {
    "es": {
        "Dear families": "Estimadas familias",
        "Dear family": "Estimada familia",
        "Thank you": "Gracias",
        "Thank you for your help": "Gracias por su ayuda",
        "Hello": "Hola",
        "Please return": "Por favor, devuelva",
        "Please send": "Por favor, envíe",
        "Please bring": "Por favor, traiga",
        "Please sign": "Por favor, firme",
        "Please complete": "Por favor, complete",
        "Please submit": "Por favor, envíe",
        "Please contact": "Por favor, comuníquese con",
        "Please call": "Por favor, llame",
        "Please RSVP": "Por favor, confirme su asistencia",
        "Please fill out": "Por favor, llene",
        "field trip permission form": "formulario de permiso para la excursión",
        "permission form": "formulario de permiso",
        "consent form": "formulario de consentimiento",
        "Family Curriculum Night": "Noche de Planes de Estudios Familiares",
        "Family Night": "Noche Familiar",
        "Curriculum Night": "Noche de Planes de Estudios",
        "book fair": "feria del libro",
        "open house": "jornada de puertas abiertas",
        "school office": "oficina de la escuela",
        "main office": "oficina principal",
        "program office": "oficina del programa",
        "program coordinator": "coordinador del programa",
        "front desk": "recepción",
        "teacher": "maestro",
        "principal": "director",
        "nurse": "enfermera",
        "volunteer": "voluntario",
        "volunteers": "voluntarios",
        "students": "estudiantes",
        "families": "familias",
        "parents": "padres",
        "children": "niños",
        "lunch": "almuerzo",
        "if you would like": "si desea",
        "optional": "opcional",
        "you may": "puede",
        "is required": "es obligatorio",
        "must": "debe",
        "should": "debe",
        "Questions?": "¿Preguntas?",
        "If you need an interpreter": "Si necesita un intérprete",
        "contact us": "comuníquese con nosotros",
        "by phone": "por teléfono",
        "by email": "por correo electrónico",
        "online": "en línea",
        "RSVP": "confirme su asistencia",
        "register": "inscribirse",
        "sign up": "inscribirse",
        "grades": "grados",
        "grade": "grado",
        "minutes": "minutos",
        "hours": "horas",
        "days": "días",
        "weeks": "semanas",
        "pages": "páginas",
        "shuttle bus": "autobús de transporte",
        "walking shoes": "zapatos para caminar",
        "food item": "alimento",
        "allergens": "alérgenos",
        "school day": "jornada escolar",
        "start at": "comenzará a las",
        "instead of": "en lugar de",
        "bring": "traer",
        "return": "devolver",
        "send": "enviar",
        "sign": "firmar",
        "complete": "completar",
        "call": "llamar",
        "contact": "comuníquese",
        "questions": "preguntas",
    },
    "hi": {
        "Dear families": "परिवारों के लिए",
        "Dear family": "परिवार के लिए",
        "Thank you": "धन्यवाद",
        "Hello": "नमस्ते",
        "Please return": "कृपया लौटाएँ",
        "Please send": "कृपया भेजें",
        "Please bring": "कृपया लाएँ",
        "Please sign": "कृपया हस्ताक्षर करें",
        "Please complete": "कृपया पूरा करें",
        "Please submit": "कृपया जमा करें",
        "Please contact": "कृपया संपर्क करें",
        "Please call": "कृपया कॉल करें",
        "Please RSVP": "कृपया पुष्टि करें",
        "permission form": "अनुमति फ़ॉर्म",
        "consent form": "सहमति फ़ॉर्म",
        "Family Curriculum Night": "पारिवारिक पाठ्यक्रम संध्या",
        "Curriculum Night": "पाठ्यक्रम संध्या",
        "school office": "विद्यालय कार्यालय",
        "main office": "मुख्य कार्यालय",
        "program office": "कार्यक्रम कार्यालय",
        "program coordinator": "कार्यक्रम समन्वयक",
        "front desk": "रिसेप्शन",
        "teacher": "शिक्षक",
        "principal": "प्रधानाचार्य",
        "nurse": "नर्स",
        "volunteer": "स्वयंसेवक",
        "students": "विद्यार्थियों",
        "families": "परिवारों",
        "parents": "अभिभावकों",
        "children": "बच्चों",
        "lunch": "दोपहर का भोजन",
        "if you would like": "यदि आप चाहें",
        "optional": "वैकल्पिक",
        "you may": "आप कर सकते हैं",
        "is required": "आवश्यक है",
        "must": "चाहिए",
        "should": "चाहिए",
        "Questions?": "क्या आपके कोई प्रश्न हैं?",
        "If you need an interpreter": "यदि आपको दुभाषिए की आवश्यकता हो",
        "RSVP": "पुष्टि करें",
        "register": "पंजीकरण",
        "sign up": "साइन अप करें",
        "minutes": "मिनट",
        "hours": "घंटे",
        "days": "दिन",
        "grades": "कक्षाएँ",
        "start at": "शुरू होगा",
        "instead of": "के बजाय",
        "bring": "लाएँ",
        "return": "लौटाएँ",
        "send": "भेजें",
        "sign": "हस्ताक्षर",
        "call": "कॉल",
        "contact": "संपर्क",
        "questions": "प्रश्न",
    },
    "ur": {
        "Dear families": "محترم خاندانوں کے لیے",
        "Thank you": "شکریہ",
        "Hello": "سلام",
        "Please return": "براہ کرم واپس کریں",
        "Please send": "براہ کرم بھیجیں",
        "Please bring": "براہ کرم لائیں",
        "Please sign": "براہ کرم دستخط کریں",
        "Please complete": "براہ کرم مکمل کریں",
        "Please contact": "براہ کرم رابطہ کریں",
        "Please call": "براہ کرم کال کریں",
        "permission form": "اجازت نامہ فارم",
        "consent form": "رضامندی فارم",
        "Family Curriculum Night": "خاندانی تعلیمی رات",
        "school office": "اسکول دفتر",
        "main office": "مرکزی دفتر",
        "program coordinator": "پروگرام کوآرڈینیٹر",
        "teacher": "استاد",
        "principal": "پرنسپل",
        "students": "طلباء",
        "families": "خاندانے",
        "parents": " والدین",
        "if you would like": "اگر آپ چاہیں",
        "optional": "اختیاری",
        "must": "ضروری ہے",
        "should": "چاہیے",
        "Questions?": "کیا آپ کو کوئی سوال ہے؟",
        "If you need an interpreter": "اگر آپ کو مترجم چاہیے",
        "RSVP": "تصدیق کریں",
        "bring": "لائیں",
        "return": "واپس",
        "send": "بھیجیں",
        "sign": "دستخط",
        "call": "کال",
        "contact": "رابطہ",
    },
}

#: Reverse tables, built once, used to bring a target-language line back to
#: English for the offline back-translation path.
REVERSE_GLOSSARIES: dict[str, dict[str, str]] = {
    code: {value.lower(): key for key, value in table.items()} for code, table in GLOSSARIES.items()
}


def translate_offline(text: str, language_code: str) -> tuple[str, list[str]]:
    """Glossary-based translation, used only by the mock provider.

    Matching is longest-phrase-first so "Family Curriculum Night" is replaced
    before "Night". Text with no glossary entry is passed through unchanged.

    Args:
        text: The masked source text.
        language_code: Target language code.

    Returns:
        The translated text and the phrases that had no glossary entry.
    """
    table = GLOSSARIES.get(language_code.lower(), {})
    if not table:
        return text, [f"No offline glossary is available for '{language_code}'."]

    lookup = {key.lower(): value for key, value in table.items()}
    phrases = sorted(lookup, key=len, reverse=True)
    pattern = re.compile("|".join(re.escape(phrase) for phrase in phrases), re.IGNORECASE)

    uncertain: list[str] = []

    def _substitute(match: re.Match[str]) -> str:
        phrase = match.group(0)
        replacement = lookup.get(phrase.lower())
        if replacement is None:
            uncertain.append(phrase)
            return phrase
        if phrase[:1].isupper():
            return replacement[:1].upper() + replacement[1:]
        return replacement

    return pattern.sub(_substitute, text), sorted(set(uncertain))


def back_translate_offline(text: str, language_code: str) -> str:
    """Glossary-based back-translation into English, for the mock provider.

    Args:
        text: The target-language line.
        language_code: The target language code.

    Returns:
        The English rendering, best-effort. Unrecognised text is left as-is.
    """
    reverse = REVERSE_GLOSSARIES.get(language_code.lower(), {})
    if not reverse:
        return text

    phrases = sorted(reverse, key=len, reverse=True)
    pattern = re.compile("|".join(re.escape(phrase) for phrase in phrases), re.IGNORECASE)

    def _substitute(match: re.Match[str]) -> str:
        phrase = match.group(0)
        replacement = reverse.get(phrase.lower(), phrase)
        if phrase[:1].isupper():
            return replacement[:1].upper() + replacement[1:]
        return replacement

    return pattern.sub(_substitute, text)
