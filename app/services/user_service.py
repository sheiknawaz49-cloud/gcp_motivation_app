import logging
from typing import Optional, Dict, Any, List
from app.services.gcp import db

logger = logging.getLogger("motivation-app")


class UserService:
    """Centralized service for managing user profiles, preferences, and feedback in Firestore."""

    @staticmethod
    def get_user_ref(email: str):
        if not db or not email:
            return None
        return db.collection("users").document(email.strip().lower())

    @staticmethod
    def get_user_data(email: str) -> Dict[str, Any]:
        user_ref = UserService.get_user_ref(email)
        if not user_ref:
            return {}
        try:
            doc = user_ref.get()
            return doc.to_dict() if doc.exists else {}
        except Exception as e:
            logger.error(f"Error fetching user data for {email}: {e}")
            return {}

    @staticmethod
    def update_user(email: str, data: Dict[str, Any]) -> bool:
        user_ref = UserService.get_user_ref(email)
        if not user_ref:
            return False
        try:
            user_ref.set(data, merge=True)
            return True
        except Exception as e:
            logger.error(f"Error updating user profile for {email}: {e}")
            return False

    @staticmethod
    def init_google_user(email: str, name: str, picture: str = "") -> bool:
        """Initializes or updates user profile on Google Sign-In with legacy profile fallback."""
        user_ref = UserService.get_user_ref(email)
        if not user_ref:
            return False
        try:
            user_doc = user_ref.get()
            if not user_doc.exists:
                legacy_doc = db.collection("users").document(name.lower()).get() if db else None
                legacy_data = legacy_doc.to_dict() if (legacy_doc and legacy_doc.exists) else {}

                user_ref.set({
                    "email": email.lower(),
                    "name": name,
                    "picture": picture,
                    "goal": legacy_data.get("goal", "building great daily habits"),
                    "last_mood": legacy_data.get("last_mood", "focused"),
                    "preferred_voice": legacy_data.get("preferred_voice", "female"),
                    "streak": legacy_data.get("streak", 1),
                    "last_quote": legacy_data.get("last_quote", ""),
                    "audio_url": legacy_data.get("audio_url", ""),
                    "liked_quotes": legacy_data.get("liked_quotes", []),
                    "disliked_quotes": legacy_data.get("disliked_quotes", []),
                    "is_pro": False
                }, merge=True)
            else:
                user_ref.set({"name": name, "picture": picture}, merge=True)
            return True
        except Exception as e:
            logger.error(f"Error initializing Google user {email}: {e}")
            return False

    @staticmethod
    def init_passcode_user(email: str, name: str) -> bool:
        """Initializes or updates user profile on Passcode Sign-In."""
        user_ref = UserService.get_user_ref(email)
        if not user_ref:
            return False
        try:
            user_doc = user_ref.get()
            if not user_doc.exists:
                user_ref.set({
                    "email": email.lower(),
                    "name": name,
                    "picture": "",
                    "goal": "building great daily habits",
                    "last_mood": "focused",
                    "preferred_voice": "female",
                    "streak": 1,
                    "is_pro": False
                }, merge=True)
            else:
                user_ref.set({"name": name}, merge=True)
            return True
        except Exception as e:
            logger.error(f"Error initializing passcode user {email}: {e}")
            return False

    @staticmethod
    def save_onboarding(
        email: str,
        name: str,
        picture: str,
        interests: List[str],
        ai_persona_summary: str,
        language: str = "en"
    ) -> bool:
        """Saves user onboarding selections and marks onboarded as True."""
        return UserService.update_user(email, {
            "interests": interests,
            "ai_persona_summary": ai_persona_summary,
            "language": language,
            "onboarded": True,
            "name": name,
            "email": email.lower(),
            "picture": picture
        })

    @staticmethod
    def skip_onboarding(email: str, name: str) -> bool:
        """Marks onboarding as completed so users get generic quotes that adapt via feedback."""
        return UserService.update_user(email, {
            "onboarded": True,
            "name": name,
            "email": email.lower()
        })

    @staticmethod
    def update_mobile_context(email: str, context: str) -> bool:
        """Records screen-time / app usage context sent from mobile apps or shortcuts."""
        return UserService.update_user(email, {
            "app_usage_context": context.strip()
        })

    @staticmethod
    def set_language(email: str, language: str) -> bool:
        return UserService.update_user(email, {
            "language": language
        })

    @staticmethod
    def record_feedback(email: str, action: str, quote: str) -> Dict[str, Any]:
        """Records quote like or dislike into user profile."""
        user_ref = UserService.get_user_ref(email)
        if not user_ref:
            return {"status": "error", "message": "Database unavailable"}

        try:
            user_doc = user_ref.get()
            user_data = user_doc.to_dict() if user_doc.exists else {}

            if action == "like" and quote:
                liked = user_data.get("liked_quotes", [])
                if quote not in liked:
                    liked.append(quote)
                user_ref.set({"liked_quotes": liked}, merge=True)
                return {"status": "liked", "total_likes": len(liked)}

            elif action == "dislike" and quote:
                disliked = user_data.get("disliked_quotes", [])
                if quote not in disliked:
                    disliked.append(quote)
                user_ref.set({"disliked_quotes": disliked}, merge=True)
                return {"status": "disliked", "total_dislikes": len(disliked)}

            return {"status": "ignored"}
        except Exception as e:
            logger.error(f"Error recording feedback for {email}: {e}")
            return {"status": "error", "message": str(e)}
