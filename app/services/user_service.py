import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple
from app.services.gcp import db

logger = logging.getLogger("motivation-app")

# Asia/Kolkata timezone support (UTC+5:30)
try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except Exception:
    IST = timezone(timedelta(hours=5, minutes=30))

MAX_DAILY_CARDS = 3


class UserService:
    """Centralized service for managing user profiles, preferences, and feedback in Firestore."""

    @staticmethod
    def get_today_str() -> str:
        return datetime.now(IST).strftime("%Y-%m-%d")

    @staticmethod
    def get_yesterday_str() -> str:
        return (datetime.now(IST) - timedelta(days=1)).strftime("%Y-%m-%d")

    @staticmethod
    def calculate_streak(user_data: Dict[str, Any]) -> Tuple[int, int, str]:
        """
        Calculates date-based streak for future leaderboards/competitions.
        - If last_streak_date == today_str: keep streak unchanged.
        - If last_streak_date == yesterday_str: increment streak += 1.
        - Otherwise (missed a day or new user): set streak = 1.
        - Always returns (streak, max_streak, today_str).
        """
        today_str = UserService.get_today_str()
        yesterday_str = UserService.get_yesterday_str()
        last_streak_date = user_data.get("last_streak_date", "")
        current_streak = int(user_data.get("streak", 1))

        if last_streak_date == today_str:
            streak = current_streak
        elif last_streak_date == yesterday_str:
            streak = current_streak + 1
        else:
            streak = 1

        max_streak = max(streak, int(user_data.get("max_streak", 0)))
        return streak, max_streak, today_str

    @staticmethod
    def get_daily_status(user_data: Dict[str, Any]) -> Tuple[int, List[Dict[str, Any]], str]:
        """
        Checks daily card allowance.
        If last_active_date != today_str, resets daily_count = 0 and daily_cards = [].
        Returns (daily_count, daily_cards, today_str).
        """
        today_str = UserService.get_today_str()
        last_active_date = user_data.get("last_active_date", "")
        if last_active_date != today_str:
            daily_count = 0
            daily_cards = []
        else:
            daily_count = int(user_data.get("daily_count", 0))
            raw_cards = user_data.get("daily_cards", [])
            daily_cards = raw_cards if isinstance(raw_cards, list) else []
        return daily_count, daily_cards, today_str

    @staticmethod
    def sync_user_daily_and_streak(email: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ensures user's streak and daily card limit state in Firestore are synced for today.
        """
        daily_count, daily_cards, today_str = UserService.get_daily_status(user_data)
        streak, max_streak, _ = UserService.calculate_streak(user_data)

        updates = {}
        if user_data.get("last_active_date") != today_str:
            updates["last_active_date"] = today_str
            updates["daily_count"] = daily_count
            updates["daily_cards"] = daily_cards

        if user_data.get("last_streak_date") != today_str or user_data.get("streak") != streak:
            updates["streak"] = streak
            updates["max_streak"] = max_streak
            updates["last_streak_date"] = today_str

        if updates and email:
            UserService.update_user(email, updates)

        synced = dict(user_data)
        synced.update({
            "daily_count": daily_count,
            "daily_cards": daily_cards,
            "last_active_date": today_str,
            "streak": streak,
            "max_streak": max_streak,
            "last_streak_date": today_str
        })
        return synced

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

                today_str = UserService.get_today_str()
                user_ref.set({
                    "email": email.lower(),
                    "name": name,
                    "picture": picture,
                    "goal": legacy_data.get("goal", "building great daily habits"),
                    "last_mood": legacy_data.get("last_mood", "focused"),
                    "preferred_voice": legacy_data.get("preferred_voice", "female"),
                    "streak": legacy_data.get("streak", 1),
                    "max_streak": legacy_data.get("max_streak", 1),
                    "last_streak_date": legacy_data.get("last_streak_date", today_str),
                    "last_active_date": legacy_data.get("last_active_date", today_str),
                    "daily_count": legacy_data.get("daily_count", 0),
                    "daily_cards": legacy_data.get("daily_cards", []),
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
                today_str = UserService.get_today_str()
                user_ref.set({
                    "email": email.lower(),
                    "name": name,
                    "picture": "",
                    "goal": "building great daily habits",
                    "last_mood": "focused",
                    "preferred_voice": "female",
                    "streak": 1,
                    "max_streak": 1,
                    "last_streak_date": today_str,
                    "last_active_date": today_str,
                    "daily_count": 0,
                    "daily_cards": [],
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

    @staticmethod
    def delete_user_account(email: str, name: str = "") -> bool:
        """Deletes user Firestore document and associated audio files in GCS bucket."""
        if not email:
            return False
        clean_email = email.strip().lower()

        # 1. Fetch user data before deletion to identify audio files
        user_data = UserService.get_user_data(clean_email)

        # 2. Delete Firestore user document
        try:
            if db:
                db.collection("users").document(clean_email).delete()
                # Also delete legacy username doc if exists
                if name:
                    db.collection("users").document(name.lower()).delete()
        except Exception as e:
            logger.error(f"Error deleting Firestore document for {clean_email}: {e}")

        # 3. Delete associated audio files from GCS bucket
        try:
            from app.services.gcp import storage_client
            from app.core.config import settings

            if storage_client and settings.BUCKET_NAME:
                bucket = storage_client.bucket(settings.BUCKET_NAME)

                # Check specific URLs saved in user profile
                urls_to_delete = []
                if user_data.get("audio_url"):
                    urls_to_delete.append(user_data["audio_url"])
                for card in user_data.get("daily_cards", []):
                    if isinstance(card, dict) and card.get("audio_url"):
                        urls_to_delete.append(card["audio_url"])

                for url in urls_to_delete:
                    try:
                        blob_name = url.split(f"/{settings.BUCKET_NAME}/")[-1]
                        blob = bucket.blob(blob_name)
                        if blob.exists():
                            blob.delete()
                    except Exception as err:
                        logger.warning(f"Failed to delete audio blob from URL {url}: {err}")

                # Delete all blobs starting with user's name or email prefix
                prefixes = []
                if name:
                    prefixes.append(f"{name.lower()}_")
                user_prefix = clean_email.split("@")[0]
                if user_prefix:
                    prefixes.append(f"{user_prefix}_")

                for prefix in set(prefixes):
                    try:
                        blobs = bucket.list_blobs(prefix=prefix)
                        for b in blobs:
                            b.delete()
                    except Exception as err:
                        logger.warning(f"Failed to delete audio blobs for prefix {prefix}: {err}")
        except Exception as e:
            logger.error(f"Error deleting GCS audio files for {clean_email}: {e}")

        return True

